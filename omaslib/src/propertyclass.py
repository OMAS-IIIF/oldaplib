"""
:Author: Lukas Rosenthaler <lukas.rosenthaler@unibas.ch>
"""
from dataclasses import dataclass
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum, unique
from pprint import pprint
from typing import Union, Set, Optional, Any, Tuple, Dict, Callable, List

from isodate import Duration
from pystrict import strict
from rdflib import URIRef, Literal, BNode
from rdflib.query import ResultRow

from omaslib.src.connection import Connection
from omaslib.src.helpers.Notify import Notify
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import QName, AnyIRI, Action
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.propertyclass_singleton import PropertyClassSingleton
from omaslib.src.helpers.propertyclassprops import PropertyClassAttribute
from omaslib.src.helpers.semantic_version import SemanticVersion
from omaslib.src.helpers.tools import lprint, RdfModifyItem, RdfModifyProp
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.model import Model
from omaslib.src.propertyrestrictions import PropertyRestrictionType, PropertyRestrictions


@unique
class OwlPropertyType(Enum):
    OwlDataProperty = 'owl:DatatypeProperty'
    OwlObjectProperty = 'owl:ObjectProperty'


PropTypes = Union[QName, AnyIRI, OwlPropertyType, XsdDatatypes, PropertyRestrictions, LangString, int, float, None]
PropertyClassAttributesContainer = Dict[PropertyClassAttribute, PropTypes]
Attributes = Dict[QName, List[Any]]


@dataclass
class PropertyClassAttributeChange:
    old_value: PropTypes
    action: Action
    test_in_use: bool


