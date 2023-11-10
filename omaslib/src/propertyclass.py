"""
:Author: Lukas Rosenthaler <lukas.rosenthaler@unibas.ch>
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique
from pprint import pprint
from typing import Union, Set, Optional, Any, Tuple, Dict, Callable

from pystrict import strict
from rdflib import URIRef, Literal, BNode

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
from omaslib.src.helpers.tools import lprint
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.model import Model
from omaslib.src.propertyrestrictions import PropertyRestrictionType, PropertyRestrictions


@unique
class OwlPropertyType(Enum):
    OwlDataProperty = 'owl:DatatypeProperty'
    OwlObjectProperty = 'owl:ObjectProperty'


PropTypes = Union[QName, AnyIRI, OwlPropertyType, XsdDatatypes, PropertyRestrictions, LangString, int, float, None]
PropertyClassAttributesContainer = Dict[PropertyClassAttribute, PropTypes]


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

    def __read_shacl(self) -> None:
        """
        Read the SHACL of a non-exclusive (shared) property (that is a sh:PropertyNode definition)
        :return:
        """
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT ?p ?o ?oo
        FROM {self._property_class_iri.prefix}:shacl
        WHERE {{
            BIND({self._property_class_iri}Shape AS ?shape)
            ?shape ?p ?o .
            OPTIONAL {{
                ?o rdf:rest*/rdf:first ?oo
            }}
        }}
        """
        res = self._con.rdflib_query(query)
        attributes = {}
        for r in res:
            p = context.iri2qname(r['p'])
            if isinstance(r['o'], URIRef):
                if attributes.get(p) is None:
                    attributes[p] = []
                attributes[p].append(context.iri2qname(r['o']))
            elif isinstance(r['o'], Literal):
                if attributes.get(p) is None:
                    attributes[p] = []
                if r['o'].language is None:
                    attributes[p].append(r['o'].toPython())
                else:
                    attributes[p].append(r['o'].toPython() + '@' + r['o'].language)
            elif isinstance(r['o'], BNode):
                pass
            else:
                if attributes.get(p) is None:
                    attributes[p] = []
                attributes[p].append(r['o'])
            if r['p'].fragment == 'languageIn':
                if not attributes.get(p):
                    attributes[p] = set()
                attributes[p].add(Language[r['oo'].toPython().upper()])

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
                self.__created = datetime.fromisoformat(str(val[0]))
            elif key == 'dcterms:contributor':
                self.__contributor = val[0]
            elif key == 'dcterms:modified':
                self.__modified = datetime.fromisoformat(str(val[0]))
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
                    OmasError(f'Invalid shacl definition: "{key} {val}"')
        #
        # setting property type for OWL which distinguished between Data- and Object-^properties
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
                    print('---->', type(self.__modified))
                    print('====>', type(dt))
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

    def read(self):
        self.__read_shacl()
        self.__read_owl()

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
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:created "{timestamp.isoformat()}"^^xsd:datetime'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:contributor {self._con.user_iri}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:modified "{timestamp.isoformat()}"^^xsd:datetime ;\n'
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
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:created "{timestamp.isoformat()}"^^xsd:datetime'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:contributor {self._con.user_iri}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} dcterms:modified "{timestamp.isoformat()}"^^xsd:datetime ;\n'
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

            sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:shacl {{\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {prop.value} ?rval .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:shacl {{\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {prop.value} {self._attributes[prop]} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'

            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:shacl {{\n'
            if owlclass_iri:
                sparql += f'{blank:{(indent + 2) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}?prop sh:path {self._property_class_iri} .\n'
            else:
                sparql += f'{blank:{(indent + 2) * indent_inc}}BIND({self._property_class_iri}Shape as ?prop)\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {prop.value} ?rval .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop dcterms:modified ?modified .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}FILTER(?modified = "{self.__modified.isoformat()}"^^xsd:datetime)\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update the administrative metadata\n#\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:shacl {{\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}?prop dcterms:modified ?modified .\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}?prop dcterms:contributor ?contributor .\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:shacl {{\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}?prop dcterms:modified "{timestamp.isoformat()}"^^xsd:datetime .\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}?prop dcterms:contributor "{self._con.user_iri}" .\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:shacl {{\n'
        if owlclass_iri:
            sparql += f'{blank:{(indent + 2) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop sh:path {self._property_class_iri} .\n'
        else:
            sparql += f'{blank:{(indent + 2) * indent_inc}}BIND({self._property_class_iri}Shape as ?prop)\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}?prop dcterms:modified ?modified .\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}?prop dcterms:contributor ?contributor .\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}FILTER(?modified = "{self.__modified.isoformat()}"^^xsd:datetime)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
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
                if change.action != Action.CREATE:
                    sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:onto {{\n'
                    sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {owl_prop[prop]} ?rval .\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'

                if change.action != Action.DELETE:
                    sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:onto {{\n'
                    sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {owl_prop[prop]} {self._attributes[prop]} .\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'

                sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:onto {{\n'
                if owlclass_iri:
                    sparql += f'{blank:{(indent + 2) * indent_inc}}{owlclass_iri} rdfs:subClassOf ?prop .\n'
                    sparql += f'{blank:{(indent + 2) * indent_inc}}?prop owl:onProperty {self._property_class_iri} .\n'
                else:
                    sparql += f'{blank:{(indent + 2) * indent_inc}}BIND({self._property_class_iri} as ?prop)\n'
                if change.action != Action.CREATE:
                    sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {owl_prop[prop]} ?rval .\n'
                #sparql += f'{blank:{(indent + 2) * indent_inc}}{self._property_class_iri.prefix}:ontology dcterms:modified ?modified .\n'
                #sparql += f'{blank:{(indent + 2) * indent_inc}}FILTER(?modified = "{self.__modified.isoformat()}"^^xsd:datetime)\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}'
                sparql_list.append(sparql)

            if prop == PropertyClassAttribute.DATATYPE or prop == PropertyClassAttribute.TO_NODE_IRI:
                sparql = f'#\n# OWL:\n# Correct OWL property type with Action "{change.action.value}\n#\n'
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:onto {{\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}?prop rdf:type ?proptype .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
                if self._attributes.get(PropertyClassAttribute.TO_NODE_IRI):
                    sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:onto {{\n'
                    sparql += f'{blank:{(indent + 2) * indent_inc}}?prop rdf:type owl:ObjectProperty .\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                else:
                    sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:onto {{\n'
                    sparql += f'{blank:{(indent + 2) * indent_inc}}?prop rdf:type owl:DatatypeProperty .\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:onto {{\n'
                if owlclass_iri:
                    sparql += f'{blank:{(indent + 2) * indent_inc}}{owlclass_iri} rdfs:subClassOf ?prop .\n'
                    sparql += f'{blank:{(indent + 2) * indent_inc}}?prop owl:onProperty {self._property_class_iri} .\n'
                else:
                    sparql += f'{blank:{(indent + 2) * indent_inc}}BIND({self._property_class_iri} as ?prop)\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}?prop rdf:type ?proptype .\n'
                #sparql += f'{blank:{(indent + 2) * indent_inc}}{self._property_class_iri.prefix}:ontology dcterms:modified ?modified .\n'
                #sparql += f'{blank:{(indent + 2) * indent_inc}}FILTER(?modified = "{self.__modified.isoformat()}"^^xsd:datetime)\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}'
                sparql_list.append(sparql)

        #
        # TODO: Update contributor, modified here! Creator and created remain and will not be changed!

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
        #print("BEGIN OWL ******************************************")
        #print(self.__update_owl(timestamp=timestamp))
        #print("END OWL ******************************************")
        #print("BEGIN SPARQL ******************************************")
        #lprint(sparql)
        #print("END SPARQL ******************************************")
        self._con.update_query(sparql)
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
