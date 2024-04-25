from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Union, List, Dict, Callable, Self
from pystrict import strict

from omaslib.src.connection import Connection
from omaslib.src.dtypes.namespaceiri import NamespaceIRI
from omaslib.src.helpers.Notify import Notify
from omaslib.src.helpers.omaserror import OmasError, OmasErrorNotFound, OmasErrorAlreadyExists, OmasErrorInconsistency, OmasErrorUpdateFailed, OmasErrorValue
from omaslib.src.enums.propertyclassattr import PropClassAttr
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.enums.resourceclassattr import ResourceClassAttribute
from omaslib.src.helpers.semantic_version import SemanticVersion
from omaslib.src.helpers.tools import RdfModifyRes, RdfModifyItem
from omaslib.src.enums.xsd_datatypes import XsdDatatypes
from omaslib.src.dtypes.bnode import BNode
from omaslib.src.enums.action import Action
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_boolean import Xsd_boolean
from omaslib.src.xsd.xsd_datetime import Xsd_dateTime
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.context import Context
from omaslib.src.iconnection import IConnection
from omaslib.src.model import Model
from omaslib.src.propertyclass import PropertyClass, Attributes
from omaslib.src.xsd.xsd_string import Xsd_string

#
# Datatype definitions
#
AttributeTypes = Union[Iri, LangString, Xsd_boolean, None]
ResourceClassAttributesContainer = Dict[ResourceClassAttribute, AttributeTypes]
Properties = Dict[BNode, Attributes]


@dataclass
class ResourceClassAttributeChange:
    old_value: Union[AttributeTypes, PropertyClass, Iri, None]
    action: Action
    test_in_use: bool


@dataclass
class ResourceClassPropertyChange:
    old_value: Union[PropertyClass, Iri, None]
    action: Action
    test_in_use: bool


