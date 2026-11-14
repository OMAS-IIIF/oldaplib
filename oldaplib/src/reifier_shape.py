"""Named, project-owned SHACL shapes for RDF 1.2 assertion annotations.

Fields reuse PropertyClass constraints but have no OWL class owner. Shape
mutations are transactional, never cached, and reject referenced deletions and
structural edits while instances use the shape. Instance editing is separate.
"""

from copy import deepcopy
from types import MappingProxyType

from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.helpers.construct_processor import ConstructProcessor
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.helpers.oldaperror import (OldapErrorAlreadyExists, OldapErrorInconsistency,
    OldapErrorInUse, OldapErrorNoPermission, OldapErrorNotFound, OldapErrorValue,
    OldapErrorUpdateFailed)
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.model import Model
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resource_transaction import resource_transaction, invalidate_model_cache_on_completion
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_qname import Xsd_QName


def values(value):
    """Normalize CONSTRUCT singleton/multiple objects without splitting an IRI."""
    return value if isinstance(value, (list, set, tuple)) else ([] if value is None else [value])


@serializer
class ReifierShape(Model, Notify):
    """Manage a named annotation shape independently of ResourceClass.

    Args:
        con: Authenticated connection; writes require ADMIN_MODEL or ADMIN_OLDAP.
        project: Owning project or its identifier.
        shape_iri: Project-local QName of the shape, including its Shape suffix
            if desired. No suffix is added or removed by this class.
        properties: Independent field definitions copied on insertion.
        creator, created, contributor, modified: Existing audit metadata.

    Mutating a field returned by properties marks the shape dirty. Adding or
    deleting fields uses mapping operations. update() checks the persisted
    modification token inside its transaction. Instances must be discarded
    after a failed enclosing transaction, following resource_transaction rules.
    """

    def __init__(self, *, con, project, shape_iri, properties=None,
                 creator=None, created=None, contributor=None, modified=None):
        Model.__init__(self, connection=con, creator=creator, created=created,
                       contributor=contributor, modified=modified)
        Notify.__init__(self)
        self._project = project if isinstance(project, Project) else Project.read(con, project)
        self._shape_iri = Xsd_QName(shape_iri)
        self._context = Context(name=con.context_name)
        self._context[self._project.projectShortName] = self._project.namespaceIri
        self._context.use(self._project.projectShortName)
        if self.shape_iri.prefix != str(self._project.projectShortName):
            raise OldapErrorValue('Reifier shape must belong to its owning project namespace.')
        self._properties = {}
        for prop in properties or []:
            if prop.property_class_iri in self._properties:
                raise OldapErrorValue(f'Duplicate annotation field {prop.property_class_iri}.')
            self[prop.property_class_iri] = prop
        self.clear_changeset()

    @property
    def shape_iri(self):
        """Immutable identity of this definition, independent of any OWL class."""
        return Xsd_QName(self._shape_iri)

    @property
    def properties(self):
        """Read-only field mapping; contained properties remain editable."""
        return MappingProxyType(self._properties)

    def __getitem__(self, key):
        return self._properties[Xsd_QName(key)]

    def __setitem__(self, key, prop):
        key = Xsd_QName(key)
        if not isinstance(prop, PropertyClass) or prop.property_class_iri != key:
            raise OldapErrorValue('Annotation field key must match its PropertyClass IRI.')
        if prop.appliesToProperty or prop.inResourceClass:
            raise OldapErrorValue('Annotation fields must be independent property definitions.')
        field = deepcopy(prop, {id(self._con): self._con})
        self._check_field(field)
        field._ownerShape = self.shape_iri
        field.set_notifier(self.notifier, key)
        self._properties[key] = field
        self.notifier(key)

    def __delitem__(self, key):
        del self._properties[Xsd_QName(key)]
        self.notifier(Xsd_QName(key))

    @staticmethod
    def _check_field(prop):
        from oldaplib.src.assertion_annotation import PROTECTED, uri
        if str(uri(Context(name=prop._con.context_name), prop.property_class_iri)) in PROTECTED:
            raise OldapErrorValue('System/permission predicates cannot be annotation fields.')
        if prop.datatype is None and prop.toClass is None:
            raise OldapErrorValue('Annotation fields require a datatype or class constraint; nodeKind alone is not supported.')
        allowed = {'TYPE', 'CLASS', 'NODEKIND', 'DATATYPE', 'NAME', 'DESCRIPTION',
                   'LANGUAGE_IN', 'UNIQUE_LANG', 'IN', 'MIN_LENGTH', 'MAX_LENGTH',
                   'PATTERN', 'MIN_EXCLUSIVE', 'MIN_INCLUSIVE', 'MAX_EXCLUSIVE',
                   'MAX_INCLUSIVE', 'MIN_COUNT', 'MAX_COUNT', 'ORDER', 'GROUP', 'EDITOR'}
        for attr, value in prop._attributes.items():
            if attr.name not in allowed and value is not None:
                raise OldapErrorValue(f'Unsupported annotation field constraint {attr.value}.')
        for value in (prop.minCount, prop.maxCount):
            if value is not None and value < 0:
                raise OldapErrorValue('Annotation cardinalities must be non-negative.')
        if prop.minCount is not None and prop.maxCount is not None and prop.minCount > prop.maxCount:
            raise OldapErrorValue('Annotation minCount must not exceed maxCount.')

    def notifier(self, field):
        """Propagate nested field changes to an owning DataModel."""
        self._changeset[field] = True
        self.notify()

    def clear_changeset(self):
        for prop in getattr(self, '_properties', {}).values():
            prop.clear_changeset()
        self._changeset = {}

    def _as_dict(self):
        return super()._as_dict() | {'project': self._project.projectShortName,
            'shape_iri': self.shape_iri, 'properties': list(self._properties.values())}

    def __deepcopy__(self, memo):
        copied = type(self)(con=self._con, project=self._project, shape_iri=self.shape_iri,
                           properties=list(self._properties.values()), creator=self.creator,
                           created=self.created, contributor=self.contributor, modified=self.modified)
        memo[id(self)] = copied
        for name in ('_creator', '_created', '_contributor', '_modified'):
            setattr(copied, name, deepcopy(getattr(self, name), memo))
        copied._changeset = deepcopy(self._changeset, memo)
        return copied

    def create_shacl(self, *, timestamp=None, **_):
        """Render complete shape triples for insertion or TriG export."""
        stamp = timestamp or self.modified
        text = f'{self.shape_iri.toRdf} a sh:NodeShape, oldap:ReifierShape'
        for predicate, value in [('creator', self.creator or (self._con.userIri if timestamp else None)),
                                 ('created', self.created or timestamp),
                                 ('contributor', self._con.userIri if timestamp else self.contributor),
                                 ('modified', stamp)]:
            if value is not None:
                text += f' ; dcterms:{predicate} {value.toRdf}'
        for prop in self._properties.values():
            self._check_field(prop)
            text += ' ; sh:property [' + prop.property_node_shacl() + ' ]'
        return text + ' .\n'

    def create_owl(self):
        """Declare annotation predicates without inventing OWL class restrictions."""
        return ''.join(prop.create_owl() for prop in self._properties.values())

    def validate_predicate_types(self):
        """Prevent annotation writes from giving an existing predicate conflicting OWL kinds."""
        if not self._properties:
            return
        rows = ' '.join(f'({prop.property_class_iri.toRdf} '
            f'{"owl:ObjectProperty" if prop.datatype is not None else "owl:DatatypeProperty"})'
            for prop in self._properties.values())
        query = self._context.sparql_context + f'ASK {{ VALUES (?predicate ?forbidden) {{ {rows} }} GRAPH ?g {{ ?predicate a ?forbidden }} }}'
        result = self._con.transaction_query(query) if self._con.in_transaction() else self._con.query(query)
        if result['boolean']:
            raise OldapErrorInconsistency('Annotation field conflicts with an existing OWL property kind.')

    def set_creation_metadata(self, timestamp):
        """Synchronize metadata after a successful enclosing DataModel insert."""
        self._modified = timestamp
        self._contributor = self._con.userIri
        if self._created is None:
            self._created = timestamp
        if self._creator is None:
            self._creator = self._con.userIri
        self.clear_changeset()

    def _structure(self):
        metadata = {PropClassAttr.NAME, PropClassAttr.DESCRIPTION, PropClassAttr.ORDER,
                    PropClassAttr.GROUP, PropClassAttr.EDITOR}
        return {key: {attr: value for attr, value in prop._attributes.items() if attr not in metadata}
                for key, prop in self._properties.items()}

    @classmethod
    def from_definition(cls, con, project, iri, definition):
        """Decode a supported named NodeShape, rejecting unsupported predicates."""
        allowed = {'rdf:type', 'sh:property', 'dcterms:creator', 'dcterms:created',
                   'dcterms:contributor', 'dcterms:modified'}
        if any(str(key) not in allowed for key in definition):
            raise OldapErrorValue(f'Unsupported reifier shape definition: {iri}.')
        types = {str(x) for x in values(definition.get(Xsd_QName('rdf:type')))}
        if 'sh:NodeShape' not in types or types - {'sh:NodeShape', 'oldap:ReifierShape'}:
            raise OldapErrorValue(f'Expected a reifier NodeShape: {iri}.')
        fields = []
        for item in values(definition.get(Xsd_QName('sh:property'))):
            if not isinstance(item, dict) or not isinstance(item.get(Xsd_QName('sh:path')), Xsd_QName):
                raise OldapErrorValue('Reifier fields require inline definitions and simple predicate paths.')
            attributes = {}
            for key, value in item.items():
                if str(key) == 'sh:path':
                    continue
                if str(key) == 'rdf:type' and str(value) == 'sh:PropertyShape':
                    continue
                attr = PropClassAttr.from_value(key)
                attributes[attr.fragment] = value
            fields.append(PropertyClass(con=con, project=project,
                property_class_iri=item[Xsd_QName('sh:path')], **attributes))
        metadata = {key.fragment: value for key, value in definition.items() if key.prefix == 'dcterms'}
        shape = cls(con=con, project=project, shape_iri=iri, properties=fields, **metadata)
        # Missing RDF audit values must not become a new timestamp on each read.
        # An explicit managed write initializes them consistently.
        for name in ('creator', 'created', 'contributor', 'modified'):
            if name not in metadata:
                setattr(shape, '_' + name, None)
        return shape

    @classmethod
    def read(cls, con, project, shape_iri):
        """Read a fresh shape; never place resolved shared definitions in Redis."""
        project = project if isinstance(project, Project) else Project.read(con, project)
        iri = Xsd_QName(shape_iri)
        definitions = ConstructProcessor.query_shacl(con=con, project=project, shape_iri=iri)
        if iri not in definitions:
            raise OldapErrorNotFound(f'Reifier shape {iri} not found.')
        if Xsd_QName('oldap:ReifierShape') not in values(definitions[iri].get(Xsd_QName('rdf:type'))):
            query = Context(name=con.context_name).sparql_context + f'ASK {{ GRAPH ?g {{ ?use sh:reifierShape {iri.toRdf} }} }}'
            result = con.transaction_query(query) if con.in_transaction() else con.query(query)
            if not result['boolean']:
                raise OldapErrorValue('Unmarked NodeShape is not referenced as a reifier shape.')
        return cls.from_definition(con, project, iri, definitions[iri])

    def _permission(self):
        grants = self._con.userdata.inProject
        if AdminPermission.ADMIN_OLDAP in (grants.get(Iri('oldap:SystemProject')) or set()):
            return
        if AdminPermission.ADMIN_MODEL not in (grants.get(self._project.projectIri) or set()):
            raise OldapErrorNoPermission('ADMIN_MODEL is required for the owning project.')

    def _ask(self, body):
        return self._con.transaction_query(self._context.sparql_context + 'ASK { ' + body + ' }')['boolean']

    def _persist(self, action):
        self._permission()
        graph = f'{self._project.projectShortName}:shacl'
        iri = self.shape_iri.toRdf
        with resource_transaction(self._con):
            invalidate_model_cache_on_completion(self._con, Xsd_QName(self._project.projectShortName, 'shacl'))
            if action != 'delete':
                self.validate_predicate_types()
            exists = self._ask(f'GRAPH {graph} {{ {iri} ?p ?o }}')
            if action == 'create' and exists:
                raise OldapErrorAlreadyExists(f'Shape {self.shape_iri} already exists.')
            if action != 'create' and not exists:
                raise OldapErrorNotFound(f'Shape {self.shape_iri} not found.')
            if action != 'create':
                current = type(self).read(self._con, self._project, self.shape_iri)
                if current.modified != self.modified:
                    raise OldapErrorUpdateFailed('Reifier shape was modified by another writer.')
                references = f'GRAPH ?g {{ ?use sh:reifierShape {iri} }}'
                if action == 'delete' and self._ask(references):
                    raise OldapErrorInUse('Cannot delete a referenced reifier shape.')
                # Conservatively protect all predicates using this shape, across
                # projects and inherited uses. No inference engine is assumed.
                if action == 'update' and current._structure() != self._structure() and self._ask(references +
                    ' GRAPH ?g { ?use sh:path ?predicate } GRAPH ?data { ?s ?predicate ?value }'):
                    raise OldapErrorInUse('Cannot change a reifier shape while its predicates have data.')
            if action != 'create':
                # Inline property/list nodes are mutable only when this shape
                # exclusively owns their complete incoming-reference closure.
                closure = f"{iri} (sh:property|sh:in|sh:languageIn|rdf:rest)+ ?node . FILTER(isBlank(?node))"
                if self._ask(f"""GRAPH {graph} {{ {closure} }}
                    {{ GRAPH ?foreign {{ ?node ?p ?o }} FILTER(?foreign != {graph}) }} UNION
                    {{ GRAPH ?incomingGraph {{ ?source ?link ?node }}
                       FILTER(?incomingGraph != {graph} || (?source != {iri} && NOT EXISTS {{
                           GRAPH {graph} {{ {iri} (sh:property|sh:in|sh:languageIn|rdf:rest)+ ?source . FILTER(isBlank(?source)) }}
                       }})) }}"""):
                    raise OldapErrorInUse('Reifier shape has shared or externally referenced blank nodes.')
            stamp = Xsd_dateTime.now()
            prefix = self._context.sparql_context
            if action != 'create':
                # Only owned blank property/list nodes are removed; referenced
                # resources and named predicates remain outside this closure.
                self._con.transaction_update(prefix + f'''WITH {graph}
                    DELETE {{ ?node ?p ?o }} WHERE {{
                        {{ BIND({iri} AS ?node) }} UNION
                        {{ {iri} sh:property ?node . FILTER(isBlank(?node)) }} UNION
                        {{ {iri} sh:property ?field . ?field ?listPredicate ?head .
                           ?head rdf:rest* ?node . ?node rdf:first ?value . FILTER(isBlank(?node)) }}
                        ?node ?p ?o . }}''')
            if action != 'delete':
                self._con.transaction_update(prefix + f'INSERT DATA {{ GRAPH {graph} {{ '
                    + self.create_shacl(timestamp=stamp) + f' }} GRAPH {self._project.projectShortName}:onto {{ '
                    + self.create_owl() + ' } }')
        if action != 'delete':
            self.set_creation_metadata(stamp)
        self.clear_changeset()

    def create(self):
        """Insert a new managed shape after permission and collision checks."""
        self._persist('create')

    def update(self):
        """Replace a shape with stale-write and in-use protection."""
        self._persist('update')

    def delete(self):
        """Delete an unreferenced managed shape and its owned blank nodes."""
        self._persist('delete')
