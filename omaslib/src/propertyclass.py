"""
:Author: Lukas Rosenthaler <lukas.rosenthaler@unibas.ch>
"""
from dataclasses import dataclass
from enum import Enum, unique
from pprint import pprint
from typing import Union, Set, Optional, Any, Tuple, Dict

from pystrict import strict
from rdflib import URIRef, Literal, BNode

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import QName, AnyIRI, Action
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.propertyclass_singleton import PropertyClassSingleton
from omaslib.src.helpers.propertyclassprops import PropertyClassProp
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.model import Model
from omaslib.src.propertyrestrictions import PropertyRestrictionType, PropertyRestrictions


@unique
class OwlPropertyType(Enum):
    OwlDataProperty = 'owl:DatatypeProperty'
    OwlObjectProperty = 'owl:ObjectProperty'


PropTypes = Union[QName, AnyIRI, OwlPropertyType, XsdDatatypes, PropertyRestrictions, LangString, int, float, None]
PropertyClassPropsContainer = Dict[PropertyClassProp, PropTypes]


@dataclass
class PropertyClassPropChange:
    old_value: PropTypes
    action: Action
    test_in_use: bool

@strict
class PropertyClass(Model, metaclass=PropertyClassSingleton):
    """
    This class implements the SHACL/OWL property definition that OMAS supports

    """
    _property_class_iri: Union[QName, None]
    _props: PropertyClassPropsContainer

    _changeset: Dict[PropertyClassProp, PropertyClassPropChange]
    _test_in_use: bool

    __datatypes: Dict[PropertyClassProp, PropTypes] = {
        PropertyClassProp.SUBPROPERTY_OF: {QName},
        PropertyClassProp.PROPERTY_TYPE: {OwlPropertyType},
        PropertyClassProp.EXCLUSIVE_FOR: {QName},
        PropertyClassProp.TO_NODE_IRI: {QName, AnyIRI},
        PropertyClassProp.DATATYPE: {XsdDatatypes},
        PropertyClassProp.RESTRICTIONS: {PropertyRestrictions},
        PropertyClassProp.NAME: {LangString},
        PropertyClassProp.DESCRIPTION: {LangString},
        PropertyClassProp.ORDER: {int, float}
    }

    def __init__(self, *,
                 con: Connection,
                 property_class_iri: Optional[QName] = None,
                 props: Optional[PropertyClassPropsContainer] = None):
        """
        Constructor for PropertyClass

        :param con: A valid instance of the Connection class
        :param property_class_iri: The OWL QName of the property
        :param props: Props of this instance
        """
        super().__init__(con)
        self._property_class_iri = property_class_iri
        if props is None:
            self._props = {}
        else:
            for prop, value in props.items():
                if type(prop) is not PropertyClassProp:
                    raise OmasError(f'Unsupported Property prop "{prop}"')
                if type(value) not in PropertyClass.__datatypes[prop]:
                    raise OmasError(f'Datatype of prop "{prop.value}": "{type(value)}", should be {PropertyClass.__datatypes[prop]} ({value}) is not valid')
                #
                # if the "value"-class is a subclass of Notify, it has the method "set_notifier".
                # we need to set it!
                #
                if getattr(value, 'set_notifier', None) is not None:
                    value.set_notifier(self.notifier, prop)
            self._props = props

        # setting property type for OWL which distinguished between Data- and Object-^properties
        if self._props.get(PropertyClassProp.TO_NODE_IRI) is not None:
            self._props[PropertyClassProp.PROPERTY_TYPE] = OwlPropertyType.OwlObjectProperty
            dt = self._props.get(PropertyClassProp.DATATYPE)
            if dt and (dt != XsdDatatypes.anyURI and dt != XsdDatatypes.QName):
                raise OmasError(f'Datatype "{dt}" not valid for OwlObjectProperty')
        else:
            self._props[PropertyClassProp.PROPERTY_TYPE] = OwlPropertyType.OwlDataProperty
        self._changeset = {}  # initialize changeset to empty set
        self._test_in_use = False

    def __str__(self):
        propstr = f'Property: {str(self._property_class_iri)};'
        for prop, value in self._props.items():
            propstr += f' {prop.value}: {value};'
        return propstr

    def __getitem__(self, prop: PropertyClassProp) -> PropTypes:
        return self._props[prop]

    def get(self, prop: PropertyClassProp) -> Union[PropTypes, None]:
        return self._props.get(prop)

    def __setitem__(self, prop: PropertyClassProp, value: PropTypes) -> None:
        if type(prop) is not PropertyClassProp:
            raise OmasError(f'Unsupported prop {prop}')
        if type(value) not in PropertyClass.__datatypes[prop]:
            raise OmasError(f'Datatype of {prop.value} is not in {PropertyClass.__datatypes[prop]}')
        if self._props.get(prop) is None:
            if getattr(value, 'set_notifier', None) is not None:
                value.set_notifier(self.notifier, prop)
            if self._changeset.get(prop) is None:
                self._changeset[prop] = PropertyClassPropChange(self._props[prop], Action.CREATE, True)
            self._props[prop] = value
        else:
            if self._props.get(prop) != value:
                if self._changeset.get(prop) is None:
                    self._changeset[prop] = PropertyClassPropChange(self._props[prop], Action.REPLACE, True)
                self._props[prop] = value

    def __delitem__(self, prop: PropertyClassProp) -> None:
        if self._props.get(prop) is not None:
            self._changeset[prop] = PropertyClassPropChange(self._props[prop], Action.DELETE, True)
            del self._props[prop]

    @property
    def property_class_iri(self) -> QName:
        return self._property_class_iri

    @property_class_iri.setter
    def property_class_iri(self, value: Any):
        OmasError(f'property_class_iri_class cannot be set!')

    @property
    def changeset(self) -> Dict[PropertyClassProp, PropertyClassPropChange]:
        return self._changeset

    def __changeset_clear(self) -> None:
        for prop, change in self._changeset.items():
            if change.action == Action.MODIFY:
                self._props[prop].changeset_clear()
        self._changeset = {}

    def notifier(self, prop: PropertyClassProp) -> None:
        self._changeset[prop] = PropertyClassPropChange(None, Action.MODIFY, True)

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
        properties = {}
        for r in res:
            p = context.iri2qname(r[0])
            if isinstance(r[1], URIRef):
                if properties.get(p) is None:
                    properties[p] = []
                properties[p].append(context.iri2qname(r[1]))
            elif isinstance(r[1], Literal):
                if properties.get(p) is None:
                    properties[p] = []
                if r[1].language is None:
                    properties[p].append(r[1].toPython())
                else:
                    properties[p].append(r[1].toPython() + '@' + r[1].language)
            elif isinstance(r[1], BNode):
                pass
            else:
                if properties.get(p) is None:
                    properties[p] = []
                properties[p].append(r[1])
            if r[0].fragment == 'languageIn':
                if not properties.get(p):
                    properties[p] = set()
                properties[p].add(Language[r[2].toPython().upper()])

        self._props[PropertyClassProp.RESTRICTIONS] = PropertyRestrictions()
        #
        # Create a set of all PropertyClassProp-strings, e.g. {"sh:path", "sh:datatype" etc.}
        #
        propkeys = {QName(x.value) for x in PropertyClassProp}
        for key, val in properties.items():
            if key == 'rdf:type':
                if val[0] == 'sh:PropertyShape':
                    continue
                else:
                    raise OmasError(f'Inconsistency, expected "sh:PropertyType", got "{val[0]}".')
            elif key == 'sh:path':
                self._property_class_iri = val[0]
            elif key in propkeys:
                prop = PropertyClassProp(key)
                if {QName, AnyIRI} == self.__datatypes[prop]:
                    self._props[prop] = val[0]  # is already QName or AnyIRI from preprocessing
                elif {XsdDatatypes} == self.__datatypes[prop]:
                    self._props[prop] = XsdDatatypes(str(val[0]))
                elif {LangString} == self.__datatypes[prop]:
                    self._props[prop] = LangString(val)
                elif {int, float} == self.__datatypes[prop]:
                    self._props[prop] = val[0]
            else:
                try:
                    self._props[PropertyClassProp.RESTRICTIONS][PropertyRestrictionType(key)] = val if key == "sh:languageIn" else val[0]
                except (ValueError, TypeError) as err:
                    OmasError(f'Invalid shacl definition: "{key} {val}"')
        #
        # setting property type for OWL which distinguished between Data- and Object-^properties
        #
        if self._props.get(PropertyClassProp.TO_NODE_IRI) is not None:
            self._props[PropertyClassProp.PROPERTY_TYPE] = OwlPropertyType.OwlObjectProperty
            dt = self._props.get(PropertyClassProp.DATATYPE)
            if dt and (dt != XsdDatatypes.anyURI and dt != XsdDatatypes.QName):
                raise OmasError(f'Datatype "{dt}" not valid for OwlObjectProperty')
        else:
            self._props[PropertyClassProp.PROPERTY_TYPE] = OwlPropertyType.OwlDataProperty
        for prop, value in self._props.items():
            if getattr(value, 'set_notifier', None) is not None:
                value.set_notifier(self.notifier, prop)

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
        obj_prop = False
        for r in res:
            prop = context.iri2qname(r[0])
            obj = context.iri2qname(r[1])
            if str(prop) == 'rdf:type':
                if str(obj) == 'owl:DatatypeProperty':
                    self._props[PropertyClassProp.PROPERTY_TYPE] = OwlPropertyType.OwlDataProperty
                elif str(obj) == 'owl:ObjectProperty':
                    self._props[PropertyClassProp.PROPERTY_TYPE] = OwlPropertyType.OwlObjectProperty
            elif prop == 'owl:subPropertyOf':
                self._props[PropertyClassProp.SUBPROPERTY_OF] = obj
            elif prop == 'rdfs:range':
                if obj.prefix == 'xsd':
                    datatype = obj
                else:
                    to_node_iri = obj
            elif prop == 'rdfs:domain':
                self._exclusive_for_class = obj
        #
        # Consistency checks
        #
        if self._props[PropertyClassProp.PROPERTY_TYPE] == OwlPropertyType.OwlDataProperty:
            if not datatype:
                raise OmasError(f'OwlDataProperty "{self._property_class_iri}" has no rdfs:range datatype defined!')
            if datatype != self._props[PropertyClassProp.DATATYPE].value:
                raise OmasError(
                    f'Property has inconsistent datatype definitions: OWL: "{datatype}" vs. SHACL: "{self._props[PropertyClassProp.DATATYPE].value}"')
        if self._props[PropertyClassProp.PROPERTY_TYPE] == OwlPropertyType.OwlObjectProperty:
            if not to_node_iri:
                raise OmasError(f'OwlObjectProperty "{self._property_class_iri}" has no rdfs:range resource class defined!')
            if to_node_iri != self._props[PropertyClassProp.TO_NODE_IRI]:
                raise OmasError(
                    f'Property has inconsistent object type definition: OWL: "{to_node_iri}" vs. SHACL: "{self._props[PropertyClassProp.TO_NODE_IRI]}".')

    def read(self):
        self.__read_shacl()
        self.__read_owl()

    def property_node_shacl(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{(indent + 1) * indent_inc}}sh:path {self._property_class_iri}'
        for prop, value in self._props.items():
            if prop == PropertyClassProp.PROPERTY_TYPE:
                continue
            if prop != PropertyClassProp.RESTRICTIONS:
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}{prop.value} {value.value if isinstance(value, Enum) else value}'
            else:
                sparql += self._props[PropertyClassProp.RESTRICTIONS].create_shacl(indent + 1, indent_inc)
        sparql += f' .\n'
        return sparql

    def __create_shacl(self, indent: int = 0, indent_inc: int = 4, as_string: bool = False) -> Union[str, None]:
        blank = ''
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}{self._property_class_iri}Shape a sh:PropertyShape ;\n'
        sparql += self.property_node_shacl(indent, indent_inc)
        return sparql

    def __create_owl(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent * indent_inc}}{self._property_class_iri} rdf:type {self._props[PropertyClassProp.PROPERTY_TYPE].value}'
        if self._props.get(PropertyClassProp.SUBPROPERTY_OF):
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} rdfs:subPropertyOf {self._props[PropertyClassProp.SUBPROPERTY_OF]}'
        if self._props.get(PropertyClassProp.EXCLUSIVE_FOR):
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} rdfs:domain {self._props[PropertyClassProp.EXCLUSIVE_FOR]}'
        if self._props.get(PropertyClassProp.PROPERTY_TYPE) == OwlPropertyType.OwlDataProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} rdfs:range {self._props[PropertyClassProp.DATATYPE].value}'
        elif self._props.get(PropertyClassProp.PROPERTY_TYPE) == OwlPropertyType.OwlObjectProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} rdfs:range {self._props[PropertyClassProp.TO_NODE_IRI]}'
        sparql += ' .\n'
        return sparql

    def create_owl_part2(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent * indent_inc}}[\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}rdf:type owl:Restriction ;\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}owl:onProperty {self._property_class_iri}'
        sparql += self._restrictions.create_owl(indent + 1, indent_inc)
        if self._props[PropertyClassProp.PROPERTY_TYPE] == OwlPropertyType.OwlDataProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:onDataRange {self._props[PropertyClassProp.DATATYPE].value}'
        elif self._props[PropertyClassProp.PROPERTY_TYPE] == OwlPropertyType.OwlObjectProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:onClass {self._props[PropertyClassProp.TO_NODE_IRI]}'
        sparql += f' ;\n{blank:{indent * indent_inc}}]'
        return sparql

    def create(self, indent: int = 0, indent_inc: int = 4, as_string: bool = False):
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:shacl {{\n'
        sparql += self.__create_shacl(indent=2)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:onto {{\n'
        sparql += self.__create_owl(indent=2)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}}}\n'
        if as_string:
            return sparql
        else:
            self._con.update_query(sparql)

    def __update_shacl(self, *,
                       owlclass_iri: Optional[QName] = None,
                       indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql_list = []
        for prop, change in self._changeset.items():
            sparql = f'#\n# Process "{prop.value}" with Action "{change.action.value}"\n#\n'
            if change.action == Action.MODIFY:
                if PropertyClass.__datatypes[prop] == {LangString}:
                    sparql += self._props[prop].update_shacl(owlclass_iri=owlclass_iri,
                                                             prop_iri=self._property_class_iri,
                                                             prop=prop,
                                                             indent=indent, indent_inc=indent_inc)
                elif PropertyClass.__datatypes[prop] == {PropertyRestrictions}:
                    sparql += self._props[prop].update_shacl(owlclass_iri=owlclass_iri,
                                                             prop_iri=self._property_class_iri,
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
                sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {prop.value} {self._props[prop]} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'

            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._property_class_iri.prefix}:shacl {{\n'
            if owlclass_iri:
                sparql += f'{blank:{(indent + 2) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}?prop sh:path {self._property_class_iri} .\n'
            else:
                sparql += f'{blank:{(indent + 2) * indent_inc}}BIND({self._property_class_iri}Shape as ?prop)\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {prop.value} ?rval\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)

        sparql = ";\n".join(sparql_list)
        return sparql

    def __update_owl(self) -> str:
        blank = ''
        return blank

    def update(self) -> None:
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += self.__update_shacl()
        self._con.update_query(sparql)
        self.__changeset_clear()

    def delete_shacl(self, indent: int = 0, indent_inc: int = 4) -> None:
        pass


if __name__ == '__main__':
    con = Connection('http://localhost:7200', 'omas')
    pclass1 = PropertyClass(con=con, property_class_iri=QName('omas:comment'))
    pclass1.read()
    print(pclass1)

    pclass2 = PropertyClass(con=con, property_class_iri=QName('omas:test'))
    pclass2.read()
    print(pclass2)