@strict
class ResourceClass(Model, Notify):
    _graph: Xsd_NCName
    _owlclass_iri: Iri | None
    _attributes: ResourceClassAttributesContainer
    _properties: Dict[Iri, PropertyClass]
    _attr_changeset: Dict[ResourceClassAttribute, ResourceClassAttributeChange]
    _prop_changeset: Dict[Iri, ResourceClassPropertyChange]
    __creator: Iri | None
    __created: Xsd_dateTime | None
    __contributor: Iri | None
    __modified: Xsd_dateTime | None
    __version: SemanticVersion
    __from_triplestore: bool

    __datatypes: Dict[ResourceClassAttribute, Union[Iri, LangString, Xsd_boolean]] = {
        ResourceClassAttribute.SUBCLASS_OF: Iri,
        ResourceClassAttribute.LABEL: LangString,
        ResourceClassAttribute.COMMENT: LangString,
        ResourceClassAttribute.CLOSED: Xsd_boolean
    }

    def __init__(self, *,
                 con: IConnection,
                 graph: Xsd_NCName,
                 owlclass_iri: Iri | str |None = None,
                 subClassOf: Iri | str | None = None,
                 label: LangString | str | None = None,
                 comment: LangString | str | None = None,
                 closed: Xsd_boolean | bool | None = None,
                 properties: List[PropertyClass | Iri] | None = None,
                 notifier: Callable[[PropClassAttr], None] | None = None,
                 notify_data: PropClassAttr | None = None):
        Model.__init__(self, con)
        Notify.__init__(self, notifier, notify_data)
        self._graph = graph if isinstance(graph, Xsd_NCName) else Xsd_NCName(graph)

        self._attributes = {}

        if isinstance(owlclass_iri, Iri):
            self._owlclass_iri = owlclass_iri
        elif owlclass_iri is not None:
            self._owlclass_iri = Iri(owlclass_iri)
        else:
            self._owlclass_iri = None
        if subClassOf is not None:
            self._attributes[ResourceClassAttribute.SUBCLASS_OF] = subClassOf if isinstance(subClassOf, Iri) else Iri(subClassOf)
        if label is not None:
            self._attributes[ResourceClassAttribute.LABEL] = label if isinstance(label, LangString) else LangString(label)
        if comment is not None:
            self._attributes[ResourceClassAttribute.COMMENT] = comment if isinstance(comment, LangString) else LangString(comment)
        if closed is not None:
            self._attributes[ResourceClassAttribute.CLOSED] = closed if isinstance(closed, Xsd_boolean) else Xsd_boolean(closed)
        self._properties = {}
        if properties is not None:
            for prop in properties:
                newprop: PropertyClass | Iri | None = None
                if isinstance(prop, Iri):  # Reference to an external, standalone property definition
                    fixed_prop = Iri(str(prop).removesuffix("Shape"))
                    try:
                        newprop = PropertyClass.read(self._con, self._graph, fixed_prop)
                    except OmasErrorNotFound as err:
                        newprop = fixed_prop
                elif isinstance(prop, PropertyClass):  # an internal, private property definition
                    if not prop._force_external:
                        prop._internal = owlclass_iri
                    newprop = prop
                else:
                    #newprop = None
                    raise OmasErrorValue(f'Unexpected property type: {type(prop).__name__}')
                if newprop is not None:
                    self._properties[newprop.property_class_iri] = newprop
                    newprop.set_notifier(self.notifier, newprop.property_class_iri)

        for attr in ResourceClassAttribute:
            prefix, name = attr.value.split(':')
            setattr(ResourceClass, name, property(
                partial(ResourceClass.__get_value, attr=attr),
                partial(ResourceClass.__set_value, attr=attr),
                partial(ResourceClass.__del_value, attr=attr)))

        self.__creator = con.userIri
        self.__created = None
        self.__contributor = con.userIri
        self.__modified = None
        self.__version = SemanticVersion()
        self._attr_changeset = {}
        self._prop_changeset = {}
        self.__from_triplestore = False

    def __get_value(self: Self, attr: ResourceClassAttribute) -> AttributeTypes | PropertyClass | Iri | None:
        return self.__getter(attr)

    def __set_value(self: Self, value: AttributeTypes | PropertyClass | Iri, attr: ResourceClassAttribute) -> None:
        self.__change_setter(attr, value)

    def __del_value(self: Self, attr: ResourceClassAttribute) -> None:
        self.__deleter(attr)

    def __getter(self, key: ResourceClassAttribute | Iri) -> AttributeTypes | PropertyClass | Iri:
        if isinstance(key, ResourceClassAttribute):
            return self._attributes.get(key)
        elif isinstance(key, Iri):
            return self._properties.get(key)
        else:
            return None

    def __change_setter(self, key: ResourceClassAttribute | Iri, value: AttributeTypes | PropertyClass | Iri) -> None:
        if type(key) not in {ResourceClassAttribute, PropertyClass, Iri}:
            raise ValueError(f'Invalid key type {type(key)} of key {key}')
        if getattr(value, 'set_notifier', None) is not None:
            value.set_notifier(self.notifier, key)
        if isinstance(key, ResourceClassAttribute):
            if self._attributes.get(key) is None:  # Attribute not yet set
                self._attr_changeset[key] = ResourceClassAttributeChange(None, Action.CREATE, False)  # TODO: Check if "check_in_use" must be set
            else:
                if self._attr_changeset.get(key) is None:  # Only first change is recorded
                    self._attr_changeset[key] = ResourceClassAttributeChange(self._attributes[key], Action.REPLACE, False)  # TODO: Check if "check_in_use" must be set
                else:
                    self._attr_changeset[key] = ResourceClassAttributeChange(self._attr_changeset[key].old_value, Action.REPLACE, False)  # TODO: Check if "check_in_use" must be set
            self._attributes[key] = value
        elif isinstance(key, Iri):  # Iri
            if self._properties.get(key) is None:  # Property not set -> CREATE action
                self._prop_changeset[key] = ResourceClassPropertyChange(None, Action.CREATE, False)
                if value is None:
                    try:
                        self._properties[key] = PropertyClass.read(self._con, graph=self._graph, property_class_iri=key)
                    except OmasErrorNotFound as err:
                        self._properties[key] = key
                else:
                    value._internal = self._owlclass_iri  # we need to access the private variable here
                    value._property_class_iri = key  # we need to access the private variable here
                    self._properties[key] = value
            else:  # REPLACE action
                if self._prop_changeset.get(key) is None:
                    self._prop_changeset[key] = ResourceClassPropertyChange(self._properties[key], Action.REPLACE, True)
                else:
                    self._prop_changeset[key] = ResourceClassPropertyChange(self._prop_changeset[key].old_value, Action.REPLACE, True)
                if value is None:
                    try:
                        self._properties[key] = PropertyClass.read(self._con, graph=self._graph, property_class_iri=key)
                    except OmasErrorNotFound as err:
                        self._properties[key] = key
                else:
                    value._internal = self._owlclass_iri  # we need to access the private variable here
                    value._property_class_iri = key  # we need to access the private variable here
                    self._properties[key] = value
        else:
            raise OmasError(f'Invalid key type {type(key).__name__} of key {key}')
        self.notify()

    def __deleter(self, key: ResourceClassAttribute | Iri) -> None:
        if not isinstance(key, (ResourceClassAttribute, Iri)):
            raise ValueError(f'Invalid key type {type(key).__name__} of key {key}')
        if isinstance(key, ResourceClassAttribute):
            if self._attr_changeset.get(key) is None:
                self._attr_changeset[key] = ResourceClassAttributeChange(self._attributes[key], Action.DELETE, False)
            else:
                self._attr_changeset[key] = ResourceClassAttributeChange(self._attr_changeset[key].old_value, Action.DELETE, False)
            del self._attributes[key]
        elif isinstance(key, Iri):
            if self._prop_changeset.get(key) is None:
                self._prop_changeset[key] = ResourceClassPropertyChange(self._properties[key], Action.DELETE, False)
            else:
                self._prop_changeset[key] = ResourceClassPropertyChange(self._prop_changeset[key].old_value, Action.DELETE, False)
            del self._properties[key]
        self.notify()

    def __getitem__(self, key: ResourceClassAttribute | Iri) -> AttributeTypes | PropertyClass | Iri:
        return self.__getter(key)

    def get(self, key: ResourceClassAttribute | Iri) -> AttributeTypes | PropertyClass | Iri | None:
        if isinstance(key, ResourceClassAttribute):
            return self._attributes.get(key)
        elif isinstance(key, Iri):
            return self._properties.get(key)
        else:
            return None

    def __setitem__(self, key: ResourceClassAttribute | Iri, value: AttributeTypes | PropertyClass | Iri) -> None:
        self.__change_setter(key, value)

    def __delitem__(self, key: ResourceClassAttribute | Iri) -> None:
        self.__deleter(key)

    @property
    def owl_class_iri(self) -> Iri:
        return self._owlclass_iri

    @property
    def version(self) -> SemanticVersion:
        return self.__version

    @property
    def creator(self) -> Iri | None:
        return self.__creator

    @property
    def created(self) -> Xsd_dateTime | None:
        return self.__created

    @property
    def contributor(self) -> Iri | None:
        return self.__contributor

    @property
    def modified(self) -> Xsd_dateTime | None:
        return self.__modified

    def properties_items(self):
        return self._properties.items()

    def attributes_items(self):
        return self._attributes.items()

    def __str__(self):
        blank = ' '
        indent = 2
        s = f'Shape: {self._owlclass_iri}Shape\n'
        s += f'{blank:{indent*1}}Attributes:\n'
        for attr, value in self._attributes.items():
            s += f'{blank:{indent*2}}{attr.value} = {value}\n'
        s += f'{blank:{indent*1}}Properties:\n'
        sorted_properties = sorted(self._properties.items(), key=lambda prop: prop[1].order if prop[1].order is not None else 9999)
        for qname, prop in sorted_properties:
            s += f'{blank:{indent*2}}{qname} = {prop}\n'
        return s

    def changeset_clear(self) -> None:
        for attr, change in self._attr_changeset.items():
            if change.action == Action.MODIFY:
                self._attributes[attr].changeset_clear()
        self._attr_changeset = {}
        for prop, change in self._prop_changeset.items():
            if change.action == Action.MODIFY:
                self._properties[prop].changeset_clear()
        self._prop_changeset = {}

    def notifier(self, what: ResourceClassAttribute | Iri):
        if isinstance(what, ResourceClassAttribute):
            self._attr_changeset[what] = ResourceClassAttributeChange(None, Action.MODIFY, True)
        elif isinstance(what, Iri):
            self._prop_changeset[what] = ResourceClassPropertyChange(None, Action.MODIFY, True)
        self.notify()

    @property
    def in_use(self) -> bool:
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT (COUNT(?resinstances) as ?nresinstances)
        WHERE {{
            ?resinstance rdf:type {self._owlclass_iri} .
            FILTER(?resinstances != {self._owlclass_iri}Shape)
        }} LIMIT 2
        """
        jsonobj = self._con.query(query)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            raise OmasError('Internal Error in "ResourceClass.in_use"')
        for r in res:
            if int(r.nresinstances) > 0:
                return True
            else:
                return False

    @staticmethod
    def __query_shacl(con: IConnection, graph: Xsd_NCName, owl_class_iri: Iri) -> Attributes:
        context = Context(name=con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT ?attriri ?value
        FROM {graph}:shacl
        WHERE {{
            BIND({owl_class_iri}Shape AS ?shape)
            ?shape ?attriri ?value
        }}
         """
        jsonobj = con.query(query)
        res = QueryProcessor(context, jsonobj)
        attributes: Attributes = {}
        for r in res:
            attriri = r['attriri']
            if attriri == 'rdf:type':
                tmp_owl_class_iri = r['value']
                if tmp_owl_class_iri == 'sh:NodeShape':
                    continue
                if tmp_owl_class_iri != owl_class_iri:
                    raise OmasError(f'Inconsistent Shape for "{owl_class_iri}": rdf:type="{tmp_owl_class_iri}"')
            elif attriri == 'sh:property':
                continue  # processes later – points to a BNode containing
            else:
                attriri = r['attriri']
                if isinstance(r['value'], Iri):
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    attributes[attriri].append(r['value'])
                elif isinstance(r['value'], Xsd_string):
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    attributes[attriri].append(str(r['value']))
                elif isinstance(r['value'], BNode):
                    pass
                else:
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    attributes[attriri].append(r['value'])
        return attributes

    def _parse_shacl(self, attributes: Attributes) -> None:
        for key, val in attributes.items():
            if key == 'sh:targetClass':
                continue
            if key == 'dcterms:hasVersion':
                self.__version = SemanticVersion.fromString(val[0])
            elif key == 'dcterms:creator':
                self.__creator = val[0]
            elif key == 'dcterms:created':
                self.__created = val[0]
            elif key == 'dcterms:contributor':
                self.__contributor = val[0]
            elif key == 'dcterms:modified':
                self.__modified = val[0]
            else:
                attr = ResourceClassAttribute(key)
                if Iri == self.__datatypes[attr]:
                    self._attributes[attr] = val[0]  # is already QName or AnyIRI from preprocessing
                elif XsdDatatypes == self.__datatypes[attr]:
                    self._attributes[attr] = XsdDatatypes(str(val[0]))
                elif LangString == self.__datatypes[attr]:
                    self._attributes[attr] = LangString(val)
                elif Xsd_boolean == self.__datatypes[attr]:
                    self._attributes[attr] = bool(val[0])
                if getattr(self._attributes[attr], 'set_notifier', None) is not None:
                    self._attributes[attr].set_notifier(self.notifier, attr)

        self.__from_triplestore = True

    @staticmethod
    def __query_resource_props(con: IConnection, graph: Xsd_NCName, owlclass_iri: Iri) -> List[PropertyClass | Iri]:
        """
        This method queries and returns a list of properties defined in a sh:NodeShape. The properties may be
        given "inline" as BNode or may be a reference to an external sh:PropertyShape. These external shapes will be
        read when the ResourceClass is constructed (see __init__() of ResourceClass).

        :param con: IConnection instance
        :param graph: Name of the graph
        :param owlclass_iri: The QName of the OWL class defining the resource. The "Shape" ending will be added
        :return: List of PropertyClasses/QNames
        """

        context = Context(name=con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT ?prop ?attriri ?value ?oo
        FROM {graph}:shacl
        WHERE {{
            BIND({owlclass_iri}Shape AS ?shape)
            ?shape sh:property ?prop .
            OPTIONAL {{
                ?prop ?attriri ?value .
                OPTIONAL {{
                    ?value rdf:rest*/rdf:first ?oo
                }}
            }}
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=context, query_result=jsonobj)
        propinfos: Dict[Iri, Attributes] = {}
        #
        # first we run over all triples to gather the information about the properties of the possible
        # BNode based sh:property-Shapes.
        # NOTE: some of the nodes may actually be QNames referencing shapes defines as "standalone" sh:PropertyShape's.
        #
        for r in res:
            if isinstance(r['value'], Iri) and r['value'] == 'rdf:type':
                continue
            if not isinstance(r['attriri'], Iri):
                raise OmasError(f"There is some inconsistency in this shape! ({r['attriri']})")
            propnode = r['prop']  # usually a BNode, but may be a reference to a standalone sh:PropertyShape definition
            prop: PropertyClass | Iri
            if isinstance(propnode, Iri):
                qname = propnode
                propinfos[qname] = propnode
            elif isinstance(propnode, BNode):
                if propinfos.get(propnode) is None:
                    propinfos[propnode]: Attributes = {}
                PropertyClass.process_triple(r, propinfos[propnode])
            else:
                raise OmasError(f'Unexpected type for propnode in SHACL. Type = "{type(propnode)}".')
        #
        # now we collected all the information from the triple store. Let's process the information into
        # a list of full PropertyClasses or QName's to external definitions
        #
        proplist: List[Iri | PropertyClass] = []
        for prop_iri, attributes in propinfos.items():
            if isinstance(attributes, Iri):
                proplist.append(prop_iri)
            else:
                prop = PropertyClass(con=con, graph=graph)
                prop.parse_shacl(attributes=attributes)
                prop.read_owl()
                if prop._internal != owlclass_iri:
                    OmasErrorInconsistency(f'ERRROR ERROR ERROR')
                proplist.append(prop)
        #prop.set_notifier(self.notifier, prop_iri)
        return proplist

    def __read_owl(self):
        context = Context(name=self._con.context_name)
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?prop ?p ?o
        FROM {self._owlclass_iri.prefix}:onto
        WHERE {{
   	        omas:OmasProject rdfs:subClassOf ?prop .
            ?prop ?p ?o .
            FILTER(?o != owl:Restriction)
        }}
        """
        jsonobj = self._con.query(query1)
        res = QueryProcessor(context=context, query_result=jsonobj)
        propdict = {}
        for r in res:
            bnode_id = str(r['prop'])
            if not propdict.get(bnode_id):
                propdict[bnode_id] = {}
            p = r['p']
            if p == 'owl:onProperty':
                propdict[bnode_id]['property_iri'] = r['o']
            elif p == 'owl:onClass':
                propdict[bnode_id]['to_node_iri'] = r['o']
            elif p == 'owl:minQualifiedCardinality':
                propdict[bnode_id]['min_count'] = r['o']
            elif p == 'owl:maxQualifiedCardinality':
                propdict[bnode_id]['max_count'] = r['o']
            elif p == 'owl:qualifiedCardinality':
                propdict[bnode_id]['min_count'] = r['o']
                propdict[bnode_id]['max_count'] = r['o']
            elif p == 'owl:onDataRange':
                propdict[bnode_id]['datatype'] = r['o']
            else:
                print(f'ERROR ERROR ERROR: Unknown restriction property: "{p}"')
        for bn, pp in propdict.items():
            if pp.get('property_iri') is None:
                OmasError('Invalid restriction node: No property_iri!')
            property_iri = pp['property_iri']
            prop = [x for x in self._properties if x == property_iri]
            if len(prop) != 1:
                OmasError(f'Property "{property_iri}" from OWL has no SHACL definition!')
            self._properties[prop[0]].prop.read_owl()

    @classmethod
    def read(cls, con: IConnection, graph: Xsd_NCName, owl_class_iri: Iri) -> Self:
        attributes = ResourceClass.__query_shacl(con, graph=graph, owl_class_iri=owl_class_iri)
        properties: List[Union[PropertyClass, Iri]] = ResourceClass.__query_resource_props(con=con, graph=graph, owlclass_iri=owl_class_iri)
        resclass = cls(con=con, graph=graph, owlclass_iri=owl_class_iri, properties=properties)
        for prop in properties:
            if isinstance(prop, PropertyClass):
                prop.set_notifier(resclass.notifier, prop.property_class_iri)
        resclass._parse_shacl(attributes=attributes)
        resclass.__read_owl()
        return resclass

    def read_modified_shacl(self, *,
                            context: Context,
                            graph: Xsd_NCName,
                            indent: int = 0, indent_inc: int = 4) -> Union[datetime, None]:
        blank = ''
        sparql = context.sparql_context
        sparql += f"{blank:{indent * indent_inc}}SELECT ?modified\n"
        sparql += f"{blank:{indent * indent_inc}}FROM {graph}:shacl\n"
        sparql += f"{blank:{indent * indent_inc}}WHERE {{\n"
        sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._owlclass_iri}Shape as ?res)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?res dcterms:modified ?modified .\n'
        sparql += f"{blank:{indent * indent_inc}}}}"
        jsonobj = self._con.transaction_query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            return None
        return res[0].get('modified')

    def read_modified_owl(self, *,
                          context: Context,
                          graph: Xsd_NCName,
                          indent: int = 0, indent_inc: int = 4) -> Union[datetime, None]:
        blank = ''
        sparql = context.sparql_context
        sparql += f"{blank:{indent * indent_inc}}SELECT ?modified\n"
        sparql += f"{blank:{indent * indent_inc}}FROM {graph}:onto\n"
        sparql += f"{blank:{indent * indent_inc}}WHERE {{\n"
        sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._owlclass_iri} as ?res)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?res dcterms:modified ?modified .\n'
        sparql += f"{blank:{indent * indent_inc}}}}"
        jsonobj = self._con.transaction_query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            return None
        return res[0].get('modified')

    def create_shacl(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        # for iri, p in self._properties.items():
        #     if p.internal is None and not p.from_triplestore:
        #         #sparql += p.create_shacl(timestamp=timestamp)
        #         sparql += f'{blank:{(indent + 2)*indent_inc}}{iri}Shape a sh:PropertyShape ;\n'
        #         sparql += p.property_node_shacl(timestamp=timestamp, indent=3) + " .\n"
        #         sparql += "\n"

        sparql += f'{blank:{(indent + 1)*indent_inc}}{self._owlclass_iri}Shape a sh:NodeShape, {self._owlclass_iri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:targetClass {self._owlclass_iri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:hasVersion {self.__version.toRdf}'
        self.__created = timestamp
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:creator {self.__creator.toRdf}'
        self.__modified = timestamp
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:contributor {self.__contributor.toRdf}'
        for attr, value in self._attributes.items():
            if attr == ResourceClassAttribute.SUBCLASS_OF:
                sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}{attr.value} {value}Shape'
            else:
                sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}{attr.value} {value.toRdf}'

        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:property'
        sparql += f'\n{blank:{(indent + 3) * indent_inc}}['
        sparql += f'\n{blank:{(indent + 4) * indent_inc}}sh:path rdf:type'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}]'

        for iri, p in self._properties.items():
            if p.internal is not None:
                sparql += f' ;\n{blank:{(indent + 2)*indent_inc}}sh:property'
                sparql += f'\n{blank:{(indent + 3)*indent_inc}}[\n'
                sparql += p.property_node_shacl(timestamp=timestamp, indent=4)
                sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}]'
            else:
                sparql += f' ;\n{blank:{(indent + 2)*indent_inc}}sh:property {iri}Shape'
        if len(self._properties) > 0:
            sparql += ' .\n'
        return sparql

    def create_owl(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4):
        blank = ''
        sparql = ''
        for iri, p in self._properties.items():
            if not p.from_triplestore:
                sparql += p.create_owl_part1(timestamp, indent + 2) + '\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}}{self._owlclass_iri} rdf:type owl:Class ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:hasVersion {self.__version.toRdf} ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf} ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:creator {self.__creator.toRdf} ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf} ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self.__contributor.toRdf} ;\n'
        if self._attributes.get(ResourceClassAttribute.SUBCLASS_OF) is not None:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:subClassOf {self._attributes[ResourceClassAttribute.SUBCLASS_OF]} ,\n'
        else:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:subClassOf\n'
        i = 0
        for iri, p in self._properties.items():
            sparql += p.create_owl_part2(indent + 4)
            if i < len(self._properties) - 1:
                sparql += ' ,\n'
            else:
                sparql += ' .\n'
            i += 1
        return sparql

    def set_creation_metadata(self, timestamp: Xsd_dateTime):
        self.__created = timestamp
        self.__creator = self._con.userIri
        self.__modified = timestamp
        self.__contributor = self._con.userIri
        self.__from_triplestore = True


    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        if self.__from_triplestore:
            raise OmasErrorAlreadyExists(f'Cannot create property that was read from triplestore before (property: {self._owlclass_iri}')
        timestamp = Xsd_dateTime.now()
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:shacl {{\n'
        sparql += self.create_shacl(timestamp=timestamp)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:onto {{\n'
        sparql += self.create_owl(timestamp=timestamp)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}}}\n'
        self._con.transaction_start()
        if self.read_modified_shacl(context=context, graph=self._graph) is not None:
            self._con.transaction_abort()
            raise OmasErrorAlreadyExists(f'Object "{self._owlclass_iri}" already exists.')
        self._con.transaction_update(sparql)
        modtime_shacl = self.read_modified_shacl(context=context, graph=self._graph)
        modtime_owl = self.read_modified_owl(context=context, graph=self._graph)
        if modtime_shacl == timestamp and modtime_owl == timestamp:
            self._con.transaction_commit()
            self.set_creation_metadata(timestamp=timestamp)
        else:
            self._con.transaction_abort()
            raise OmasErrorUpdateFailed(f'Creating resource "{self._owlclass_iri}" failed.')

    def write_as_trig(self, filename: str, indent: int = 0, indent_inc: int = 4) -> None:
        with open(filename, 'w') as f:
            timestamp = Xsd_dateTime.now()
            blank = ''
            context = Context(name=self._con.context_name)
            f.write(context.turtle_context)

            f.write(f'{blank:{indent * indent_inc}}{self._graph}:shacl {{\n')
            f.write(self.create_shacl(timestamp=timestamp))
            f.write(f'\n{blank:{indent * indent_inc}}}}\n')

            f.write(f'{blank:{indent * indent_inc}}{self._graph}:onto {{\n')
            f.write(self.create_owl(timestamp=timestamp))
            f.write(f'{blank:{indent * indent_inc}}}}\n')

    def __update_shacl(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4) -> str:
        if not self._attr_changeset and not self._prop_changeset:
            return ''
        blank = ''
        sparql_list = []

        #
        # First process attributes
        #
        for item, change in self._attr_changeset.items():
            sparql = f'#\n# Process "{item.value}" with Action "{change.action.value}"\n#\n'

            sparql += RdfModifyRes.shacl(action=change.action,
                                         graph=self._graph,
                                         owlclass_iri=self._owlclass_iri,
                                         ele=RdfModifyItem(str(item.value),
                                                           None if change.old_value is None else str(change.old_value),
                                                           str(self._attributes[item])),
                                         last_modified=self.__modified)
            sparql_list.append(sparql)

        #
        # now process properties
        #
        for prop, change in self._prop_changeset.items():
            if change.action in {Action.CREATE, Action.REPLACE}:  # do nothing for Action.MODIFY here
                if self._properties[prop].internal is None:
                    sparql = f'#\n# Process "QName" with action "{change.action.value}"\n#\n'
                    sparql += RdfModifyRes.shacl(action=change.action,
                                                 graph=self._graph,
                                                 owlclass_iri=self._owlclass_iri,
                                                 ele=RdfModifyItem('sh:property',
                                                                   None if change.old_value is None else str(change.old_value),
                                                                   f'{prop}Shape'),
                                                 last_modified=self.__modified)
                    sparql_list.append(sparql)
            elif change.action == Action.DELETE:
                if change.old_value.internal is not None:
                    change.old_value.delete()
                else:
                    sparql = f'#\n# Process "QName" with action "{change.action.value}"\n#\n'

                    sparql += RdfModifyRes.shacl(action=change.action,
                                                 graph=self._graph,
                                                 owlclass_iri=self._owlclass_iri,
                                                 ele=RdfModifyItem('sh:property',
                                                                   None if change.old_value is None else f'{change.old_value.property_class_iri}Shape',
                                                                   f'{prop}Shape'),
                                                 last_modified=self.__modified)
                    sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor\n#\n'
        sparql += RdfModifyRes.shacl(action=Action.REPLACE if self.__contributor else Action.CREATE,
                                     graph=self._graph,
                                     owlclass_iri=self._owlclass_iri,
                                     ele=RdfModifyItem('dcterms:contributor', f'<{self.__contributor}>', f'<{self._con.userIri}>'),
                                     last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified\n#\n'
        sparql += RdfModifyRes.shacl(action=Action.REPLACE if self.__modified else Action.CREATE,
                                     graph=self._graph,
                                     owlclass_iri=self._owlclass_iri,
                                     ele=RdfModifyItem('dcterms:modified', self.__modified.toRdf, timestamp.toRdf),
                                     last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def __update_owl(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4) -> str:
        if not self._attr_changeset and not self._prop_changeset:
            return ''
        blank = ''
        sparql_list = []
        #
        # Adapt OWL for changing *attributes* (where only rdfs:subClassOf is relevant...)
        #
        for item, change in self._attr_changeset.items():
            #
            # we only need to add rdfs:subClassOf to the ontology – all other attributes are irrelevant
            #
            if item == ResourceClassAttribute.SUBCLASS_OF:
                sparql = f'#\n# OWL: Process attribute "{item.value}" with Action "{change.action.value}"\n#\n'
                sparql += f'WITH {self._graph}:onto\n'
                if change.action != Action.CREATE:
                    sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?prop rdfs:subClassOf {change.old_value.toRdf} .\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                if change.action != Action.DELETE:
                    sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?prop rdfs:subClassOf {self._attributes[item].toRdf} .\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.owl_class_iri.toRdf} as ?prop)\n'
                if change.action != Action.CREATE:
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?res rdfs:subClassOf {change.old_value.toRdf} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?res dcterms:modified ?modified .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {timestamp.toRdf})\n'
                sparql += f'{blank:{indent * indent_inc}}}}'
                sparql_list.append(sparql)

        for prop, change in self._prop_changeset.items():
            sparql = f'#\n# OWL: Process property "{prop}" with Action "{change.action.value}"\n#\n'
            sparql += f'WITH {self._graph}:onto\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?res rdfs:subClassOf ?node .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?node ?p ?v\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?res rdfs:subClassOf\n'
                sparql += self._properties[prop].create_owl_part2(indent=2)
                sparql += '\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.owl_class_iri.toRdf} as ?res)\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{(indent + 2) * indent_inc}}?node owl:onProperty {prop.toRdf}\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor\n#\n'
        sparql += RdfModifyRes.onto(action=Action.REPLACE if self.__contributor else Action.CREATE,
                                    graph=self._graph,
                                    owlclass_iri=self._owlclass_iri,
                                    ele=RdfModifyItem('dcterms:contributor', f'<{self.__contributor}>', f'<{self._con.userIri}>'),
                                    last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified\n#\n'
        sparql += RdfModifyRes.onto(action=Action.REPLACE if self.__modified else Action.CREATE,
                                    graph=self._graph,
                                    owlclass_iri=self._owlclass_iri,
                                    ele=RdfModifyItem('dcterms:modified', self.__modified.toRdf, timestamp.toRdf),
                                    last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def update(self) -> None:
        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)
        #
        # First we process the changes regarding the properties
        #
        for prop, change in self._prop_changeset.items():
            if change.action == Action.CREATE:
                if self._properties[prop].internal is not None:
                    self._properties[prop].create()

                    # TODO: Add here the OWL rdfs:subClassOf to the owl ontology
            elif change.action == Action.REPLACE:
                if change.old_value.internal is not None:
                    change.old_value.delete()
                if not self._properties[prop].from_triplestore:
                    self._properties[prop].create()
                else:
                    if self._properties[prop].get(PropClassAttr.EXCLUSIVE_FOR) is None:
                        continue  # TODO: replace reference in __update_shacl and __update_owl
                    else:
                        raise OmasErrorInconsistency(f'Property is exclusive – simple reference not allowed')
            elif change.action == Action.MODIFY:
                self._properties[prop].update()
            elif change.action == Action.DELETE:
                if change.old_value.internal is not None:
                    change.old_value.delete()
        sparql = context.sparql_context
        sparql += self.__update_shacl(timestamp=timestamp)
        sparql += ' ;\n'
        sparql += self.__update_owl(timestamp=timestamp)
        self._con.transaction_start()
        self._con.transaction_update(sparql)
        modtime_shacl = self.read_modified_shacl(context=context, graph=self._graph)
        modtime_owl = self.read_modified_owl(context=context, graph=self._graph)
        if modtime_shacl == timestamp and modtime_owl == timestamp:
            self._con.transaction_commit()
            self.changeset_clear()
            self.__modified = timestamp
            self.__contributor = self._con.userIri
        else:
            self._con.transaction_abort()
            raise OmasErrorUpdateFailed(f'Update of {self._owlclass_iri} failed. {modtime_shacl} {modtime_owl} {timestamp}')

    def __delete_shacl(self) -> str:
        sparql = f'#\n# SHALC: Delete "{self._owlclass_iri}" completely\n#\n'
        sparql += f"""
        WITH {self._graph}:shacl
        DELETE {{
            {self._owlclass_iri}Shape ?rattr ?rvalue .
            ?rvalue ?pattr ?pval .
            ?z rdf:first ?head ;
            rdf:rest ?tail .
        }}
        WHERE {{
            {self._owlclass_iri}Shape ?rattr ?rvalue .
            OPTIONAL {{
                ?rvalue ?pattr ?pval .
                OPTIONAL {{
                    ?pval rdf:rest* ?z .
                    ?z rdf:first ?head ;
                    rdf:rest ?tail .
                }}
                FILTER(isBlank(?rvalue))
            }}
        }}
        """
        return sparql

    def __delete_owl(self) -> str:
        sparql = f'#\n# OWL: Delete "{self._owlclass_iri}" completely\n#\n'
        sparql += f"""
        WITH {self._graph}:onto
        DELETE {{
            ?prop ?p ?v
        }}
        WHERE {{
            ?prop rdfs:domain {self._owlclass_iri.toRdf} .
            ?prop ?p ?v
        }} ;
        WITH {self._graph}:onto
        DELETE {{
            ?res ?prop ?value .
            ?value ?pp ?vv .
        }}
        WHERE {{
            BIND({self._owlclass_iri.toRdf} AS ?res)
            ?res ?prop ?value
            OPTIONAL {{
                ?value ?pp ?vv
                FILTER(isBlank(?value))
            }}
        }}
        """
        return sparql

    def delete(self) -> None:
        timestamp = datetime.now()
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += self.__delete_shacl()
        sparql += ' ;\n'
        sparql += self.__delete_owl()
        self._con.transaction_start()
        self._con.transaction_update(sparql)
        sparql = context.sparql_context
        sparql += f"SELECT * FROM {self._graph}:shacl WHERE {{ {self._owlclass_iri}Shape ?p ?v }}"
        jsonobj = self._con.transaction_query(sparql)
        res_shacl = QueryProcessor(context, jsonobj)
        sparql = context.sparql_context
        sparql += f"SELECT * FROM {self._graph}:onto WHERE {{ {self._owlclass_iri.toRdf} ?p ?v }}"
        jsonobj = self._con.transaction_query(sparql)
        res_onto = QueryProcessor(context, jsonobj)
        if len(res_shacl) > 0 or len(res_onto) > 0:
            self._con.transaction_abort()
            raise OmasErrorUpdateFailed(f'Could not delete "{self._owlclass_iri}".')
        else:
            self._con.transaction_commit()


if __name__ == '__main__':
    context = Context(name="DEFAULT")
    context['test'] = NamespaceIRI("http://omas.org/test#")
    context.use('test', 'dcterms')

    connection = Connection(server='http://localhost:7200',
                                 userId="rosenth",
                                 credentials="RioGrande",
                                 repo="omas",
                                 context_name="DEFAULT")
    properties: list[PropertyClass | Iri] = [
        Iri("test:comment"),
        Iri("test:test"),
    ]
    r1 = ResourceClass(con=connection,
                       graph=Xsd_NCName('test'),
                       owlclass_iri=Iri("test:testMyResMinimal"))
    r1.closed = Xsd_boolean(True)

