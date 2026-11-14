"""Explicit, lazy RDF 1.2 assertion annotations and transactional persistence.

Ordinary instance reads/searches never import or query this subsystem. Writes
resolve fresh policies and keep the asserted triple and owned reifiers in the
same data graph. External/blank/shared reifiers are readable but not adopted.
"""
from dataclasses import dataclass
from collections.abc import Mapping
import json
from types import MappingProxyType

from rdflib import Literal, URIRef, BNode, Graph, RDF

from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.convert2datatype import convert2datatype
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorInUse, OldapErrorNotFound, OldapErrorNoPermission, OldapErrorUpdateFailed
from oldaplib.src.helpers.property_validation import validate_value
from oldaplib.src.reifier_shape import ReifierShape
from oldaplib.src.resource_transaction import resource_query
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName

MARKER = URIRef('http://oldap.org/base#AssertionAnnotation')
REIFIES = URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies')
PROTECTED = frozenset('http://oldap.org/base#' + name for name in (
    'attachedToRole', 'hasRole', 'inProject', 'hasDataPermission',
    'createdBy', 'creationDate', 'lastModifiedBy', 'lastModificationDate')) | {str(RDF.type), str(REIFIES)}


def uri(context, value):
    """Expand a validated QName/IRI to the canonical RDF identifier."""
    value = Iri(str(value), validate=True)
    return URIRef(str(context.qname2iri(value.as_qname)) if value.is_qname else str(value))


def term_json(value):
    """Encode an RDF term without losing literal type, language or identity."""
    if isinstance(value, URIRef):
        return {'type': 'uri', 'value': str(value)}
    if isinstance(value, BNode):
        return {'type': 'bnode', 'value': str(value)}
    result = {'type': 'literal', 'value': str(value)}
    if value.language:
        result['xml:lang'] = value.language
    elif value.datatype:
        result['datatype'] = str(value.datatype)
    return result


def json_term(data, context):
    """Decode the scalar SPARQL term convention used by annotation JSON."""
    if not isinstance(data, dict) or set(data) - {'type', 'value', 'datatype', 'xml:lang'} or not isinstance(data.get('value'), str):
        raise OldapErrorValue('Expected an RDF term object with type and lexical value.')
    kind = data.get('type')
    if kind == 'uri' and set(data) == {'type', 'value'}:
        return uri(context, data['value'])
    if kind == 'bnode' and set(data) == {'type', 'value'}:
        return BNode(data['value'])
    if kind in {'literal', 'typed-literal'} and not (data.get('datatype') and data.get('xml:lang')):
        return Literal(data['value'], datatype=uri(context, data['datatype']) if data.get('datatype') else (None if data.get('xml:lang') else URIRef('http://www.w3.org/2001/XMLSchema#string')),
                       lang=data.get('xml:lang'), normalize=False)
    raise OldapErrorValue('Invalid RDF annotation term.')


@dataclass(frozen=True)
class AssertionAnnotation:
    """One independently identified assertion annotation.

    RDF terms remain typed. fields is an immutable mapping of predicate IRIs to
    tuples of terms. managed only describes the marker, not write permission;
    exclusivity and graph ownership are checked freshly on every mutation.
    """
    iri: URIRef | BNode
    property_iri: URIRef
    value: URIRef | Literal | BNode
    fields: Mapping[URIRef, tuple[URIRef | Literal | BNode, ...]]
    managed: bool = True
    asserted: bool = True

    def to_json(self):
        """Return lossless JSON, including the state of externally read records."""
        return {'iri': str(self.iri) if isinstance(self.iri, URIRef) else '_:' + str(self.iri),
                'property': str(self.property_iri), 'value': term_json(self.value),
                'fields': {str(key): [term_json(value) for value in values] for key, values in self.fields.items()},
                'managed': self.managed, 'asserted': self.asserted}


