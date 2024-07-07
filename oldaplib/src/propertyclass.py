"""
:Author: Lukas Rosenthaler <lukas.rosenthaler@unibas.ch>
:Copyright: © Lukas Rosenthaler (2023, 2024)
"""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pprint import pprint
from typing import Callable, Self, Any

from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.dtypes.xsdset import XsdSet
from oldaplib.src.enums.owlpropertytype import OwlPropertyType
from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.action import Action
from oldaplib.src.helpers.numeric import Numeric
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_float import Xsd_float
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNotFound, OldapErrorAlreadyExists, OldapErrorUpdateFailed, OldapErrorValue, OldapErrorInconsistency
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.helpers.query_processor import RowType, QueryProcessor
from oldaplib.src.helpers.semantic_version import SemanticVersion
from oldaplib.src.helpers.tools import RdfModifyItem, RdfModifyProp
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model, AttributeChange
from oldaplib.src.xsd.xsd_string import Xsd_string

PropTypes = Iri | OwlPropertyType | XsdDatatypes | LangString | Xsd_string | Xsd_integer | Xsd_boolean | LanguageIn | XsdSet | Numeric | None
PropClassAttrContainer = dict[PropClassAttr, PropTypes]
Attributes = dict[Iri, PropTypes]

@dataclass
class HasPropertyData:
    refprop: Iri | None = None
    minCount: Xsd_integer | None = None
    maxCount: Xsd_integer | None = None
    order: Xsd_decimal | None = None
    group: Iri | None = None

    def create_shacl(self, indent: int = 0, indent_inc: int = 4):
        blank = ''
        sparql = ''
        if self.minCount is not None:
            sparql += f' ;\n{blank:{indent * indent_inc}}sh:minCount {self.minCount.toRdf}'
        if self.maxCount is not None:
            sparql += f' ;\n{blank:{indent * indent_inc}}sh:maxCount {self.maxCount.toRdf}'
        if self.order is not None:
            sparql += f' ;\n{blank:{indent * indent_inc}}sh:order {self.order.toRdf}'
        if self.group is not None:
            sparql += f' ;\n{blank:{indent * indent_inc}}sh:group {self.group.toRdf}'
        return sparql

    def create_owl(self, indent: int = 0, indent_inc: int = 4):
        def create_owl(self, indent: int = 0, indent_inc: int = 4):
            blank = ''
            sparql = ''
            min_count = Xsd_nonNegativeInteger(int(self.minCount)) if self.minCount else None
            max_count = Xsd_nonNegativeInteger(int(self.maxCount)) if self.maxCount else None

            if min_count and max_count and min_count == max_count:
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:qualifiedCardinality {min_count.toRdf}'
            else:
                if min_count:
                    sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:minQualifiedCardinality {min_count.toRdf}'
                if max_count:
                    sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:maxQualifiedCardinality {max_count.toRdf}'
            return sparql


