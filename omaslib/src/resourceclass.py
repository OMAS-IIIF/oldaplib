from dataclasses import dataclass
from datetime import datetime
from pprint import pprint
from typing import Union, Optional, List, Dict, Callable
from pystrict import strict

from omaslib.src.connection import Connection
from omaslib.src.helpers.Notify import Notify
from omaslib.src.helpers.omaserror import OmasError, OmasErrorNotFound, OmasErrorAlreadyExists, OmasErrorInconsistency, OmasErrorUpdateFailed
from omaslib.src.helpers.propertyclassattr import PropertyClassAttribute
from omaslib.src.helpers.query_processor import QueryProcessor, OmasStringLiteral
from omaslib.src.helpers.resourceclassattr import ResourceClassAttribute
from omaslib.src.helpers.semantic_version import SemanticVersion
from omaslib.src.helpers.tools import RdfModifyProp, RdfModifyRes, RdfModifyItem, lprint
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.helpers.datatypes import QName, Action, AnyIRI, NCName, BNode
from omaslib.src.helpers.langstring import Language, LangString
from omaslib.src.helpers.context import Context
from omaslib.src.model import Model
from omaslib.src.propertyclass import PropertyClass, Attributes
from omaslib.src.propertyrestrictions import PropertyRestrictions

#
# Datatype definitions
#
AttributeTypes = Union[QName, LangString, bool, None]
ResourceClassAttributesContainer = Dict[ResourceClassAttribute, AttributeTypes]
Properties = Dict[BNode, Attributes]


@dataclass
class ResourceClassAttributeChange:
    old_value: Union[AttributeTypes, PropertyClass, QName, None]
    action: Action
    test_in_use: bool

@dataclass
class ResourceClassPropertyChange:
    old_value: Union[PropertyClass, QName, None]
    action: Action
    test_in_use: bool