def read_annotations(instance, *, check_visibility=True):
    """Read scalar bindings only; never depend on QueryProcessor triple terms.

    Public reads recheck parent visibility in the annotation SELECT itself.
    Transactional write preparation may opt out after owning its write boundary.
    Include orphans for diagnosis, without renumbering blank-node identities.
    """
    context = Context(name=instance._con.context_name)
    excluded = ', '.join(URIRef(value).n3() for value in PROTECTED)
    quoted = (f'<<( {instance.iri.toRdf} ?predicate ?value )>>'
              if getattr(instance._con, '_resource_permissions_rdf12', False) is True
              else f'<< {instance.iri.toRdf} ?predicate ?value >>')
    access = ''
    if check_visibility:
        grant_term = (f'<<( {instance.iri.toRdf} oldap:attachedToRole ?annotationReadRole )>>'
                      if getattr(instance._con, '_resource_permissions_rdf12', False) is True
                      else f'<< {instance.iri.toRdf} oldap:attachedToRole ?annotationReadRole >>')
        access = f"""FILTER EXISTS {{
          GRAPH {instance._graph}:data {{ {instance.iri.toRdf} oldap:attachedToRole ?annotationReadRole .
            ?annotationReadGrant rdf:reifies {grant_term} ; oldap:hasDataPermission ?annotationReadPermission . }}
          GRAPH oldap:admin {{ {instance._con.userIri.toRdf} oldap:hasRole ?annotationReadRole .
            ?annotationReadPermission oldap:permissionValue ?annotationReadLevel .
            FILTER(?annotationReadLevel >= {DataPermission.DATA_VIEW.numeric.toRdf}) }}
        }}"""
    query = context.sparql_context + f'''SELECT ?reifier ?predicate ?value ?field ?item ?asserted WHERE {{
      GRAPH {instance._graph}:data {{
        ?reifier rdf:reifies {quoted} .
        FILTER(?predicate NOT IN ({excluded}))
        OPTIONAL {{ {instance.iri.toRdf} ?predicate ?value . BIND(true AS ?asserted) }}
        OPTIONAL {{ ?reifier ?field ?item . FILTER(?field != rdf:reifies) }}
      }} {access} }}'''
    groups = {}
    for row in resource_query(instance._con, query)['results']['bindings']:
        r, p, v = (json_term(row[key], context) for key in ('reifier', 'predicate', 'value'))
        key = (r, p, v)
        fields, asserted = groups.setdefault(key, ({}, 'asserted' in row))
        if 'field' in row:
            field = json_term(row['field'], context)
            fields.setdefault(field, set()).add(json_term(row['item'], context))
    result = []
    for (r, p, v), (fields, asserted) in groups.items():
        types = fields.pop(RDF.type, set())
        managed = types == {MARKER}
        if types - {MARKER}:
            fields[RDF.type] = types
        result.append(AssertionAnnotation(r, p, v, MappingProxyType({key: tuple(sorted(values, key=lambda value: value.n3()))
                                                                    for key, values in fields.items()}), managed, asserted))
    return tuple(sorted(result, key=lambda record: (str(record.iri), str(record.property_iri), record.value.n3())))


def policies(instance):
    """Resolve current property-use policies and inherited conjunctions afresh."""
    return resolve_policies(instance._con, instance.project, instance.name)


def resolve_policies(con, project, class_iri):
    """Resolve annotation constraints for a class without constructing an instance."""
    context = Context(name=con.context_name)
    graph = project.projectShortName
    pending = {Iri(str(class_iri) + 'Shape')}
    seen, result = set(), {}
    while pending - seen:
        current = pending - seen
        seen.update(current)
        terms = ' '.join(term.toRdf for term in current)
        query = context.sparql_context + f'''SELECT ?parent ?path ?shape ?required WHERE {{
          VALUES ?owner {{ {terms} }} VALUES ?graph {{ {graph}:shacl shared:shacl oldap:shacl }} GRAPH ?graph {{
            {{ ?owner sh:node ?parent }} UNION {{ ?owner sh:property ?use . ?use sh:path ?path .
               OPTIONAL {{ ?use sh:reifierShape ?shape }} OPTIONAL {{ ?use sh:reificationRequired ?required }}
               FILTER(BOUND(?shape) || BOUND(?required)) }}
          }} }}'''
        pending = set()
        for row in resource_query(con, query)['results']['bindings']:
            if 'parent' in row:
                pending.add(Iri(row['parent']['value']))
            if 'path' in row:
                predicate = json_term(row['path'], context)
                refs, required = result.setdefault(predicate, (set(), False))
                if 'shape' in row:
                    refs.add(row['shape']['value'])
                required = required or row.get('required', {}).get('value') in {'true', '1'}
                result[predicate] = refs, required
    resolved = {}
    for predicate, (refs, required) in result.items():
        if str(predicate) in PROTECTED:
            raise OldapErrorValue('System/permission predicates cannot carry business annotations.')
        shapes = []
        for ref in refs:
            name = context.iri2qname(ref)
            if name is None or str(name.prefix) not in {str(graph), 'shared'}:
                raise OldapErrorValue('Annotation shapes must be local or shared.')
            shapes.append(ReifierShape.read(con, project if str(name.prefix) == str(graph) else 'shared', name))
        if required and not shapes:
            raise OldapErrorValue('Required reification has no shape definition.')
        resolved[predicate] = shapes, required
    return resolved