@strict
class PropertyClass(Model, Notify, metaclass=PropertyClassSingleton):
    """
    This class implements the SHACL/OWL property definition that OMAS supports

    """
    _property_class_iri: Union[QName, None]
    _attributes: PropertyClassAttributesContainer
    _changeset: Dict[PropertyClassAttribute, PropertyClassAttributeChange]
    _test_in_use: bool
    _notifier: Union[Callable[[type], None], None]
    #
    # The following attributes of this class cannot be set explicitely by the used
    # They are automatically managed by the OMAS system
    #
    __creator: Optional[QName]
    __created: Optional[datetime]
    __contributor: Optional[QName]
    __modified: Optional[datetime]
    __version: SemanticVersion
    __from_ts: bool

    __datatypes: Dict[PropertyClassAttribute, PropTypes] = {
        PropertyClassAttribute.SUBPROPERTY_OF: {QName},
        PropertyClassAttribute.PROPERTY_TYPE: {OwlPropertyType},
        PropertyClassAttribute.EXCLUSIVE_FOR: {QName},
        PropertyClassAttribute.TO_NODE_IRI: {QName, AnyIRI},
        PropertyClassAttribute.DATATYPE: {XsdDatatypes},
        PropertyClassAttribute.RESTRICTIONS: {PropertyRestrictions},
        PropertyClassAttribute.NAME: {LangString},
        PropertyClassAttribute.DESCRIPTION: {LangString},
        PropertyClassAttribute.ORDER: {int, float}
    }

    def __init__(self, *,
                 con: Connection,
                 property_class_iri: Optional[QName] = None,
                 attrs: Optional[PropertyClassAttributesContainer] = None,
                 notifier: Optional[Callable[[PropertyClassAttribute], None]] = None,
                 notify_data: Optional[PropertyClassAttribute] = None):
        """
        Constructor for PropertyClass

        :param con: A valid instance of the Connection class
        :param property_class_iri: The OWL QName of the property
        :param attrs: Props of this instance
        """
        Model.__init__(self, con)
        Notify.__init__(self, notifier, notify_data)
        self._property_class_iri = property_class_iri
        if attrs is None:
            self._attributes = {}
        else:
            for attr, value in attrs.items():
                if type(attr) is not PropertyClassAttribute:
                    raise OmasError(f'Unsupported Property prop "{attr}"')
                if type(value) not in PropertyClass.__datatypes[attr]:
                    raise OmasError(f'Datatype of prop "{attr.value}": "{type(value)}", should be {PropertyClass.__datatypes[attr]} ({value}) is not valid')
                #
                # if the "value"-class is a subclass of Notify, it has the method "set_notifier".
                # we need to set it!
                #
                if getattr(value, 'set_notifier', None) is not None:
                    value.set_notifier(self.notifier, attr)
            self._attributes = attrs

        # setting property type for OWL which distinguished between Data- and Object-^properties
        if self._attributes:
            if self._attributes.get(PropertyClassAttribute.TO_NODE_IRI) is not None:
                self._attributes[PropertyClassAttribute.PROPERTY_TYPE] = OwlPropertyType.OwlObjectProperty
                dt = self._attributes.get(PropertyClassAttribute.DATATYPE)
                if dt and (dt != XsdDatatypes.anyURI and dt != XsdDatatypes.QName):
                    raise OmasError(f'Datatype "{dt}" not valid for OwlObjectProperty')
            else:
                self._attributes[PropertyClassAttribute.PROPERTY_TYPE] = OwlPropertyType.OwlDataProperty
        self._changeset = {}  # initialize changeset to empty set
        self._test_in_use = False
        self.__creator = None
        self.__created = None
        self.__contributor = None
        self.__modified = None
        self.__version = SemanticVersion()
        self.__from_ts = False

    def __len__(self) -> int:
        return len(self._attributes)

    def __str__(self) -> str:
        propstr = f'Property: {str(self._property_class_iri)};'
        for attr, value in self._attributes.items():
            propstr += f' {attr.value}: {value};'
        return propstr

    def __getitem__(self, attr: PropertyClassAttribute) -> PropTypes:
        return self._attributes[attr]

    def get(self, attr: PropertyClassAttribute) -> Union[PropTypes, None]:
        return self._attributes.get(attr)

    def __setitem__(self, attr: PropertyClassAttribute, value: PropTypes) -> None:
        if type(attr) is not PropertyClassAttribute:
            raise OmasError(f'Unsupported prop {attr}')
        if type(value) not in PropertyClass.__datatypes[attr]:
            raise OmasError(f'Datatype of {attr.value} is not in {PropertyClass.__datatypes[attr]}')

        if self._attributes.get(attr) is None:
            if getattr(value, 'set_notifier', None) is not None:
                value.set_notifier(self.notifier, attr)
            if self._changeset.get(attr) is None:
                self._changeset[attr] = PropertyClassAttributeChange(None, Action.CREATE, True)
            self._attributes[attr] = value
            self.notify()
        else:
            if self._attributes.get(attr) != value:  # we do nothing if nothing changes
                if attr == PropertyClassAttribute.TO_NODE_IRI \
                        and self._attributes.get(PropertyClassAttribute.DATATYPE) \
                        and self._attributes[PropertyClassAttribute.DATATYPE] != XsdDatatypes.anyURI \
                        and self._attributes[PropertyClassAttribute.DATATYPE] != XsdDatatypes.QName:
                    # We have to delete the DATATYPE
                    self._changeset[PropertyClassAttribute.DATATYPE] = PropertyClassAttributeChange(self._attributes[PropertyClassAttribute.DATATYPE], Action.DELETE, True)
                    del self._attributes[PropertyClassAttribute.DATATYPE]
                    self._changeset[attr] = PropertyClassAttributeChange(self._attributes[attr], Action.CREATE, True)
                    self.notify()
                elif attr == PropertyClassAttribute.DATATYPE \
                        and self._attributes.get(PropertyClassAttribute.TO_NODE_IRI) \
                        and value != XsdDatatypes.anyURI \
                        and value != XsdDatatypes.QName:
                    self._changeset[PropertyClassAttribute.TO_NODE_IRI] = PropertyClassAttributeChange(self._attributes[PropertyClassAttribute.TO_NODE_IRI],
                                                                                                    Action.DELETE, True)
                    del self._attributes[PropertyClassAttribute.TO_NODE_IRI]
                    self._changeset[attr] = PropertyClassAttributeChange(self._attributes[attr], Action.CREATE, True)
                    self.notify()
                elif self._changeset.get(attr) is None:
                    self._changeset[attr] = PropertyClassAttributeChange(self._attributes[attr], Action.REPLACE, True)
                self._attributes[attr] = value
                self.notify()

    def __delitem__(self, attr: PropertyClassAttribute) -> None:
        if self._attributes.get(attr) is not None:
            self._changeset[attr] = PropertyClassAttributeChange(self._attributes[attr], Action.DELETE, True)
            del self._attributes[attr]
            self.notify()

    @property
    def property_class_iri(self) -> QName:
        return self._property_class_iri

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
    def modified(self):
        return self.__modified

    @property
    def changeset(self) -> Dict[PropertyClassAttribute, PropertyClassAttributeChange]:
        return self._changeset

    def undo(self, attr: Optional[Union[PropertyClassAttribute, PropertyRestrictionType]] = None) -> None:
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
            if type(attr) is PropertyClassAttribute:
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
            elif type(attr) is PropertyRestrictionType:
                self._attributes[PropertyClassAttribute.RESTRICTIONS].undo(attr)
                if len(self._attributes[PropertyClassAttribute.RESTRICTIONS]) == 0:
                    del self._attributes[PropertyClassAttribute.RESTRICTIONS]
                if len(self._attributes[PropertyClassAttribute.RESTRICTIONS].changeset) == 0:
                    del self._changeset[PropertyClassAttribute.RESTRICTIONS]

    def __changeset_clear(self) -> None:
        for attr, change in self._changeset.items():
            if change.action == Action.MODIFY:
                self._attributes[attr].changeset_clear()
        self._changeset = {}

    def notifier(self, attr: PropertyClassAttribute) -> None:
        self._changeset[attr] = PropertyClassAttributeChange(None, Action.MODIFY, True)

    @property
    def in_use(self):
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT (COUNT(?rinstances) as ?nrinstances)
        WHERE {{
            ?rinstances {self._property_class_iri} ?value
        }} LIMIT 2
        """
        res = self._con.rdflib_query(query)
        if len(res) != 1:
            raise OmasError('Internal Error in "propertyClass.in_use"')
        for r in res:
            if int(r.nresinstances) > 0:
                return True
            else:
                return False

    def delete_singleton(self) -> None:
        del self._cache[str(self._property_class_iri)]

    @staticmethod
    def process_triple(context: Context, r: ResultRow, attributes: Attributes) -> None:
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
        if r['attriri'].fragment == 'languageIn':
            if not attributes.get(attriri):
                attributes[attriri] = set()
            attributes[attriri].add(Language[r['oo'].toPython().upper()])

    @staticmethod
    def __query_shacl(con: Connection, property_class_iri: QName) -> Attributes:
        context = Context(name=con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT ?attriri ?value ?oo
        FROM {property_class_iri.prefix}:shacl
        WHERE {{
            BIND({property_class_iri}Shape AS ?shape)
            ?shape ?attriri ?value .
            OPTIONAL {{
                ?value rdf:rest*/rdf:first ?oo
            }}
        }}
        """
        res = con.rdflib_query(query)
        attributes: Attributes = {}
        for r in res:
            PropertyClass.process_triple(context, r, attributes)
        return attributes

    def parse_shacl(self, attributes: Attributes) -> None:
        """
        Read the SHACL of a non-exclusive (shared) property (that is a sh:PropertyNode definition)
        :return:
        """
        self._attributes[PropertyClassAttribute.RESTRICTIONS] = PropertyRestrictions()
        #
        # Create a set of all PropertyClassProp-strings, e.g. {"sh:path", "sh:datatype" etc.}
        #
        propkeys = {QName(x.value) for x in PropertyClassAttribute}
        for key, val in attributes.items():
            if key == 'rdf:type':
                if val[0] == 'sh:PropertyShape':
                    continue
                else:
                    raise OmasError(f'Inconsistency, expected "sh:PropertyType", got "{val[0]}".')
            elif key == 'sh:path':
                self._property_class_iri = val[0]
            elif key == 'dcterms:hasVersion':
                self.__version = SemanticVersion.fromString(val[0])
            elif key == 'dcterms:creator':
                self.__creator = val[0]
            elif key == 'dcterms:created':
                self.__created = val[0]
            elif key == 'dcterms:contributor':
                self.__contributor = val[0]
            elif key == 'dcterms:modified':
                self.__modified = val[0]
            elif key in propkeys:
                attr = PropertyClassAttribute(key)
                if {QName, AnyIRI} == self.__datatypes[attr]:
                    self._attributes[attr] = val[0]  # is already QName or AnyIRI from preprocessing
                elif {XsdDatatypes} == self.__datatypes[attr]:
                    self._attributes[attr] = XsdDatatypes(str(val[0]))
                elif {LangString} == self.__datatypes[attr]:
                    self._attributes[attr] = LangString(val)
                elif {int, float} == self.__datatypes[attr]:
                    self._attributes[attr] = val[0]
            else:
                try:
                    self._attributes[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType(key)] = val if key == "sh:languageIn" else val[0]
                except (ValueError, TypeError) as err:
                    raise OmasError(f'Invalid shacl definition of PropertyClass attribute: "{key} {val}"')
        #
        # setting property type for OWL which distinguished between Data- and Object-properties
        #
        if self._attributes.get(PropertyClassAttribute.TO_NODE_IRI) is not None:
            self._attributes[PropertyClassAttribute.PROPERTY_TYPE] = OwlPropertyType.OwlObjectProperty
            dt = self._attributes.get(PropertyClassAttribute.DATATYPE)
            if dt and (dt != XsdDatatypes.anyURI and dt != XsdDatatypes.QName):
                raise OmasError(f'Datatype "{dt}" not valid for OwlObjectProperty')
        else:
            self._attributes[PropertyClassAttribute.PROPERTY_TYPE] = OwlPropertyType.OwlDataProperty
        for attr, value in self._attributes.items():
            if getattr(value, 'set_notifier', None) is not None:
                value.set_notifier(self.notifier, attr)
        self.__from_ts = True

    def __read_owl(self):
        context = Context(name=self._con.context_name)
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?p ?o
        FROM {self._property_class_iri.prefix}:onto
        WHERE {{
            {self._property_class_iri} ?p ?o
        }}
        """
        res = self._con.rdflib_query(query1)
        datatype = None
        to_node_iri = None
        for r in res:
            attr = context.iri2qname(r['p'])
            obj = context.iri2qname(r['o']) if isinstance(r['o'], URIRef) else r['o']
            if str(attr) == 'rdf:type':
                if str(obj) == 'owl:DatatypeProperty':
                    self._attributes[PropertyClassAttribute.PROPERTY_TYPE] = OwlPropertyType.OwlDataProperty
                elif str(obj) == 'owl:ObjectProperty':
                    self._attributes[PropertyClassAttribute.PROPERTY_TYPE] = OwlPropertyType.OwlObjectProperty
            elif attr == 'owl:subPropertyOf':
                self._attributes[PropertyClassAttribute.SUBPROPERTY_OF] = obj
            elif attr == 'rdfs:range':
                if obj.prefix == 'xsd':
                    datatype = obj
                else:
                    to_node_iri = obj
            elif attr == 'rdfs:domain':
                self._exclusive_for_class = obj
            elif attr == 'dcterms:creator':
                if self.__creator != obj:
                    raise OmasError(f'Inconsistency between SHACL and OWL: creator {self.__creator} vs {obj}.')
            elif attr == 'dcterms:created':
                dt = datetime.fromisoformat(obj)
                if self.__created != dt:
                    raise OmasError(f'Inconsistency between SHACL and OWL: created {self.__created} vs {dt}.')
            elif attr == 'dcterms:contributor':
                if self.__creator != obj:
                    raise OmasError(f'Inconsistency between SHACL and OWL: contributor {self.__contributor} vs {obj}.')
            elif attr == 'dcterms:modified':
                dt = datetime.fromisoformat(obj)
                if self.__modified != dt:
                    raise OmasError(f'Inconsistency between SHACL and OWL: created {self.__modified} vs {dt}.')
        #
        # Consistency checks
        #
        if self._attributes[PropertyClassAttribute.PROPERTY_TYPE] == OwlPropertyType.OwlDataProperty:
            if not datatype:
                raise OmasError(f'OwlDataProperty "{self._property_class_iri}" has no rdfs:range datatype defined!')
            if datatype != self._attributes[PropertyClassAttribute.DATATYPE].value:
                raise OmasError(
                    f'Property has inconsistent datatype definitions: OWL: "{datatype}" vs. SHACL: "{self._attributes[PropertyClassAttribute.DATATYPE].value}"')
        if self._attributes[PropertyClassAttribute.PROPERTY_TYPE] == OwlPropertyType.OwlObjectProperty:
            if not to_node_iri:
                raise OmasError(f'OwlObjectProperty "{self._property_class_iri}" has no rdfs:range resource class defined!')
            if to_node_iri != self._attributes.get(PropertyClassAttribute.TO_NODE_IRI):
                raise OmasError(
                    f'Property has inconsistent object type definition: OWL: "{to_node_iri}" vs. SHACL: "{self._attributes.get(PropertyClassAttribute.TO_NODE_IRI)}".')

    @classmethod
    def read(cls, con: Connection, property_class_iri: QName) -> 'PropertyClass':
        property = cls(con=con, property_class_iri=property_class_iri)
        attributes = PropertyClass.__query_shacl(con, property_class_iri)
        property.parse_shacl(attributes=attributes)
        property.__read_owl()
        return property

    def property_node_shacl(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{(indent + 1) * indent_inc}}sh:path {self._property_class_iri}'
        for prop, value in self._attributes.items():
            if prop == PropertyClassAttribute.PROPERTY_TYPE:
                continue
            if prop != PropertyClassAttribute.RESTRICTIONS:
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}{prop.value} {value.value if isinstance(value, Enum) else value}'
            else:
                sparql += self._attributes[PropertyClassAttribute.RESTRICTIONS].create_shacl(indent + 1, indent_inc)
        sparql += f' .\n'
        return sparql

    def __create_shacl(self, timestamp: datetime, indent: int = 0, indent_inc: int = 4, as_string: bool = False) -> Union[str, None]:
        blank = ''
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}{self._property_class_iri}Shape a sh:PropertyShape'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:hasVersion "{str(self.__version)}"'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:creator {self._con.user_iri}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:created "{timestamp.isoformat()}"^^xsd:dateTime'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:contributor {self._con.user_iri}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:modified "{timestamp.isoformat()}"^^xsd:dateTime ;\n'
        sparql += self.property_node_shacl(indent, indent_inc)
        return sparql

    def __create_owl(self, timestamp: datetime, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent * indent_inc}}{self._property_class_iri} rdf:type {self._attributes[PropertyClassAttribute.PROPERTY_TYPE].value}'
        if self._attributes.get(PropertyClassAttribute.SUBPROPERTY_OF):
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} rdfs:subPropertyOf {self._attributes[PropertyClassAttribute.SUBPROPERTY_OF]}'
        if self._attributes.get(PropertyClassAttribute.EXCLUSIVE_FOR):
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} rdfs:domain {self._attributes[PropertyClassAttribute.EXCLUSIVE_FOR]}'
        if self._attributes.get(PropertyClassAttribute.PROPERTY_TYPE) == OwlPropertyType.OwlDataProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} rdfs:range {self._attributes[PropertyClassAttribute.DATATYPE].value}'
        elif self._attributes.get(PropertyClassAttribute.PROPERTY_TYPE) == OwlPropertyType.OwlObjectProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} rdfs:range {self._attributes[PropertyClassAttribute.TO_NODE_IRI]}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:creator {self._con.user_iri}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:created "{timestamp.isoformat()}"^^xsd:dateTime'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:contributor {self._con.user_iri}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:modified "{timestamp.isoformat()}"^^xsd:dateTime ;\n'
        sparql += ' .\n'
        return sparql

    def create_owl_part2(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent * indent_inc}}[\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}} rdf:type owl:Restriction ;\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}} owl:onProperty {self._property_class_iri}'
        sparql += self._restrictions.create_owl(indent + 1, indent_inc)
        if self._attributes[PropertyClassAttribute.PROPERTY_TYPE] == OwlPropertyType.OwlDataProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} owl:onDataRange {self._attributes[PropertyClassAttribute.DATATYPE].value}'
        elif self._attributes[PropertyClassAttribute.PROPERTY_TYPE] == OwlPropertyType.OwlObjectProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} owl:onClass {self._attributes[PropertyClassAttribute.TO_NODE_IRI]}'
        sparql += f' ;\n{blank:{indent * indent_inc}}]'
        return sparql

    def create(self, indent: int = 0, indent_inc: int = 4, as_string: bool = False):
        if self.__from_ts:
            raise OmasError(f'Cannot create property that was read from TS before (property: {self._property_class_iri}')
        timestamp = datetime.now()
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:shacl {{\n'
        sparql += self.__create_shacl(timestamp=timestamp, indent=2)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:onto {{\n'
        sparql += self.__create_owl(timestamp=timestamp, indent=2)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}}}\n'
        if as_string:
            return sparql
        else:
            self._con.update_query(sparql)
        self.__created = timestamp
        self.__modified = timestamp

    def __update_shacl(self, *,
                       owlclass_iri: Optional[QName] = None,
                       timestamp: datetime,
                       indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql_list = []
        for prop, change in self._changeset.items():
            sparql = f'#\n# SHACL\n# Process "{prop.value}" with Action "{change.action.value}"\n#\n'
            if change.action == Action.MODIFY:
                if PropertyClass.__datatypes[prop] == {LangString}:
                    sparql += self._attributes[prop].update_shacl(owlclass_iri=owlclass_iri,
                                                                  prop_iri=self._property_class_iri,
                                                                  prop=prop,
                                                                  modified=self.__modified,
                                                                  indent=indent, indent_inc=indent_inc)
                elif PropertyClass.__datatypes[prop] == {PropertyRestrictions}:
                    sparql += self._attributes[prop].update_shacl(owlclass_iri=owlclass_iri,
                                                                  prop_iri=self._property_class_iri,
                                                                  modified=self.__modified,
                                                                  indent=indent, indent_inc=indent_inc)
                else:
                    raise OmasError(f'SHACL property {prop.value} should not have update action "Update".')
                sparql_list.append(sparql)
                continue

            ele = RdfModifyItem(prop.value,
                                str(change.old_value) if change.action != Action.CREATE else None,
                                str(self._attributes[prop]) if change.action != Action.DELETE else None)
            sparql += RdfModifyProp.shacl(action=change.action,
                                          owlclass_iri=owlclass_iri,
                                          pclass_iri=self._property_class_iri,
                                          graph=QName(f'{self._property_class_iri.prefix}:shacl'),
                                          ele=ele,
                                          last_modified=self.__modified)
            sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor\n#\n'
        sparql += RdfModifyProp.shacl(action=Action.REPLACE if self.__contributor else Action.CREATE,
                                      owlclass_iri=owlclass_iri,
                                      pclass_iri=self._property_class_iri,
                                      graph=QName(f'{self._property_class_iri.prefix}:shacl'),
                                      ele=RdfModifyItem('dcterms:contributor', self.__contributor, self._con.user_iri),
                                      last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified\n#\n'
        sparql += RdfModifyProp.shacl(action=Action.REPLACE if self.__modified else Action.CREATE,
                                      owlclass_iri=owlclass_iri,
                                      pclass_iri=self._property_class_iri,
                                      graph=QName(f'{self._property_class_iri.prefix}:shacl'),
                                      ele=RdfModifyItem('dcterms:modified', f'"{self.__modified}"^^xsd:dateTime', f'"{timestamp.isoformat()}"^^xsd:dateTime'),
                                      last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = ";\n".join(sparql_list)
        return sparql

    def __update_owl(self, *,
                     owlclass_iri: Optional[QName] = None,
                     timestamp: datetime,
                     indent: int = 0, indent_inc: int = 4) -> str:
        owl_propclass_attributes = {PropertyClassAttribute.SUBPROPERTY_OF,  # should be in OWL ontology
                                    PropertyClassAttribute.DATATYPE,  # used for rdfs:range in OWL ontology
                                    PropertyClassAttribute.TO_NODE_IRI}  # used for rdfs:range in OWL ontology
        owl_prop = {PropertyClassAttribute.SUBPROPERTY_OF: PropertyClassAttribute.SUBPROPERTY_OF.value,
                    PropertyClassAttribute.DATATYPE: "rdfs:range",
                    PropertyClassAttribute.TO_NODE_IRI: "rdfs:range"}
        blank = ''
        sparql_list = []
        for prop, change in self._changeset.items():
            if prop == PropertyClassAttribute.RESTRICTIONS and change.action == Action.MODIFY:
                self._attributes[prop].update_owl(owlclass_iri=owlclass_iri,
                                                  prop_iri=self._property_class_iri,
                                                  modified=self.__modified,
                                                  indent=indent, indent_inc=indent_inc)
            if prop in owl_propclass_attributes:
                sparql = f'#\n# OWL:\n# Process "{owl_prop[prop]}" with Action "{change.action.value}"\n#\n'
                ele = RdfModifyItem(property=owl_prop[prop],
                                    old_value=str(change.old_value) if change.action != Action.CREATE else None,
                                    new_value=str(self._attributes[prop]) if change.action != Action.DELETE else None)
                sparql += RdfModifyProp.onto(action=change.action,
                                             owlclass_iri=owlclass_iri,
                                             pclass_iri=self._property_class_iri,
                                             graph=QName(f'{self._property_class_iri.prefix}:onto'),
                                             ele=ele,
                                             last_modified=self.__modified,
                                             indent=indent, indent_inc=indent_inc)
                sparql_list.append(sparql)

            if prop == PropertyClassAttribute.DATATYPE or prop == PropertyClassAttribute.TO_NODE_IRI:
                ele: RdfModifyItem
                if self._attributes.get(PropertyClassAttribute.TO_NODE_IRI):
                    ele = RdfModifyItem('rdf:type', QName('owl:DatatypeProperty'), QName('owl:ObjectProperty'))
                else:
                    ele = RdfModifyItem('rdf:type', QName('owl:ObjectProperty'), QName('owl:DatatypeProperty'))
                sparql = f'#\n# OWL:\n# Correct OWL property type with Action "{change.action.value}\n#\n'
                sparql += RdfModifyProp.onto(action=Action.REPLACE,
                                             owlclass_iri=owlclass_iri,
                                             pclass_iri=self._property_class_iri,
                                             graph=QName(f'{self._property_class_iri.prefix}:onto'),
                                             ele=ele,
                                             last_modified=self.__modified,
                                             indent=indent, indent_inc=indent_inc)

                sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor\n#\n'
        sparql += RdfModifyProp.onto(action=Action.REPLACE if self.__contributor else Action.CREATE,
                                     owlclass_iri=owlclass_iri,
                                     pclass_iri=self._property_class_iri,
                                     graph=QName(f'{self._property_class_iri.prefix}:shacl'),
                                     ele=RdfModifyItem('dcterms:contributor', self.__contributor, self._con.user_iri),
                                     last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified\n#\n'
        sparql += RdfModifyProp.onto(action=Action.REPLACE if self.__modified else Action.CREATE,
                                     owlclass_iri=owlclass_iri,
                                     pclass_iri=self._property_class_iri,
                                     graph=QName(f'{self._property_class_iri.prefix}:shacl'),
                                     ele=RdfModifyItem('dcterms:modified', f'"{self.__modified}"^^xsd:dateTime', f'"{timestamp.isoformat()}"^^xsd:dateTime'),
                                     last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = ";\n".join(sparql_list)
        return sparql

    def update(self) -> None:
        timestamp = datetime.now()
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += self.__update_shacl(timestamp=timestamp)
        sparql += ";\n"
        sparql += self.__update_owl(timestamp=timestamp)
        self._con.update_query(sparql)

        for prop, change in self._changeset.items():
            if change.action == Action.MODIFY:
                self._attributes[prop].changeset_clear()
        self.__changeset_clear()
        self.__modified = timestamp
        self.__contributor = self._con.user_iri

    def delete_shacl(self, indent: int = 0, indent_inc: int = 4) -> None:
        self.__from_ts = False
        pass


if __name__ == '__main__':
    con = Connection('http://localhost:7200', 'omas')
    pclass1 = PropertyClass(con=con, property_class_iri=QName('omas:comment'))
    pclass1.read()
    print(pclass1)

    pclass2 = PropertyClass(con=con, property_class_iri=QName('omas:test'))
    pclass2.read()
    print(pclass2)