#@strict
class PropertyClass(Model, Notify):
    """
    This class implements a property as used by OMASlib. There are 2 types of properties:
    - _External properties_: External properties are defined outside a specific resource class
      and can be (re-)used by several resources. In SHACL, they are defined as "sh:PropertyShape"
      instance.
    - _Internal or exclusive properties_: These Properties ate defined as blank node within the
      definition of a resource class. A "sh:property" predicate points to the blank node that
      defines the property. These properties cannot be re-used!

    *NOTE*: External properties have to be defined and created before being referenced as
    property within a resource definition. In order to reference an external property, the
    QName has to be used!

    """
    _graph: Xsd_NCName
    _project: Project
    _property_class_iri: Iri | None
    _internal: Iri | None
    _force_external: bool
    _attributes: PropClassAttrContainer
    _test_in_use: bool
    _notifier: Callable[[type], None] | None

    #
    # The following attributes of this class cannot be set explicitely by the used
    # They are automatically managed by the OMAS system
    #
    __version: SemanticVersion
    __from_triplestore: bool

    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | str | None = None,
                 created: Xsd_dateTime | datetime | str | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | datetime | str | None = None,
                 project: Project | Iri | Xsd_NCName | str,
                 property_class_iri: Iri | str | None = None,
                 notifier: Callable[[PropClassAttr], None] | None = None,
                 notify_data: PropClassAttr | None = None,
                 **kwargs):
        Model.__init__(self,
                       connection=con,
                       creator=creator,
                       created=created,
                       contributor=contributor,
                       modified=modified)
        Notify.__init__(self, notifier, notify_data)

        if isinstance(project, Project):
            self._project = project
        else:
            self._project = Project.read(self._con, project)
        context = Context(name=self._con.context_name)
        context[self._project.projectShortName] = self._project.namespaceIri
        context.use(self._project.projectShortName)
        self._graph = self._project.projectShortName

        self._property_class_iri = Iri(property_class_iri) if property_class_iri else None
        self.set_attributes(kwargs, PropClassAttr)

        #
        # Consistency checks
        #
        if self._attributes.get(PropClassAttr.LANGUAGE_IN) is not None:
            if self._attributes.get(PropClassAttr.DATATYPE) is None:
                self._attributes[PropClassAttr.DATATYPE] = XsdDatatypes.langString
            elif self._attributes[PropClassAttr.DATATYPE] != XsdDatatypes.langString:
                raise OldapErrorValue(f'Using restriction LANGUAGE_IN requires DATATYPE "rdf:langString", not "{self._attributes[PropClassAttr.DATATYPE].value}"')
        if self._attributes.get(PropClassAttr.DATATYPE) is not None and self._attributes.get(PropClassAttr.CLASS) is not None:
            raise OldapErrorInconsistency(f'It\'s not possible to use both DATATYPE="{self._attributes[PropClassAttr.DATATYPE]}" and CLASS={self._attributes[PropClassAttr.CLASS]} restrictions.')

        # setting property type for OWL which distinguished between Data- and Object-properties
        if self._attributes.get(PropClassAttr.CLASS) is not None:
            self._attributes[PropClassAttr.TYPE] = OwlPropertyType.OwlObjectProperty
            if self._attributes.get(PropClassAttr.DATATYPE) is not None:
                raise OldapError(f'Datatype "{self._attributes.get(PropClassAttr.DATATYPE)}" not possible for OwlObjectProperty')
        else:
            self._attributes[PropClassAttr.TYPE] = OwlPropertyType.OwlDataProperty

        #
        # set the class properties
        #
        for attr in PropClassAttr:
            name = attr.value.fragment
            if name == 'in':
                name = 'inSet'
            elif name == 'class':
                name = 'toClass'
            setattr(PropertyClass, name, property(
                partial(PropertyClass._get_value, attr=attr),
                partial(PropertyClass._set_value, attr=attr),
                partial(PropertyClass._del_value, attr=attr)))

        self._test_in_use = False
        self._internal = None
        self._force_external = False
        self.__version = SemanticVersion()
        self.__from_triplestore = False

    def check_consistency(self, attr: PropClassAttr, value: Any) -> None:
        if attr == PropClassAttr.CLASS:
            if self._attributes.get(PropClassAttr.DATATYPE) is not None:
                self._changeset[PropClassAttr.DATATYPE] = AttributeChange(self._attributes[PropClassAttr.DATATYPE], Action.DELETE)
                del self._attributes[PropClassAttr.DATATYPE]
            if self._attributes.get(PropClassAttr.CLASS) is not None:
                self._changeset[PropClassAttr.CLASS] = AttributeChange(self._attributes[PropClassAttr.CLASS], Action.REPLACE)
            else:
                self._changeset[PropClassAttr.CLASS] = AttributeChange(None, Action.CREATE)
            self._attributes[PropClassAttr.CLASS] = value
        elif attr == PropClassAttr.DATATYPE:
            if self._attributes.get(PropClassAttr.CLASS) is not None:
                self._changeset[PropClassAttr.CLASS] = AttributeChange(self._attributes[PropClassAttr.CLASS], Action.DELETE)
                del self._attributes[PropClassAttr.CLASS]
            if self._attributes.get(PropClassAttr.DATATYPE) is not None:
                self._changeset[PropClassAttr.DATATYPE] = AttributeChange(self._attributes[PropClassAttr.DATATYPE], Action.REPLACE)
            else:
                self._changeset[PropClassAttr.DATATYPE] = AttributeChange(None, Action.CREATE)
            self._attributes[PropClassAttr.DATATYPE] = value

    def _change_setter(self: Self, attr: PropClassAttr, value: PropTypes) -> None:
        if not isinstance(attr, PropClassAttr):
            raise OldapError(f'Unsupported prop {attr}')
        if self._attributes.get(attr) == value:
            return
        super()._change_setter(attr, value)
        if getattr(value, 'set_notifier', None) is not None:
            value.set_notifier(self.notifier, attr)

    def __len__(self) -> int:
        return len(self._attributes)

    def __str__(self) -> str:
        propstr = f'Property: {str(self._property_class_iri)};'
        for attr, value in self._attributes.items():
            propstr += f' {attr.value}: {value};'
        propstr += f' internal: {self._internal};'
        return propstr

    @property
    def property_class_iri(self) -> Iri:
        return self._property_class_iri

    @property
    def version(self) -> SemanticVersion:
        return self.__version

    @property
    def internal(self) -> Iri | None:
        return self._internal

    def force_external(self):
        self._force_external = True

    @property
    def from_triplestore(self) -> bool:
        return self.__from_triplestore

    def undo(self, attr: PropClassAttr | None = None) -> None:
        if attr is None:
            for p, change in self._changeset.items():
                if change.action == Action.MODIFY:
                    self._attributes[p].undo()
                    if len(self._attributes[p]) == 0:
                        del self._attributes[p]
                else:
                    if change.action == Action.CREATE:
                        del self._attributes[p]
                    else:
                        self._attributes[p] = change.old_value
            self._changeset = {}
        else:
            if self._changeset.get(attr) is not None:  # this prop really changed...
                if self._changeset[attr].action == Action.MODIFY:
                    self._attributes[attr].undo()
                    if len(self._attributes[attr]) == 0:
                        del self._attributes[attr]
                elif self._changeset[attr].action == Action.CREATE:
                    del self._attributes[attr]
                else:
                    self._attributes[attr] = self._changeset[attr].old_value
                del self._changeset[attr]


    def notifier(self, attr: PropClassAttr) -> None:
        if attr.datatype in [XsdSet, LanguageIn]:
            # we can *not* modify sets, we have to replace them if an item is added or discarded
            if self._changeset.get(attr) is None:
                tmp = deepcopy(self._attributes[attr])
                self._changeset[attr] = AttributeChange(tmp, Action.REPLACE)
        else:
            self._changeset[attr] = AttributeChange(None, Action.MODIFY)
        self.notify()

    @property
    def in_use(self):
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT (COUNT(?rinstances) as ?nrinstances)
        WHERE {{
            ?rinstances {self._property_class_iri.toRdf} ?value
        }} LIMIT 2
        """
        jsonres = self._con.query(query)
        res = QueryProcessor(jsonres)
        if len(res) != 1:
            raise OldapError('Internal Error in "propertyClass.in_use"')
        for r in res:
            if r['nresinstances'] > 0:
                return True
            else:
                return False

    @staticmethod
    def process_triple(r: RowType, attributes: Attributes) -> None:
        attriri = r['attriri']
        if r['attriri'].fragment == 'languageIn':
            if attributes.get(attriri) is None:
                attributes[attriri] = LanguageIn()
            attributes[attriri].add(r['oo'])
        elif r['attriri'].fragment == 'in':
            if attributes.get(attriri) is None:
                attributes[attriri] = XsdSet()
            attributes[attriri].add(r['oo'])
        else:
            if isinstance(r['value'], Xsd_string) and r['value'].lang is not None:
                if attributes.get(attriri) is None:
                    attributes[attriri] = LangString()
                try:
                    attributes[attriri].add(r['value'])
                except AttributeError as err:
                    raise OldapError(f'Invalid value for attribute {attriri}: {err}.')
            else:
                if attributes.get(attriri) is not None:
                    raise OldapError(f'Property attribute "{attriri}" already defined (value="{r['value']}", type="{type(r['value']).__name__}").')
                attributes[attriri] = r['value']

    @staticmethod
    def __query_shacl(con: IConnection, graph: Xsd_NCName, property_class_iri: Iri) -> Attributes:
        context = Context(name=con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT ?attriri ?value ?oo
        FROM {graph}:shacl
        WHERE {{
            BIND({property_class_iri}Shape AS ?shape)
            ?shape ?attriri ?value .
            OPTIONAL {{
                ?value rdf:rest*/rdf:first ?oo
            }}
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OldapErrorNotFound(f'Property "{property_class_iri}" not found.')
        attributes: Attributes = {}
        for r in res:
            PropertyClass.process_triple(r, attributes)
        return attributes

    def parse_shacl(self, attributes: Attributes) -> HasPropertyData | None:
        """
        Read the SHACL of a non-exclusive (shared) property (that is a sh:PropertyNode definition)
        :return:
        """
        #
        # Create a set of all PropertyClassProp-strings, e.g. {"sh:path", "sh:datatype" etc.}
        #
        refprop: Iri | None = None
        minCount: Xsd_integer | None = None
        maxCount: Xsd_integer | None = None
        order: Xsd_decimal | None = None
        group: Iri | None = None
        propkeys = {Iri(x.value) for x in PropClassAttr}
        for key, val in attributes.items():
            if key == 'rdf:type':
                if val != 'sh:PropertyShape':
                    raise OldapError(f'Inconsistency, expected "sh:PropertyType", got "{val}".')
                continue
            elif key == 'sh:path':
                if isinstance(val, Iri):
                    self._property_class_iri = val
                else:
                    raise OldapError(f'Inconsistency in SHACL "sh:path" of "{self._property_class_iri}" ->"{val}"')
            elif key == 'dcterms:hasVersion':
                if isinstance(val, Xsd_string):
                    self.__version = SemanticVersion.fromString(str(val))
                else:
                    raise OldapError(f'Inconsistency in SHACL "dcterms:hasVersion"')
            elif key == 'dcterms:creator':
                if isinstance(val, Iri):
                    self._creator = val
                else:
                    raise OldapError(f'Inconsistency in SHACL "dcterms:creator"')
            elif key == 'dcterms:created':
                if isinstance(val, Xsd_dateTime):
                    self._created = val
                else:
                    raise OldapError(f'Inconsistency in SHACL "dcterms:created"')
            elif key == 'dcterms:contributor':
                if isinstance(val, Iri):
                    self._contributor = val
                else:
                    raise OldapError(f'Inconsistency in SHACL "dcterms:contributor"')
            elif key == 'dcterms:modified':
                if isinstance(val, Xsd_dateTime):
                    self._modified = val
                else:
                    raise OldapError(f'Inconsistency in SHACL "dcterms:modified"')
            elif key == 'sh:node':
                if str(val).endswith("Shape"):
                    refprop = Iri(str(val)[:-5], validate=False)
                else:
                    refprop = val
            elif key == 'sh:minCount':
                minCount = val
            elif key == 'sh:maxCount':
                maxCount = val
            elif key == 'sh:order':
                order = val
            elif key == 'sh:group':
                group = val
            elif key in propkeys:
                attr = PropClassAttr.from_value(key.as_qname)
                if attr.datatype == Numeric:
                    if not isinstance(val, (Xsd_integer, Xsd_float)):
                        raise OldapErrorInconsistency(f'SHACL inconsistency: "{attr.value}" expects a "Xsd:integer" or "Xsd:float", but got "{type(val).__name__}".')
                else:
                    self._attributes[attr] = attr.datatype(val)

        if refprop:
            return HasPropertyData(refprop=refprop,
                                   minCount=minCount,
                                   maxCount=maxCount,
                                   order=order,
                                   group=group)

        if self._attributes.get(PropClassAttr.CLASS) is not None:
            self._attributes[PropClassAttr.TYPE] = OwlPropertyType.OwlObjectProperty
            dt = self._attributes.get(PropClassAttr.DATATYPE)
            if dt and (dt != XsdDatatypes.anyURI and dt != XsdDatatypes.QName):
                raise OldapError(f'Datatype "{dt}" not valid for OwlObjectProperty')
        else:
            self._attributes[PropClassAttr.TYPE] = OwlPropertyType.OwlDataProperty
        for attr, value in self._attributes.items():
            if getattr(value, 'set_notifier', None) is not None:
                value.set_notifier(self.notifier, attr)
        self.__from_triplestore = True
        return HasPropertyData(refprop, minCount, maxCount, order, group)

    def read_owl(self):
        context = Context(name=self._con.context_name)
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?p ?o
        FROM {self._graph}:onto
        WHERE {{
            {self._property_class_iri} ?p ?o
        }}
        """
        jsonobj = self._con.query(query1)
        res = QueryProcessor(context=context, query_result=jsonobj)
        datatype = None
        to_node_iri = None
        for r in res:
            attr = r['p']
            obj = r['o']
            match attr:
                case 'rdf:type':
                    if obj == 'owl:DatatypeProperty':
                        self._attributes[PropClassAttr.TYPE] = OwlPropertyType.OwlDataProperty
                    elif obj == 'owl:ObjectProperty':
                        self._attributes[PropClassAttr.TYPE] = OwlPropertyType.OwlObjectProperty
                case 'owl:subPropertyOf':
                    self._attributes[PropClassAttr.SUBPROPERTY_OF] = obj
                case 'rdfs:range':
                    if obj.prefix == 'xsd' or obj.prefix == 'rdf':
                        datatype = obj
                    else:
                        to_node_iri = obj
                case 'rdfs:domain':
                    self._internal = obj
                case 'dcterms:creator':
                    if self._creator != obj:
                        raise OldapError(f'Inconsistency between SHACL and OWL: creator "{self._creator}" vs "{obj}" for property "{self._property_class_iri}".')
                case 'dcterms:created':
                    dt = obj
                    if self._created != dt:
                        raise OldapError(f'Inconsistency between SHACL and OWL: created "{self._created}" vs "{dt}".')
                case 'dcterms:contributor':
                    if self._creator != obj:
                        raise OldapError(f'Inconsistency between SHACL and OWL: contributor "{self._contributor}" vs "{obj}".')
                case 'dcterms:modified':
                    dt = obj
                    if self._modified != dt:
                        raise OldapError(f'Inconsistency between SHACL and OWL: created "{self._modified}" vs "{dt}".')
        #
        # Consistency checks
        #
        if self._attributes[PropClassAttr.TYPE] == OwlPropertyType.OwlDataProperty:
            if not datatype:
                raise OldapError(f'OwlDataProperty "{self._property_class_iri}" has no rdfs:range datatype defined!')
            if datatype != self._attributes.get(PropClassAttr.DATATYPE).value:
                raise OldapError(
                    f'Property "{self._property_class_iri}" has inconsistent datatype definitions: OWL: "{datatype}" vs. SHACL: "{self._attributes[PropClassAttr.DATATYPE].value}"')
        if self._attributes[PropClassAttr.TYPE] == OwlPropertyType.OwlObjectProperty:
            if not to_node_iri:
                raise OldapError(f'OwlObjectProperty "{self._property_class_iri}" has no rdfs:range resource class defined!')
            if to_node_iri != self._attributes.get(PropClassAttr.CLASS):
                raise OldapError(
                    f'Property "{self._property_class_iri}" has inconsistent object type definition: OWL: "{to_node_iri}" vs. SHACL: "{self._attributes.get(PropClassAttr.CLASS)}".')

    @classmethod
    def read(cls, con: IConnection,
             project: Project | Iri | Xsd_NCName | str,
             property_class_iri: Iri) -> Self:
        property = cls(con=con, project=project, property_class_iri=property_class_iri)
        attributes = PropertyClass.__query_shacl(con, property._graph, property_class_iri)
        property.parse_shacl(attributes=attributes)
        property.read_owl()
        return property

    def read_modified_shacl(self, *,
                            context: Context,
                            graph: Xsd_NCName,
                            indent: int = 0, indent_inc: int = 4) -> Xsd_dateTime | None:
        blank = ''
        sparql = context.sparql_context
        owlclass_iri = self._internal
        sparql += f"{blank:{indent * indent_inc}}SELECT ?modified\n"
        sparql += f"{blank:{indent * indent_inc}}FROM {graph}:shacl\n"
        sparql += f"{blank:{indent * indent_inc}}WHERE {{\n"
        if owlclass_iri:
            sparql += f"{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n"
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:path {self._property_class_iri} .\n'
        else:
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri}Shape as ?prop)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified .\n'
        sparql += f"{blank:{indent * indent_inc}}}}"
        jsonobj = self._con.transaction_query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            return None
        return res[0].get('modified')

    def read_modified_owl(self, *,
                          context: Context,
                          graph: Xsd_NCName,
                          indent: int = 0, indent_inc: int = 4) -> Xsd_dateTime | None:
        blank = ''
        sparql = context.sparql_context
        owlclass_iri = self._internal
        sparql += f"{blank:{indent * indent_inc}}SELECT ?modified\n"
        sparql += f"{blank:{indent * indent_inc}}FROM {graph}:onto\n"
        sparql += f"{blank:{indent * indent_inc}}WHERE {{\n"
        sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri} AS ?prop)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified .\n'
        sparql += f"{blank:{indent * indent_inc}}}}"
        jsonobj = self._con.transaction_query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            return None
        return res[0].get('modified')


    def property_node_shacl(self, *,
                            timestamp: Xsd_dateTime,
                            bnode: Xsd_QName | None = None,
                            haspropdata: HasPropertyData | None = None,
                            indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{(indent + 1) * indent_inc}}# >>PropertyClass.property_node_shacl()'
        if bnode:
            sparql += f'\n{blank:{(indent + 1) * indent_inc}} {bnode} sh:path {self._property_class_iri.toRdf}'
        else:
            sparql += f'\n{blank:{(indent + 1) * indent_inc}}sh:path {self._property_class_iri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:hasVersion {self.__version.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        for prop, value in self._attributes.items():
            if prop == PropClassAttr.TYPE:
                continue
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}{prop.value} {value.toRdf}'
        if haspropdata:
            sparql += haspropdata.create_shacl(indent=indent + 1)
        return sparql

    def create_shacl(self, *,
                     timestamp: Xsd_dateTime,
                     owlclass_iri: Iri | None = None,
                     haspropdata: HasPropertyData | None = None,
                     indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'\n{blank:{indent * indent_inc}}# PropertyClass.create_shacl()'
        if owlclass_iri is None:  # standalone property! Therefor no minCount, maxCount!
            sparql += f'\n{blank:{indent * indent_inc}}{self._property_class_iri}Shape a sh:PropertyShape ;\n'
            sparql += self.property_node_shacl(timestamp=timestamp,
                                               haspropdata=haspropdata,
                                               indent=indent, indent_inc=indent_inc)
        else:
            bnode = Xsd_QName('_:propnode')
            sparql += f'\n{blank:{indent * indent_inc}}{owlclass_iri}Shape sh:property {bnode} .\n'
            sparql += self.property_node_shacl(timestamp=timestamp, bnode=bnode,
                                               haspropdata=haspropdata,
                                               indent=indent, indent_inc=indent_inc)
        sparql += ' .\n'
        return sparql

    def create_owl_part1(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent * indent_inc}}{self._property_class_iri.toRdf} rdf:type {self._attributes[PropClassAttr.TYPE].value}'
        if self._attributes.get(PropClassAttr.SUBPROPERTY_OF):
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:subPropertyOf {self._attributes[PropClassAttr.SUBPROPERTY_OF].toRdf}'
        if self._internal:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:domain {self._internal.toRdf}'
        if self._attributes.get(PropClassAttr.TYPE) == OwlPropertyType.OwlDataProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:range {self._attributes[PropClassAttr.DATATYPE].value}'
        elif self._attributes.get(PropClassAttr.TYPE) == OwlPropertyType.OwlObjectProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:range {self._attributes[PropClassAttr.CLASS].toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql += ' .\n'
        return sparql

    def create_owl_part2(self, *,
                         haspropdata: HasPropertyData | None = None,
                         indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent * indent_inc}}[\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}rdf:type owl:Restriction ;\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}owl:onProperty {self._property_class_iri.toRdf}'

        if haspropdata.minCount and haspropdata.maxCount  and haspropdata.minCount == haspropdata.maxCount:
            sparql += f' ;\n{blank:{(indent + 1)*indent_inc}}owl:qualifiedCardinality {haspropdata.minCount.toRdf}'
        else:
            if haspropdata.minCount:
                sparql += f' ;\n{blank:{(indent + 1)*indent_inc}}owl:minQualifiedCardinality {haspropdata.minCount.toRdf}'
            if haspropdata.maxCount:
                sparql += f' ;\n{blank:{(indent + 1)*indent_inc}}owl:maxQualifiedCardinality {haspropdata.maxCount.toRdf}'
        #
        # (NOTE: owl:onClass and owl:onDatatype can be used only in a restriction and are "local" to the use
        # of the property within the given resource. However, rdfs:range is "global" for all use of this property!
        #
        if self._attributes[PropClassAttr.TYPE] == OwlPropertyType.OwlDataProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:onDatatype {self._attributes[PropClassAttr.DATATYPE].value}'
        elif self._attributes[PropClassAttr.TYPE] == OwlPropertyType.OwlObjectProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:onClass {self._attributes[PropClassAttr.CLASS]}'
        sparql += f' ;\n{blank:{indent * indent_inc}}]'
        return sparql

    def set_creation_metadata(self, timestamp: Xsd_dateTime):
        self._created = timestamp
        self._creator = self._con.userIri
        self._modified = timestamp
        self._contributor = self._con.userIri
        self.__from_triplestore = True


    def create(self, *,
               haspropdata: HasPropertyData | None = None,
               indent: int = 0, indent_inc: int = 4) -> None:
        if self.__from_triplestore:
            raise OldapErrorAlreadyExists(f'Cannot create property that was read from TS before (property: {self._property_class_iri}')
        timestamp = Xsd_dateTime.now()
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:shacl {{\n'
        if self._internal is not None:  # internal property, add minCount, maxCount if defined
            sparql += self.create_shacl(timestamp=timestamp,
                                        owlclass_iri=self._internal,
                                        haspropdata=haspropdata,
                                        indent=2)
        else:  # external standalone (reusable) property -> no minCount, maxCount
            sparql += self.create_shacl(timestamp=timestamp,
                                        indent=2)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:onto {{\n'
        sparql += self.create_owl_part1(timestamp=timestamp, indent=2)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}}}\n'
        self.set_creation_metadata(timestamp)

        try:
            self._con.transaction_start()
        except OldapError as err:
            self._con.transaction_abort()
            raise
        try:
            r = self.read_modified_shacl(context=context, graph=self._graph)
        except OldapError as err:
            self._con.transaction_abort()
            raise
        if r is not None:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'Property "{self._property_class_iri}" already exists.')
        try:
            self._con.transaction_update(sparql)
        except OldapError as err:
            self._con.transaction_abort()
            raise
        try:
            modtime_shacl = self.read_modified_shacl(context=context, graph=self._graph)
            modtime_owl = self.read_modified_owl(context=context, graph=self._graph)
        except OldapError as err:
            self._con.transaction_abort()
            raise
        if modtime_shacl == timestamp and modtime_owl == timestamp:
            self._con.transaction_commit()
        else:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed(f"Update of RDF didn't work!")

    def write_as_trig(self, filename: str, indent: int = 0, indent_inc: int = 4) -> None:
        with open(filename, 'w') as f:
            timestamp = Xsd_dateTime().now()
            blank = ''
            context = Context(name=self._con.context_name)
            f.write(context.turtle_context)

            f.write(f'{blank:{indent * indent_inc}}{self._graph}:shacl {{\n')
            if self._internal is not None:
                f.write(self.create_shacl(timestamp=timestamp, owlclass_iri=self._internal, indent=2))
            else:
                f.write(self.create_shacl(timestamp=timestamp, indent=2))
            f.write(f'{blank:{indent * indent_inc}}}}\n')

            f.write(f'{blank:{indent * indent_inc}}{self._graph}:onto {{\n')
            f.write(self.create_owl_part1(timestamp=timestamp, indent=2))
            f.write(f'{blank:{indent * indent_inc}}}}\n')

    def update_shacl(self, *,
                     owlclass_iri: Iri | None = None,
                     timestamp: Xsd_dateTime,
                     indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql_list = []
        for prop, change in self._changeset.items():
            sparql = f'#\n# SHACL\n# Process "{prop.value}" with Action "{change.action.value}"\n#\n'
            if change.action == Action.MODIFY:
                if prop.datatype == LangString:
                    sparql += self._attributes[prop].update_shacl(graph=self._graph,
                                                                  owlclass_iri=owlclass_iri,
                                                                  prop_iri=self._property_class_iri,
                                                                  attr=prop,
                                                                  modified=self._modified,
                                                                  indent=indent, indent_inc=indent_inc)
                else:
                    raise OldapError(f'SHACL property {prop.value} should not have update action "MODIFY" ({prop.datatype}).')
                sparql_list.append(sparql)
            else:
                if change.action == Action.DELETE:
                    old_value = '?val'
                    new_value = None
                elif change.action == Action.CREATE:
                    old_value = None
                    new_value = self._attributes[prop].toRdf
                elif change.action == Action.REPLACE:
                    old_value = change.old_value.toRdf
                    new_value = self._attributes[prop].toRdf
                else:
                    raise OldapError(f'An unexpected Action occured: {change.action} for {prop.value}.')
                ele = RdfModifyItem(prop.value, old_value, new_value)
                if prop.datatype in {XsdSet, LanguageIn}:
                    sparql += RdfModifyProp.replace_rdfset(action=change.action,
                                                           graph=self._graph,
                                                           owlclass_iri=owlclass_iri,
                                                           pclass_iri=self._property_class_iri,
                                                           ele=ele,
                                                           last_modified=self._modified)
                else:
                    sparql += RdfModifyProp.shacl(action=change.action,
                                                  graph=self._graph,
                                                  owlclass_iri=owlclass_iri,
                                                  pclass_iri=self._property_class_iri,
                                                  ele=ele,
                                                  last_modified=self._modified)
                sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor in {self._graph}:shacl\n#\n'
        sparql += RdfModifyProp.shacl(action=Action.REPLACE if self._contributor else Action.CREATE,
                                      graph=self._graph,
                                      owlclass_iri=owlclass_iri,
                                      pclass_iri=self._property_class_iri,
                                      ele=RdfModifyItem('dcterms:contributor', f'{self._contributor.toRdf}', f'{self._con.userIri.toRdf}'),
                                      last_modified=self._modified)
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified in {self._graph}:shacl\n#\n'
        sparql += RdfModifyProp.shacl(action=Action.REPLACE if self._modified else Action.CREATE,
                                      graph=self._graph,
                                      owlclass_iri=owlclass_iri,
                                      pclass_iri=self._property_class_iri,
                                      ele=RdfModifyItem('dcterms:modified', f'{self._modified.toRdf}', f'{timestamp.toRdf}'),
                                      last_modified=self._modified)
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def update_owl(self, *,
                   owlclass_iri: Xsd_QName | None = None,
                   timestamp: Xsd_dateTime,
                   indent: int = 0, indent_inc: int = 4) -> str:
        owl_propclass_attributes = {PropClassAttr.SUBPROPERTY_OF,  # should be in OWL ontology
                                    PropClassAttr.DATATYPE,  # used for rdfs:range in OWL ontology
                                    PropClassAttr.CLASS}  # used for rdfs:range in OWL ontology
        owl_prop = {PropClassAttr.SUBPROPERTY_OF: PropClassAttr.SUBPROPERTY_OF.value,
                    PropClassAttr.DATATYPE: "rdfs:range",
                    PropClassAttr.CLASS: "rdfs:range"}
        blank = ''
        sparql_list = []
        for prop, change in self._changeset.items():
            if prop in owl_propclass_attributes:
                sparql = f'#\n# OWL:\n# Process "{owl_prop[prop]}" with Action "{change.action.value}"\n#\n'
                ele = RdfModifyItem(property=owl_prop[prop],
                                    old_value=str(change.old_value) if change.action != Action.CREATE else None,
                                    new_value=str(self._attributes[prop]) if change.action != Action.DELETE else None)
                sparql += RdfModifyProp.onto(action=change.action,
                                             graph=self._graph,
                                             owlclass_iri=owlclass_iri,
                                             pclass_iri=self._property_class_iri,
                                             ele=ele,
                                             last_modified=self._modified,
                                             indent=indent, indent_inc=indent_inc)
                sparql_list.append(sparql)

            if prop == PropClassAttr.DATATYPE or prop == PropClassAttr.CLASS:
                ele: RdfModifyItem
                if self._attributes.get(PropClassAttr.CLASS):
                    ele = RdfModifyItem('rdf:type', 'owl:DatatypeProperty', 'owl:ObjectProperty')
                else:
                    ele = RdfModifyItem('rdf:type', 'owl:ObjectProperty', 'owl:DatatypeProperty')
                sparql = f'#\n# OWL:\n# Correct OWL property type with Action "{change.action.value}\n#\n'
                sparql += RdfModifyProp.onto(action=Action.REPLACE,
                                             graph=self._graph,
                                             owlclass_iri=owlclass_iri,
                                             pclass_iri=self._property_class_iri,
                                             ele=ele,
                                             last_modified=self._modified,
                                             indent=indent, indent_inc=indent_inc)

                sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor {self._graph}:onto\n#\n'
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:onto\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:contributor {self._contributor.toRdf}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:contributor {self._con.userIri.toRdf}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri} AS ?prop)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified in {self._graph}:onto\n#\n'
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:onto\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified {timestamp.toRdf}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri} AS ?prop)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def update(self) -> None:
        timestamp = Xsd_dateTime.now()

        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context

        self._con.transaction_start()

        sparql += self.update_shacl(owlclass_iri=self._internal,
                                    timestamp=timestamp)
        sparql += " ;\n"
        sparql += self.update_owl(owlclass_iri=self._internal,
                                  timestamp=timestamp)
        try:
            self._con.transaction_update(sparql)
        except OldapError as e:
            self._con.transaction_abort()
            raise
        try:
            modtime_shacl = self.read_modified_shacl(context=context, graph=self._graph)
        except OldapError as e:
            self._con.transaction_abort()
            raise
        try:
            modtime_owl = self.read_modified_owl(context=context, graph=self._graph)
        except OldapError as e:
            self._con.transaction_abort()
            raise

        if modtime_shacl == timestamp and modtime_owl == timestamp:
            self._con.transaction_commit()
            self._modified = timestamp
            self._contributor = self._con.userIri
            for prop, change in self._changeset.items():
                if change.action == Action.MODIFY:
                    self._attributes[prop].changeset_clear()
            self._changeset = {}
        else:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed(f'Update RDF of "{self._property_class_iri}" didn\'t work: shacl={modtime_shacl} owl={modtime_owl} timestamp={timestamp}')

    def delete_shacl(self, *,
                     indent: int = 0, indent_inc: int = 4) -> str:
        #
        # TODO: Test here if property is in use
        #
        owlclass_iri = self._internal
        blank = ''
        sparql_list = []
        sparql = f'#\n# Delete {self._property_class_iri} from shacl\n#\n'
        #
        # First we delete all list (sh:languageIn/sh:in restrictions) if existing
        #
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:shacl\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?z rdf:first ?head ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}rdf:rest ?tail .\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        sparql += f'{blank:{indent * indent_inc}}WHERE{{\n'
        if owlclass_iri is not None:
            sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode sh:path {self._property_class_iri} .\n'
        else:
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri}Shape as ?propnode)\n'
        #sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode sh:languageIn ?list .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?listprop ?list .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?list rdf:rest* ?z .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?z rdf:first ?head ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}rdf:rest ?tail .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode dcterms:modified ?modified .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        sparql_list.append(sparql)

        sparql = ''
        #
        # Now we delete the remaining triples
        #
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:shacl\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE{{\n'
        if owlclass_iri is not None:
            sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE{{\n'
        if owlclass_iri is not None:
            sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode sh:path {self._property_class_iri} .\n'
        else:
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri}Shape as ?propnode)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode dcterms:modified ?modified .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def delete_owl_subclass_str(self, *,
                                owlclass_iri: Iri,
                                indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:onto\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri.toRdf} rdfs:subClassOf ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri.toRdf} rdfs:subClassOf ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode owl:onProperty {self._property_class_iri.toRdf} .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql

    def delete_owl(self, *,
                   indent: int = 0, indent_inc: int = 4) -> str:
        owlclass_iri = self._internal
        blank = ''
        sparql_list = []
        sparql = f'#\n# Delete {self._property_class_iri} from onto\n#\n'
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:onto\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{indent * indent_inc}}BIND({self._property_class_iri} as ?propnode)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode dcterms:modified ?modified .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        sparql_list.append(sparql)

        if owlclass_iri is not None:
            sparql = self.delete_owl_subclass_str(owlclass_iri=owlclass_iri)
            sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def delete(self) -> None:
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context

        sparql += self.delete_shacl()
        sparql += ' ;\n'
        sparql += self.delete_owl()

        self.__from_triplestore = False
        self._con.transaction_start()
        self._con.transaction_update(sparql)
        modtime_shacl = self.read_modified_shacl(context=context, graph='test')
        modtime_owl = self.read_modified_owl(context=context, graph='test')
        if modtime_shacl is not None or modtime_owl is not None:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed("Deleting Property failed")
        else:
            self._con.transaction_commit()


if __name__ == '__main__':
    n = Numeric(Xsd_integer(4))
    print(n, type(n).__name__)

    s = Iri("xsd:integer")
    dt = XsdDatatypes(s)
    print(dt, type(dt))