def _typed_term(value, prop, context):
    if isinstance(value, dict):
        value = json_term(value, context)
    if isinstance(value, (URIRef, Literal, BNode)):
        return value
    if prop.datatype == XsdDatatypes.langString:
        literal = LangString(value)
        if len(literal) != 1:
            raise OldapErrorValue('One base annotation value must be one RDF term.')
        text = next(iter(literal))
        # LangString iteration retains its language suffix.
        lexical, language = str(text).rsplit('@', 1)
        return Literal(lexical, lang=language)
    converted = convert2datatype(value, prop.datatype, validate=True)
    graph = Graph()
    graph.parse(data=context.turtle_context + f'<urn:annotation:s> <urn:annotation:p> {converted.toRdf} .', format='turtle')
    return next(graph.objects())


def _values(instance, predicate, prop, context):
    key = context.iri2qname(str(predicate))
    return _terms(instance._values.get(key, ()), prop, context)


def _terms(values, prop, context):
    """Canonical set comparison for staged base values and history restores."""
    if isinstance(values, LangString):
        return {Literal(str(text), lang=lang.name.lower()) for lang, text in values.items()}
    return {_typed_term(value, prop, context) for value in (values or ())}


def _check_values(instance, prop, terms, context):
    """Reuse scalar constraints and enforce cardinality/type/link visibility."""
    if prop.minCount is not None and len(terms) < int(prop.minCount) or prop.maxCount is not None and len(terms) > int(prop.maxCount):
        raise OldapErrorValue(f'Annotation cardinality failed for {prop.property_class_iri}.')
    languages = []
    for term in terms:
        if isinstance(term, BNode):
            raise OldapErrorValue('Blank-node annotation values are read-only.')
        if prop.datatype is None:
            if not isinstance(term, URIRef):
                raise OldapErrorValue('Object annotation field requires an IRI.')
            value = Iri(context.iri2qname(str(term)) or str(term))
            validate_value(value, prop, annotation=True)
            if not prop.inSet:
                linked = instance.factory.read(value)
                from oldaplib.src.objectfactory import resource_class_is_or_extends
                if not resource_class_is_or_extends(type(linked), str(prop.toClass)):
                    raise OldapErrorValue(f'Linked annotation value does not have class {prop.toClass}.')
        else:
            if not isinstance(term, Literal):
                raise OldapErrorValue('Literal annotation field requires a literal.')
            expected = uri(context, prop.datatype.value)
            actual = term.datatype or (RDF.langString if term.language else URIRef('http://www.w3.org/2001/XMLSchema#string'))
            if expected != actual:
                raise OldapErrorValue(f'Wrong annotation datatype for {prop.property_class_iri}.')
            value = convert2datatype(str(term) + ('@' + term.language if term.language else ''), prop.datatype, validate=True)
            validate_value(value, prop, annotation=True)
            if term.language:
                languages.append(term.language.lower())
        kind = str(prop.nodeKind) if prop.nodeKind is not None else None
        if kind:
            kind = str(uri(context, kind)).rsplit('#', 1)[-1]
            allowed = {'IRI', 'BlankNodeOrIRI', 'IRIOrLiteral'} if isinstance(term, URIRef) else {'Literal', 'BlankNodeOrLiteral', 'IRIOrLiteral'}
            if kind not in allowed:
                raise OldapErrorValue(f'Annotation nodeKind failed for {prop.property_class_iri}.')
    if prop.uniqueLang and len(languages) != len(set(languages)):
        raise OldapErrorValue('Duplicate annotation language.')


@dataclass
class AnnotationWrite:
    """Prepared before/after state, owned by one resource transaction."""
    before: tuple[AssertionAnnotation, ...]
    after: tuple[AssertionAnnotation, ...]
    changed_properties: set[Xsd_QName]


