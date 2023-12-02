from dataclasses import dataclass
from datetime import datetime
from typing import Union, Optional, List, Dict
from pystrict import strict
from rdflib import URIRef, Literal, BNode

from omaslib.src.connection import Connection
from omaslib.src.helpers.omaserror import OmasError, OmasErrorNotFound, OmasErrorAlreadyExists
from omaslib.src.helpers.propertyclassattr import PropertyClassAttribute
from omaslib.src.helpers.resourceclassattr import ResourceClassAttribute
from omaslib.src.helpers.semantic_version import SemanticVersion
from omaslib.src.helpers.tools import RdfModifyProp, RdfModifyRes, RdfModifyItem
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.helpers.datatypes import QName, Action, AnyIRI, NCName
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


@strict
class ResourceClass(Model):
    _graph: NCName
    _owl_class_iri: Union[QName, None]
    _attributes: ResourceClassAttributesContainer
    _properties: Dict[QName, Union[PropertyClass, QName]]
    _changeset: Dict[Union[ResourceClassAttribute, QName], ResourceClassAttributeChange]
    __creator: Optional[QName]
    __created: Optional[datetime]
    __contributor: Optional[QName]
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
                 owl_class_iri: Optional[QName] = None,
                 attrs: Optional[ResourceClassAttributesContainer] = None,
                 properties: Optional[List[Union[PropertyClass, QName]]] = None):
        super().__init__(con)
        self._graph = graph
        self._owl_class_iri = owl_class_iri
        self.__creator = None
        self.__created = None
        self.__contributor = None
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
                newprop: PropertyClass
                if isinstance(prop, QName):
                    fixed_prop = QName(str(prop).removesuffix("Shape"))
                    newprop = PropertyClass.read(self._con, self._graph, fixed_prop)
                else:
                    newprop = prop
                self._properties[newprop.property_class_iri] = newprop
                newprop.set_notifier(self.notifier, newprop.property_class_iri)
        self._changeset = {}
        self.__from_triplestore = False

    def __getitem__(self, key: Union[ResourceClassAttribute, QName]) -> Union[AttributeTypes, PropertyClass, QName]:
        if type(key) is ResourceClassAttribute:
            return self._attributes[key]
        elif type(key) is QName:
            return self._properties[key]
        else:
            raise ValueError(f'Invalid key type {type(key)} of key {key}')

    def get(self, key: Union[ResourceClassAttribute, QName]) -> Union[AttributeTypes, PropertyClass, QName, None]:
        if type(key) is ResourceClassAttribute:
            return self._attributes.get(key)
        elif type(key) is QName:
            return self._attributes.get(key)
        else:
            return None

    def __setitem__(self, key: Union[ResourceClassAttribute, QName], value: Union[AttributeTypes, PropertyClass, QName]) -> None:
        if type(key) not in {ResourceClassAttribute, PropertyClass, QName}:
            raise ValueError(f'Invalid key type {type(key)} of key {key}')
        if getattr(value, 'set_notifier', None) is not None:
            value.set_notifier(self.notifier, key)
        if type(key) is ResourceClassAttribute:
            if self._attributes.get(key) is None:  # Attribute not yet set
                if self._changeset.get(key) is None:  # Only first change is recorded
                    self._changeset[key] = ResourceClassAttributeChange(None, Action.CREATE, False)  # TODO: Check if "check_in_use" must be set
            else:
                if self._changeset.get(key) is None:  # Only first change is recorded
                    self._changeset[key] = ResourceClassAttributeChange(self._attributes[key], Action.REPLACE, False)  # TODO: Check if "check_in_use" must be set
            self._attributes[key] = value
        elif isinstance(key, QName):  # QName
            if self._properties.get(key) is None:  # Property not set
                if self._changeset.get(key) is None:
                    self._changeset[key] = ResourceClassAttributeChange(None, Action.CREATE, False)
            else:
                if self._changeset.get(key) is None:
                    self._changeset[key] = ResourceClassAttributeChange(self._properties[key], Action.REPLACE, False)
            if self._properties.get(key) is None:
                try:
                    self._properties[key] = PropertyClass.read(self._con, graph=self._graph, property_class_iri=key)
                except OmasErrorNotFound as err:
                    self._properties[key] = None
            else:
                self._properties[key] = value

    def __delitem__(self, key: Union[ResourceClassAttribute, QName]) -> None:
        if type(key) not in {ResourceClassAttribute, PropertyClass, QName}:
            raise ValueError(f'Invalid key type {type(key)} of key {key}')
        if self._changeset.get(key) is None:
            self._changeset[key] = ResourceClassAttributeChange(self._attributes[key], Action.DELETE, False)
        del self._attributes[key]

    @property
    def owl_class_iri(self) -> QName:
        return self._owl_class_iri

    @property
    def owl_class_iri(self) -> QName:
        return self._owl_class_iri

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
        s = f'Shape: {self._owl_class_iri}Shape\n'
        s += f'{blank:{indent*1}}Attributes:\n'
        for attr, value in self._attributes.items():
            s += f'{blank:{indent*2}}{attr.value} = {value}\n'
        s += f'{blank:{indent*1}}Properties:\n'
        sorted_properties = sorted(self._properties.items(), key=lambda prop: prop[1].order if prop[1].order is not None else 9999)
        for qname, prop in sorted_properties:
            s += f'{blank:{indent*2}}{qname} = {prop}\n'
        return s

    def __changeset_clear(self) -> None:
        for attr, change in self._changeset.items():
            if change.action == Action.MODIFY:
                if isinstance(attr, ResourceClassAttribute):
                    self._attributes[attr].changeset_clear()
                elif isinstance(attr, QName):
                    self._properties[attr].changeset_clear()
                else:
                    raise OmasError("You should never sse this!")
        self._changeset = {}

    def notifier(self, what: Union[ResourceClassAttribute, QName]):
        self._changeset[what] = ResourceClassAttributeChange(None, Action.MODIFY, True)

    @property
    def in_use(self) -> bool:
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT (COUNT(?resinstances) as ?nresinstances)
        WHERE {{
            ?resinstance rdf:type {self._owl_class_iri} .
            FILTER(?resinstances != {self._owl_class_iri}Shape)
        }} LIMIT 2
        """
        res = self._con.rdflib_query(query)
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
        res = con.rdflib_query(query)
        attributes: Attributes = {}
        for r in res:
            attriri = context.iri2qname(r['attriri'])
            if attriri == QName('rdf:type'):
                tmp_owl_class_iri = context.iri2qname(r[1])
                if tmp_owl_class_iri == QName('sh:NodeShape'):
                    continue
                if tmp_owl_class_iri != owl_class_iri:
                    raise OmasError(f'Inconsistent Shape for "{owl_class_iri}": rdf:type="{tmp_owl_class_iri}"')
            elif attriri == QName('sh:property'):
                continue  # processes later – points to a BNode containing
            else:
                attriri = context.iri2qname(r['attriri'])
                if isinstance(r['value'], URIRef):
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    attributes[attriri].append(context.iri2qname(r['value']))
                elif isinstance(r['value'], Literal):
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    if r['value'].language is None:
                        attributes[attriri].append(r['value'].toPython())
                    else:
                        attributes[attriri].append(r['value'].toPython() + '@' + r['value'].language)
                elif isinstance(r['value'], BNode):
                    pass
                else:
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    attributes[attriri].append(r['value'])
        return attributes

    def parse_shacl(self, attributes: Attributes) -> None:
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
    def __query_resource_props(con: Connection, graph: NCName, owl_class_iri: QName) -> List[Union[PropertyClass, QName]]:
        """
        This method queries and returns a list of properties defined in a sh:NodeShape. The properties may be
        given "inline" as BNode or may be a reference to an external sh:PropertyShape. These external shapes will be
        read when the ResourceClass is constructed (see __init__() of ResourceClass).

        :param con: Connection instance
        :param graph: Name of the graph
        :param owl_class_iri: The QName of the OWL class defining the resource. The "Shape" ending will be added
        :return: List of PropertyClasses/QNames
        """

        context = Context(name=con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT ?prop ?attriri ?value ?oo
        FROM {graph}:shacl
        WHERE {{
            BIND({owl_class_iri}Shape AS ?shape)
            ?shape sh:property ?prop .
            OPTIONAL {{
                ?prop ?attriri ?value .
                OPTIONAL {{
                    ?value rdf:rest*/rdf:first ?oo
                }}
            }}
        }}
        """
        res = con.rdflib_query(query)
        propinfos: Dict[QName, Attributes] = {}
        #
        # first we run over all triples to gather the information about the properties of the possible
        # BNode based sh:property-Shapes.
        # NOTE: some of the nodes may actually be QNames referencing shapes defines as "standalone" sh:PropertyShape's.
        #
        for r in res:
            if r['value'] == URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'):
                continue
            if not isinstance(r['attriri'], URIRef):
                raise OmasError(f"There is some inconsistency in this shape! ({r['attriri']})")
            propnode = r['prop']  # usually a BNode, but may be a reference to a standalone sh:PropertyShape definition
            prop: Union[PropertyClass, QName]
            if isinstance(propnode, URIRef):
                qname = context.iri2qname(propnode)
                propinfos[qname] = propnode
            elif isinstance(propnode, BNode):
                if propinfos.get(propnode) is None:
                    propinfos[propnode]: Attributes = {}
                attributes: Attributes = propinfos[propnode]
                PropertyClass.process_triple(context, r, attributes)
            else:
                raise OmasError(f'Unexpected type for propnode in SHACL. Type = "{type(propnode)}".')
            #
            # now we collected all the information from the triple store. Let's process the informationj into
            # a list of full PropertyClasses or QName's to external definitions
            #
        proplist: List[Union[QName, PropertyClass]] = []
        for prop_iri, attributes in propinfos.items():
            if isinstance(attributes, (QName, URIRef)):
                proplist.append(prop_iri)
            else:
                prop = PropertyClass(con=con, graph=graph)
                prop.parse_shacl(attributes=attributes)
                prop.read_owl()
                proplist.append(prop)
        #prop.set_notifier(self.notifier, prop_iri)
        return proplist

    def __read_owl(self):
        context = Context(name=self._con.context_name)
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?prop ?p ?o
        FROM {self._owl_class_iri.prefix}:onto
        WHERE {{
   	        omas:OmasProject rdfs:subClassOf ?prop .
            ?prop ?p ?o .
            FILTER(?o != owl:Restriction)
        }}
        """
        res = self._con.rdflib_query(query1)
        propdict = {}
        for r in res:
            bnode_id = str(r[0])
            if not propdict.get(bnode_id):
                propdict[bnode_id] = {}
            p = context.iri2qname(str(r[1]))
            pstr = str(p)
            if pstr == 'owl:onProperty':
                propdict[bnode_id]['property_iri'] = context.iri2qname(str(r[2]))
            elif pstr == 'owl:onClass':
                propdict[bnode_id]['to_node_iri'] = context.iri2qname(str(r[2]))
            elif pstr == 'owl:minQualifiedCardinality':
                propdict[bnode_id]['min_count'] = r[2].value
            elif pstr == 'owl:maxQualifiedCardinality':
                propdict[bnode_id]['max_count'] = r[2].value
            elif pstr == 'owl:qualifiedCardinality':
                propdict[bnode_id]['min_count'] = r[2].value
                propdict[bnode_id]['max_count'] = r[2].value
            elif pstr == 'owl:onDataRange':
                propdict[bnode_id]['datatype'] = context.iri2qname(str(r[2]))
            else:
                print(f'ERROR ERROR ERROR: Unknown restriction property: "{pstr}"')
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
        properties: List[Union[PropertyClass, QName]] = ResourceClass.__query_resource_props(con=con, graph=graph, owl_class_iri=owl_class_iri)
        resclass = cls(con=con, graph=graph, owl_class_iri=owl_class_iri, properties=properties)
        for prop in properties:
            if isinstance(prop, PropertyClass):
                prop.set_notifier(resclass.notifier, prop.property_class_iri)
        resclass.parse_shacl(attributes=attributes)
        resclass.__read_owl()
        return resclass

    def __create_shacl(self, timestamp: datetime, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ' '
        sparql = ''
        for iri, p in self._properties.items():
            if p.get(PropertyClassAttribute.EXCLUSIVE_FOR) is None and not p.from_triplestore:
                #sparql += p.create_shacl(timestamp=timestamp)
                sparql += f'{blank:{(indent + 2)*indent_inc}}{iri}Shape a sh:PropertyShape ;\n'
                sparql += p.property_node_shacl(timestamp=timestamp, indent=3) + " .\n"
                sparql += "\n"

        sparql += f'{blank:{(indent + 2)*indent_inc}}{self._owl_class_iri}Shape a sh:NodeShape, {self._owl_class_iri}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}sh:targetClass {self._owl_class_iri}'
        if self.__version is not None:
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:hasVersion "{self.__version}"'
        if self.__created is not None:
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created "{self.__created}"^^xsd:dateTime'
        if self.__creator is not None:
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self.__creator}'
        if self.__modified is not None:
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified "{self.__modified}"^^xsd:dateTime'
        if self.__contributor is not None:
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self.__contributor}'
        for attr, value in self._attributes.items():
            if attr == ResourceClassAttribute.SUBCLASS_OF:
                sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{attr.value} {value}Shape'
            elif attr == ResourceClassAttribute.CLOSED:
                sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}sh:closed {"true" if value else "false"}'
            else:
                sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{attr.value} {value}'

        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}sh:property'
        sparql += f'\n{blank:{(indent + 4) * indent_inc}}['
        sparql += f'\n{blank:{(indent + 5) * indent_inc}}sh:path rdf:type'
        sparql += f' ;\n{blank:{(indent + 4) * indent_inc}}]'

        for iri, p in self._properties.items():
            if p.get(PropertyClassAttribute.EXCLUSIVE_FOR) is not None:
                sparql += f' ;\n{blank:{(indent + 3)*indent_inc}}sh:property'
                sparql += f'\n{blank:{(indent + 4)*indent_inc}}[\n'
                sparql += p.property_node_shacl(timestamp=timestamp, indent=5)
                sparql += f' ;\n{blank:{(indent + 4) * indent_inc}}]'
            else:
                sparql += f' ;\n{blank:{(indent + 3)*indent_inc}}sh:property {iri}Shape'
        return sparql

    def __create_owl(self, timestamp: datetime, indent: int = 0, indent_inc: int = 4):
        blank = ''
        sparql = ''
        for iri, p in self._properties.items():
            if not p.from_triplestore:
                sparql += p.create_owl_part1(timestamp, indent + 2) + '\n'
        sparql += f'{blank:{(indent + 2)*indent_inc}}{self._owl_class_iri} rdf:type owl:Class ;\n'
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

    def create(self, indent: int = 0, indent_inc: int = 4, as_string: bool = False) -> Union[str, None]:
        if self.__from_triplestore:
            raise OmasErrorAlreadyExists(f'Cannot create property that was read from triplestore before (property: {self._owl_class_iri}')
        timestamp = datetime.now()
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:shacl {{\n'
        sparql += self.__create_shacl(timestamp=timestamp)
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:onto {{\n'
        sparql += self.__create_owl(timestamp=timestamp)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}}}\n'
        if as_string:
            return sparql
        else:
            self._con.update_query(sparql)
            self.__created = timestamp
            self.__modified = timestamp
            self.__from_triplestore = True

    def __update_shacl(self, timestamp: datetime, indent: int = 0, indent_inc: int = 4) -> str:
        if not self._changeset:
            return ''
        blank = ' '
        sparql_list = []

        for item, change in self._changeset.items():
            if isinstance(item, ResourceClassAttribute):
                sparql = f'#\n# Process "{item.value}" with Action "{change.action.value}"\n#\n'

                sparql += RdfModifyRes.shacl(action=change.action,
                                             graph=self._graph,
                                             owlclass_iri=self._owl_class_iri,
                                             ele=RdfModifyItem(str(item.value),
                                                               None if change.old_value is None else str(change.old_value),
                                                               str(self._attributes[item])),
                                             last_modified=self.__modified)
                sparql_list.append(sparql)
            elif isinstance(item, PropertyClass):
                pass
            elif isinstance(item, QName):
                if change.action == Action.CREATE:
                    if self._properties[item].from_triplestore:
                        #
                        # this property is already defined as standalone, and we already read it at
                        # the time of the assignment. We just have to add the property clause
                        #
                        sparql = f'#\n# Process "QName" with action "{change.action.value}"\n#\n'
                        sparql += RdfModifyRes.shacl(action=change.action,
                                                     graph=self._graph,
                                                     owlclass_iri=self._owl_class_iri,
                                                     ele=RdfModifyItem('sh:property',
                                                                       None if change.old_value is None else str(change.old_value),
                                                                       f'{item}Shape'),
                                                     last_modified=self.__modified)
                        sparql_list.append(sparql)
                    else:
                        #
                        # this property does not exist in triple store -> create it
                        #
                        self._properties[item].create()
                        if self._properties[item].get(PropertyClassAttribute.EXCLUSIVE_FOR) is None:
                            sparql = f'#\n# Process "QName" with action "{change.action.value}"\n#\n'
                            sparql += RdfModifyRes.shacl(action=change.action,
                                                         graph=self._graph,
                                                         owlclass_iri=self._owl_class_iri,
                                                         ele=RdfModifyItem('sh:property',
                                                                           None if change.old_value is None else str(change.old_value),
                                                                           f'{item}Shape'),
                                                         last_modified=self.__modified)
                            sparql_list.append(sparql)


                elif change.action == Action.MODIFY:
                    self._properties[item].update()

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor\n#\n'
        sparql += RdfModifyRes.shacl(action=Action.REPLACE if self.__contributor else Action.CREATE,
                                     graph=self._graph,
                                     owlclass_iri=self._owl_class_iri,
                                     ele=RdfModifyItem('dcterms:contributor', str(self.__contributor), str(self._con.user_iri)),
                                     last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified\n#\n'
        sparql += RdfModifyRes.shacl(action=Action.REPLACE if self.__modified else Action.CREATE,
                                     graph=self._graph,
                                     owlclass_iri=self._owl_class_iri,
                                     ele=RdfModifyItem('dcterms:modified', f'"{self.__modified}"^^xsd:dateTime', f'"{timestamp.isoformat()}"^^xsd:dateTime'),
                                     last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def __update_owl(self, timestamp: datetime, indent: int = 0, indent_inc: int = 4) -> str:
        if not self._changeset:
            return ''
        blank = ''
        sparql_list = []
        for item, change in self._changeset.items():
            if isinstance(item, ResourceClassAttribute):
                #
                # we only need to add rdf:subClassOf to the ontology – all other attributes are irrelevant
                #
                if item == ResourceClassAttribute.SUBCLASS_OF:
                    sparql = f'#\n# Process "{item.value}" with Action "{change.action.value}"\n#\n'
                    sparql += f'WITH {self._graph}:onto\n'
                    if change.action != Action.CREATE:
                        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop rdf:subClassOf {change.old_value} .\n'
                        sparql += f'{blank:{indent * indent_inc}}}}\n'
                    if change.action != Action.DELETE:
                        sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop rdf:subClassOf {self._attributes[item]} .\n'
                        sparql += f'{blank:{indent * indent_inc}}}}\n'
                    sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.owl_class_iri}Shape as ?prop)\n'
                    if change.action != Action.CREATE:
                        sparql += f'{blank:{(indent + 1) * indent_inc}}?res rdf:subClassOf {change.old_value} .\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?res dcterms:modified ?modified .\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = "{timestamp.isoformat()}"^^xsd:dateTime)\n'
                    sparql += f'{blank:{indent * indent_inc}}}}'
                    sparql_list.append(sparql)
            elif isinstance(item, QName):
                sparql = f'#\n# Processing QName (reference to property): {item} for OWL\n#\n'
                sparql += f'WITH {self._graph}:onto\n'
                if change.action != Action.CREATE:
                    pass
                if change.action != Action.DELETE:
                    sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?resource rdf:subClassOf _:bnode .\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}_:bnode a owl:Restriction ;\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}owl:onProperty {item} ;\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.owl_class_iri}Shape as ?resource)\n'
                #if change.action != Action.CREATE:
                #    sparql += f'{blank:{(indent + 2) * indent_inc}}?resource rdf:subClassOf {change.old_value} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?resource dcterms:modified ?modified .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = "{timestamp.isoformat()}"^^xsd:dateTime)\n'
                sparql += f'{blank:{indent * indent_inc}}}}'
                sparql_list.append(sparql)
            else:
                sparql = self._properties[item].update_owl(owlclass_iri=self.owl_class_iri,
                                                           timestamp=timestamp,
                                                           indent=indent, indent_inc=indent_inc)
                sparql_list.append(sparql)
        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor\n#\n'
        sparql += RdfModifyRes.onto(action=Action.REPLACE if self.__contributor else Action.CREATE,
                                    graph=self._graph,
                                    owlclass_iri=self._owl_class_iri,
                                    ele=RdfModifyItem('dcterms:contributor', str(self.__contributor), str(self._con.user_iri)),
                                    last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified\n#\n'
        sparql += RdfModifyRes.onto(action=Action.REPLACE if self.__modified else Action.CREATE,
                                    graph=self._graph,
                                    owlclass_iri=self._owl_class_iri,
                                    ele=RdfModifyItem('dcterms:modified', f'"{self.__modified}"^^xsd:dateTime', f'"{timestamp.isoformat()}"^^xsd:dateTime'),
                                    last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql


    def update(self, as_string: bool = False) -> Union[str, None]:
        timestamp = datetime.now()
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += self.__update_shacl(timestamp=timestamp)
        sparql += ' ;\n'
        sparql += self.__update_owl(timestamp=timestamp)
        if as_string:
            return sparql
        else:
            self._con.update_query(sparql)
        self.__changeset_clear()
        self.__modified = timestamp
        self.__contributor = self._con.user_iri


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
    print(omas_project.update(as_string=True))
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
        owl_class_iri=QName('omas:OmasComment'),
        subclass_of=QName('omas:OmasUser'),
        label=LangString({Language.EN: 'Omas Comment', Language.DE: 'Omas Kommentar'}),
        comment=LangString({Language.EN: 'A class to comment something...'}),
        properties=pdict,
        closed=True
    )
    comment_class.create()
    comment_class = None
    comment_class2 = ResourceClass(con=con, owl_class_iri=QName('omas:OmasComment'))
    comment_class2.read()
    print(comment_class2)