@strict
class ResourceClass(Model, Notify):
    _graph: NCName
    _owlclass_iri: Union[QName, None]
    _attributes: ResourceClassAttributesContainer
    _properties: Dict[QName, PropertyClass]
    _attr_changeset: Dict[ResourceClassAttribute, ResourceClassAttributeChange]
    _prop_changeset: Dict[QName, ResourceClassPropertyChange]
    __creator: Optional[AnyIRI]
    __created: Optional[datetime]
    __contributor: Optional[AnyIRI]
    __modified: Optional[datetime]
    __version: SemanticVersion
    __from_triplestore: bool

    __datatypes: Dict[ResourceClassAttribute, Union[QName, LangString, bool]] = {
        ResourceClassAttribute.SUBCLASS_OF: QName,
        ResourceClassAttribute.LABEL: LangString,
        ResourceClassAttribute.COMMENT: LangString,
        ResourceClassAttribute.CLOSED: bool
    }

    def __init__(self, *,
                 con: Connection,
                 graph: NCName,
                 owlclass_iri: Optional[QName] = None,
                 attrs: Optional[ResourceClassAttributesContainer] = None,
                 properties: Optional[List[Union[PropertyClass, QName]]] = None,
                 notifier: Optional[Callable[[PropertyClassAttribute], None]] = None,
                 notify_data: Optional[PropertyClassAttribute] = None):
        Model.__init__(self, con)
        Notify.__init__(self, notifier, notify_data)
        self._graph = graph
        self._owlclass_iri = owlclass_iri
        self.__creator = con.userIri
        self.__created = None
        self.__contributor = con.userIri
        self.__modified = None
        self.__version = SemanticVersion()
        self._attributes = {}
        if attrs is not None:
            for attr, value in attrs.items():
                if (attr == ResourceClassAttribute.LABEL or attr == ResourceClassAttribute.COMMENT) and type(value) != LangString:
                    raise OmasError(f'Attribute "{attr.value}" must be a "LangString", but is "{type(value)}"!')
                if attr == ResourceClassAttribute.SUBCLASS_OF and type(value) != QName:
                    raise OmasError(f'Attribute "{attr.value}" must be a "QName", but is "{type(value)}"!')
                if attr == ResourceClassAttribute.CLOSED and type(value) != bool:
                    raise OmasError(f'Attribute "{attr.value}" must be a "bool", but is "{type(value)}"!')
                if getattr(value, 'set_notifier', None) is not None:
                    value.set_notifier(self.notifier, attr)
                self._attributes[attr] = value
        self._properties = {}
        if properties is not None:
            for prop in properties:
                newprop: Union[PropertyClass, QName]
                if isinstance(prop, QName):  # Reference to an external, standalone property definition
                    fixed_prop = QName(str(prop).removesuffix("Shape"))
                    try:
                        newprop = PropertyClass.read(self._con, self._graph, fixed_prop)
                    except OmasErrorNotFound as err:
                        newprop = fixed_prop
                elif isinstance(prop, PropertyClass):  # an internal, private property definition
                    if not prop._force_external:
                        prop._internal = owlclass_iri
                    newprop = prop
                self._properties[newprop.property_class_iri] = newprop
                newprop.set_notifier(self.notifier, newprop.property_class_iri)
        self._attr_changeset = {}
        self._prop_changeset = {}
        self.__from_triplestore = False

    def __getitem__(self, key: Union[ResourceClassAttribute, QName]) -> Union[AttributeTypes, PropertyClass, QName]:
        if isinstance(key, ResourceClassAttribute):
            return self._attributes[key]
        elif isinstance(key, QName):
            return self._properties[key]
        else:
            raise ValueError(f'Invalid key type {type(key)} of key {key}')

    def get(self, key: Union[ResourceClassAttribute, QName]) -> Union[AttributeTypes, PropertyClass, QName, None]:
        if isinstance(key, ResourceClassAttribute):
            return self._attributes.get(key)
        elif isinstance(key, QName):
            return self._properties.get(key)
        else:
            return None

    def __setitem__(self, key: Union[ResourceClassAttribute, QName], value: Union[AttributeTypes, PropertyClass, QName]) -> None:
        if type(key) not in {ResourceClassAttribute, PropertyClass, QName}:
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
        elif isinstance(key, QName):  # QName
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
        self.notify()

    def __delitem__(self, key: Union[ResourceClassAttribute, QName]) -> None:
        if type(key) not in {ResourceClassAttribute, QName}:
            raise ValueError(f'Invalid key type {type(key)} of key {key}')
        if isinstance(key, ResourceClassAttribute):
            if self._attr_changeset.get(key) is None:
                self._attr_changeset[key] = ResourceClassAttributeChange(self._attributes[key], Action.DELETE, False)
            else:
                self._attr_changeset[key] = ResourceClassAttributeChange(self._attr_changeset[key].old_value, Action.DELETE, False)
            del self._attributes[key]
        elif isinstance(key, QName):
            if self._prop_changeset.get(key) is None:
                self._prop_changeset[key] = ResourceClassPropertyChange(self._properties[key], Action.DELETE, False)
            else:
                self._prop_changeset[key] = ResourceClassPropertyChange(self._prop_changeset[key].old_value, Action.DELETE, False)
            del self._properties[key]
        self.notify()

    @property
    def owl_class_iri(self) -> QName:
        return self._owlclass_iri

    @property
    def version(self) -> SemanticVersion:
        return self.__version

    @property
    def creator(self) -> Optional[AnyIRI]:
        return self.__creator

    @property
    def created(self) -> Optional[datetime]:
        return self.__created

    @property
    def contributor(self) -> Optional[AnyIRI]:
        return self.__contributor

    @property
    def modified(self) -> Optional[datetime]:
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

    def notifier(self, what: ResourceClassAttribute | QName):
        if isinstance(what, ResourceClassAttribute):
            self._attr_changeset[what] = ResourceClassAttributeChange(None, Action.MODIFY, True)
        elif isinstance(what, QName):
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
    def __query_shacl(con: Connection, graph: NCName, owl_class_iri: QName) -> Attributes:
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
                if isinstance(r['value'], QName):
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    attributes[attriri].append(r['value'])
                elif isinstance(r['value'], OmasStringLiteral):
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
                if QName == self.__datatypes[attr]:
                    self._attributes[attr] = val[0]  # is already QName or AnyIRI from preprocessing
                elif XsdDatatypes == self.__datatypes[attr]:
                    self._attributes[attr] = XsdDatatypes(str(val[0]))
                elif LangString == self.__datatypes[attr]:
                    self._attributes[attr] = LangString(val)
                elif bool == self.__datatypes[attr]:
                    self._attributes[attr] = bool(val[0])
                if getattr(self._attributes[attr], 'set_notifier', None) is not None:
                    self._attributes[attr].set_notifier(self.notifier, attr)

        self.__from_triplestore = True

    @staticmethod
    def __query_resource_props(con: Connection, graph: NCName, owlclass_iri: QName) -> List[Union[PropertyClass, QName]]:
        """
        This method queries and returns a list of properties defined in a sh:NodeShape. The properties may be
        given "inline" as BNode or may be a reference to an external sh:PropertyShape. These external shapes will be
        read when the ResourceClass is constructed (see __init__() of ResourceClass).

        :param con: Connection instance
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
        propinfos: Dict[QName, Attributes] = {}
        #
        # first we run over all triples to gather the information about the properties of the possible
        # BNode based sh:property-Shapes.
        # NOTE: some of the nodes may actually be QNames referencing shapes defines as "standalone" sh:PropertyShape's.
        #
        for r in res:
            if r['value'] == 'rdf:type':
                continue
            if not isinstance(r['attriri'], QName):
                raise OmasError(f"There is some inconsistency in this shape! ({r['attriri']})")
            propnode = r['prop']  # usually a BNode, but may be a reference to a standalone sh:PropertyShape definition
            prop: Union[PropertyClass, QName]
            if isinstance(propnode, QName):
                qname = propnode
                propinfos[qname] = propnode
            elif isinstance(propnode, BNode):
                if propinfos.get(propnode) is None:
                    propinfos[propnode]: Attributes = {}
                attributes: Attributes = propinfos[propnode]
                PropertyClass.process_triple(r, propinfos[propnode])
            else:
                raise OmasError(f'Unexpected type for propnode in SHACL. Type = "{type(propnode)}".')
        #
        # now we collected all the information from the triple store. Let's process the information into
        # a list of full PropertyClasses or QName's to external definitions
        #
        proplist: List[Union[QName, PropertyClass]] = []
        for prop_iri, attributes in propinfos.items():
            if isinstance(attributes, QName):
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
    def read(cls, con: Connection, graph: NCName, owl_class_iri: QName) -> 'ResourceClass':
        attributes = ResourceClass.__query_shacl(con, graph=graph, owl_class_iri=owl_class_iri)
        properties: List[Union[PropertyClass, QName]] = ResourceClass.__query_resource_props(con=con, graph=graph, owlclass_iri=owl_class_iri)
        resclass = cls(con=con, graph=graph, owlclass_iri=owl_class_iri, properties=properties)
        for prop in properties:
            if isinstance(prop, PropertyClass):
                prop.set_notifier(resclass.notifier, prop.property_class_iri)
        resclass._parse_shacl(attributes=attributes)
        resclass.__read_owl()
        return resclass

    def read_modified_shacl(self, *,
                            context: Context,
                            graph: NCName,
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
                            graph: NCName,
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

    def create_shacl(self, timestamp: datetime, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        # for iri, p in self._properties.items():
        #     if p.internal is None and not p.from_triplestore:
        #         #sparql += p.create_shacl(timestamp=timestamp)
        #         sparql += f'{blank:{(indent + 2)*indent_inc}}{iri}Shape a sh:PropertyShape ;\n'
        #         sparql += p.property_node_shacl(timestamp=timestamp, indent=3) + " .\n"
        #         sparql += "\n"

        sparql += f'{blank:{(indent + 1)*indent_inc}}{self._owlclass_iri}Shape a sh:NodeShape, {self._owlclass_iri}'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:targetClass {self._owlclass_iri}'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:hasVersion "{self.__version}"'
        self.__created = timestamp
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:created "{timestamp.isoformat()}"^^xsd:dateTime'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:creator <{self.__creator}>'
        self.__modified = timestamp
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:modified "{timestamp.isoformat()}"^^xsd:dateTime'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:contributor <{self.__contributor}>'
        for attr, value in self._attributes.items():
            if attr == ResourceClassAttribute.SUBCLASS_OF:
                sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}{attr.value} {value}Shape'
            elif attr == ResourceClassAttribute.CLOSED:
                sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:closed {"true" if value else "false"}'
            else:
                sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}{attr.value} {value}'

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

    def create_owl(self, timestamp: datetime, indent: int = 0, indent_inc: int = 4):
        blank = ''
        sparql = ''
        for iri, p in self._properties.items():
            if not p.from_triplestore:
                sparql += p.create_owl_part1(timestamp, indent + 2) + '\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}}{self._owlclass_iri} rdf:type owl:Class ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:hasVersion "{self.__version}" ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:created "{timestamp.isoformat()}"^^xsd:dateTime ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:creator <{self.__creator}> ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:modified "{timestamp.isoformat()}"^^xsd:dateTime ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:contributor <{self.__contributor}> ;\n'
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

    def set_creation_metadata(self, timestamp: datetime):
        self.__created = timestamp
        self.__creator = self._con.userIri
        self.__modified = timestamp
        self.__contributor = self._con.userIri
        self.__from_triplestore = True


    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        if self.__from_triplestore:
            raise OmasErrorAlreadyExists(f'Cannot create property that was read from triplestore before (property: {self._owlclass_iri}')
        timestamp = datetime.now()
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
            timestamp = datetime.now()
            blank = ''
            context = Context(name=self._con.context_name)
            f.write(context.turtle_context)

            f.write(f'{blank:{indent * indent_inc}}{self._graph}:shacl {{\n')
            f.write(self.create_shacl(timestamp=timestamp))
            f.write(f' ;\n{blank:{indent * indent_inc}}}}\n')

            f.write(f'{blank:{indent * indent_inc}}{self._graph}:onto {{\n')
            f.write(self.create_owl(timestamp=timestamp))
            f.write(f'{blank:{indent * indent_inc}}}}\n')

    def __update_shacl(self, timestamp: datetime, indent: int = 0, indent_inc: int = 4) -> str:
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
                                     ele=RdfModifyItem('dcterms:modified', f'"{self.__modified.isoformat()}"^^xsd:dateTime', f'"{timestamp.isoformat()}"^^xsd:dateTime'),
                                     last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def __update_owl(self, timestamp: datetime, indent: int = 0, indent_inc: int = 4) -> str:
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
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?prop rdfs:subClassOf {change.old_value} .\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                if change.action != Action.DELETE:
                    sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?prop rdfs:subClassOf {self._attributes[item]} .\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.owl_class_iri} as ?prop)\n'
                if change.action != Action.CREATE:
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?res rdfs:subClassOf {change.old_value} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?res dcterms:modified ?modified .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = "{timestamp.isoformat()}"^^xsd:dateTime)\n'
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
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.owl_class_iri} as ?res)\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{(indent + 2) * indent_inc}}?node owl:onProperty {prop}\n'
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
                                    ele=RdfModifyItem('dcterms:modified', f'"{self.__modified.isoformat()}"^^xsd:dateTime', f'"{timestamp.isoformat()}"^^xsd:dateTime'),
                                    last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def update(self) -> None:
        timestamp = datetime.now()
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
                    if self._properties[prop].get(PropertyClassAttribute.EXCLUSIVE_FOR) is None:
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
            ?prop rdfs:domain {self._owlclass_iri} .
            ?prop ?p ?v
        }} ;
        WITH {self._graph}:onto
        DELETE {{
            ?res ?prop ?value .
            ?value ?pp ?vv .
        }}
        WHERE {{
            BIND({self._owlclass_iri} AS ?res)
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
        sparql += f"SELECT * FROM {self._graph}:onto WHERE {{ {self._owlclass_iri} ?p ?v }}"
        jsonobj = self._con.transaction_query(sparql)
        res_onto = QueryProcessor(context, jsonobj)
        if len(res_shacl) > 0 or len(res_onto) > 0:
            self._con.transaction_abort()
            raise OmasErrorUpdateFailed(f'Could not delete "{self._owlclass_iri}".')
        else:
            self._con.transaction_commit()


if __name__ == '__main__':
    con = Connection('http://localhost:7200', 'omas')
    omas_project = ResourceClass(con, QName('omas:Project'))
    omas_project.read()
    #print(omas_project)
    #print(omas_project.create(as_string=True))
    #exit(0)
    #omas_project.label = LangString({Languages.EN: '*Omas Project*', Languages.DE: '*Omas-Projekt*'})
    #omas_project.comment_add(Languages.FR, 'Un project pour OMAS')
    #omas_project.closed = False
    #omas_project.subclass_of = QName('omas:Object')
    omas_project[QName('omas:projectEnd')].name = LangString({Language.DE: "Projektende"})
    print(omas_project.update())
    # omas_project2 = ResourceClass(con, QName('omas:OmasProject'))
    # omas_project2.read()
    # print(omas_project2)
    # exit(0)
    #omas_project.closed = False
    #omas_project.update()
    #omas_project2 = ResourceClass(con, QName('omas:OmasProject'))
    #omas_project2.read()
    #print(omas_project2)
    #exit(0)
    #print(omas_project)
    #omas_project.create()
    #exit(-1)
    pdict = {
        QName('omas:commentstr'):
        PropertyClass(con=con,
                      property_class_iri=QName('omas:commentstr'),
                      datatype=XsdDatatypes.string,
                      exclusive_for_class=QName('omas:OmasComment'),
                      restrictions=PropertyRestrictions(
                          min_count=1,
                          language_in={Language.DE, Language.EN},
                          unique_lang=True
                      ),
                      name=LangString({Language.EN: "Comment"}),
                      description=LangString({Language.EN: "A comment to anything"}),
                      order=1),
        QName('omas:creator'):
        PropertyClass(con=con,
                      property_class_iri=QName('omas:creator'),
                      to_node_iri=QName('omas:User'),
                      restrictions=PropertyRestrictions(
                          min_count=1,
                          max_count=1
                      ),
                      order=2),
        QName('omas:createdAt'):
        PropertyClass(con=con,
                      property_class_iri=QName('omas:createdAt'),
                      datatype=XsdDatatypes.dateTime,
                      restrictions=PropertyRestrictions(
                          min_count=1,
                          max_count=1
                      ),
                      order=3)
    }
    comment_class = ResourceClass(
        con=con,
        owlclass_iri=QName('omas:OmasComment'),
        subclass_of=QName('omas:OmasUser'),
        label=LangString({Language.EN: 'Omas Comment', Language.DE: 'Omas Kommentar'}),
        comment=LangString({Language.EN: 'A class to comment something...'}),
        properties=pdict,
        closed=True
    )
    comment_class.create()
    comment_class = None
    comment_class2 = ResourceClass(con=con, owlclass_iri=QName('omas:OmasComment'))
    comment_class2.read()
    print(comment_class2)