def prepare_write(instance, operation):
    """Validate final annotated state before any normal instance mutation."""
    context = Context(name=instance._con.context_name)
    policy = policies(instance)
    before = read_annotations(instance, check_visibility=False) if operation != 'create' else ()
    edits = instance._annotation_edits or []
    if not policy and not before and not edits:
        instance._annotation_write = None
        return
    if getattr(instance._con, '_resource_permissions_rdf12', False) is not True:
        raise OldapErrorValue('Business annotations require the RDF 1.2 backend.')
    if operation != 'create':
        permission = (DataPermission.DATA_DELETE if operation == 'delete' else
                      DataPermission.DATA_UPDATE if edits else DataPermission.DATA_EXTEND)
        admin, _ = instance.check_for_permissions(AdminPermission.ADMIN_RESOURCES)
        if not admin and not instance.get_data_permission(permission):
            raise OldapErrorNoPermission('No permission to change annotated instance.')
        from oldaplib.src.xsd.xsd_datetimestamp import Xsd_dateTimeStamp
        rows = resource_query(instance._con, context.sparql_context +
            f'SELECT ?modified WHERE {{ GRAPH {instance._graph}:data {{ {instance.iri.toRdf} oldap:lastModificationDate ?modified }} }}')['results']['bindings']
        if len(rows) != 1 or Xsd_dateTimeStamp(rows[0]['modified']['value']) != instance.lastModificationDate:
            raise OldapErrorUpdateFailed('Resource changed since it was read; read it again.')
    props = {uri(context, key): prop for key, prop in instance.resolved_properties().items()}
    records = {str(record.iri): record for record in before}
    if len(records) != len(before):
        raise OldapErrorValue('Shared reifiers are read-only; import normalization is required.')
    for record in before:
        if not record.managed or not record.asserted or not isinstance(record.iri, URIRef):
            raise OldapErrorValue('External, blank-node or orphan reifiers are read-only; explicit migration is required.')
        # Ownership is checked across all named graphs; metadata outside the
        # owner graph and any incoming reference prevent generic mutation.
        query = context.sparql_context + f'''ASK {{
          {{ GRAPH ?g {{ {record.iri.n3()} ?p ?v }} FILTER(?g != {instance._graph}:data) }} UNION
          {{ GRAPH ?g {{ ?s ?p {record.iri.n3()} }} }} UNION
          {{ GRAPH ?g {{ {record.iri.n3()} rdf:reifies ?a, ?b }} FILTER(?a != ?b) }}
        }}'''
        if resource_query(instance._con, query)['boolean']:
            raise OldapErrorInUse('Annotation identity is shared or externally referenced.')
    for edit in edits:
        action, identifier, predicate, value, fields = edit
        identifier = str(uri(context, identifier))
        if action == 'remove':
            if identifier not in records:
                raise OldapErrorNotFound('Annotation not found on this instance.')
            del records[identifier]
            continue
        if action == 'replace':
            if identifier not in records:
                raise OldapErrorNotFound('Annotation not found on this instance.')
            previous = records[identifier]
            predicate, value = previous.property_iri, previous.value
        else:
            predicate = uri(context, predicate)
            if identifier in records or resource_query(instance._con, context.sparql_context +
                f'ASK {{ GRAPH ?g {{ {{ <{identifier}> ?p ?o }} UNION {{ ?s ?p <{identifier}> }} }} }}')['boolean']:
                raise OldapErrorValue('Annotation identity already exists.')
        if predicate not in policy or not policy[predicate][0] or predicate not in props:
            raise OldapErrorValue('The property has no usable reifier shape policy.')
        prop = props[predicate]
        if prop.inversePath or str(prop.toClass) == 'oldap:Dating':
            raise OldapErrorValue('Inverse and structured Dating annotations are not supported.')
        value = _typed_term(value, prop, context)
        definitions = {uri(context, key): field for shape in policy[predicate][0] for key, field in shape.properties.items()}
        normalized = {}
        for field, values in fields.items():
            field = uri(context, field)
            if field not in definitions or str(field) in PROTECTED:
                raise OldapErrorValue(f'Unknown or protected annotation field {field}.')
            if not isinstance(values, (list, tuple, set)):
                raise OldapErrorValue('Annotation field values must be arrays.')
            terms = tuple(sorted({_typed_term(item, definitions[field], context) for item in values}, key=lambda item: item.n3()))
            if terms:
                normalized[field] = terms
        records[identifier] = AssertionAnnotation(URIRef(identifier), predicate, value, MappingProxyType(normalized))
    # Removing an asserted value removes only its exclusively owned annotations.
    if operation == 'delete':
        records = {}
    else:
        for identifier, record in list(records.items()):
            prop = props.get(record.property_iri)
            if prop is None:
                raise OldapErrorValue('Stored annotation property is absent from the current model.')
            if record.value not in _values(instance, record.property_iri, prop, context):
                if any(edit[1] == identifier and edit[0] != 'remove' for edit in edits):
                    raise OldapErrorValue('Annotation must reference an asserted base value.')
                del records[identifier]
        for predicate, (shapes, required) in policy.items():
            prop = props.get(predicate)
            if prop is None:
                raise OldapErrorValue('Instance model is stale; reload before writing.')
            base = _values(instance, predicate, prop, context)
            matching = [record for record in records.values() if record.property_iri == predicate]
            if required and any(not any(record.value == value for record in matching) for value in base):
                raise OldapErrorValue('Required annotation is missing for an asserted value.')
            for record in matching:
                allowed = {uri(context, key) for shape in shapes for key in shape.properties}
                if set(record.fields) - allowed:
                    raise OldapErrorValue('Stored annotation has fields outside the current model.')
                for shape in shapes:
                    for key, field in shape.properties.items():
                        _check_values(instance, field, record.fields.get(uri(context, key), ()), context)
        if any(record.property_iri not in policy for record in records.values()):
            raise OldapErrorValue('Stored annotations have no current policy.')
    # History restore may assign an identical base set. Discard only verified
    # replacement no-ops on annotated properties; ordinary update behavior is
    # unaffected and the stale-read check above has already run.
    from oldaplib.src.enums.action import Action
    if operation == 'update':
        for key, change in list(instance._changeset.items()):
            predicate = uri(context, key)
            if predicate in policy and change.action == Action.REPLACE:
                if _terms(change.old_value, props[predicate], context) == _values(instance, predicate, props[predicate], context):
                    del instance._changeset[key]
    after = tuple(sorted(records.values(), key=lambda record: str(record.iri)))
    before_map = {str(record.iri): record for record in before}
    after_map = {str(record.iri): record for record in after}
    changed = {record.property_iri for key in before_map.keys() | after_map.keys()
               if before_map.get(key) != after_map.get(key) for record in (before_map.get(key) or after_map[key],)}
    instance._annotation_write = AnnotationWrite(before, after, {context.iri2qname(str(prop)) for prop in changed})


def apply_write(instance):
    """Persist only changed owned reifiers inside the existing transaction."""
    state = instance._annotation_write
    if state is None:
        return
    context = Context(name=instance._con.context_name)
    before = {str(record.iri): record for record in state.before}
    after = {str(record.iri): record for record in state.after}
    commands = []
    for key in sorted(before.keys() | after.keys()):
        if before.get(key) == after.get(key):
            continue
        if key in before:
            commands.append(f'DELETE WHERE {{ GRAPH {instance._graph}:data {{ <{key}> ?p ?o }} }}')
        if key in after:
            record = after[key]
            triples = [f'{record.iri.n3()} a oldap:AssertionAnnotation ; rdf:reifies <<( {instance.iri.toRdf} {record.property_iri.n3()} {record.value.n3()} )>> .']
            triples.extend(f'{record.iri.n3()} {field.n3()} {value.n3()} .' for field, values in record.fields.items() for value in values)
            commands.append(f'INSERT DATA {{ GRAPH {instance._graph}:data {{ {" ".join(triples)} }} }}')
    if commands:
        instance._con.transaction_update(context.sparql_context + ';\n'.join(commands))


def snapshot(records, predicate):
    """Stable JSON used as an opaque RDF literal in property history."""
    return json.dumps([record.to_json() for record in records if record.property_iri == predicate], sort_keys=True, separators=(',', ':'))


def restore_annotations(instance, predicate, records):
    """Stage a complete historical group using fresh, unshared identities."""
    context = Context(name=instance._con.context_name)
    predicate = uri(context, predicate)
    current = [record for record in read_annotations(instance) if record.property_iri == predicate]
    def contents(items):
        return sorted(json.dumps({key: value for key, value in item.items() if key != 'iri'}, sort_keys=True) for item in items)
    if contents([record.to_json() for record in current]) == contents(records):
        return
    for record in current:
        instance.remove_annotation(str(record.iri))
    for record in records:
        instance.add_annotation(str(predicate), record['value'], record['fields'])
