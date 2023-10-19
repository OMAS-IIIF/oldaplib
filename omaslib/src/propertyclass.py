"""
:Author: Lukas Rosenthaler <lukas.rosenthaler@unibas.ch>
"""
from enum import Enum, unique
from typing import Union, Set, Optional, Any, List, Tuple, Dict

from pystrict import strict
from rdflib import URIRef, Literal, BNode

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import QName, AnyIRI, Action
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.propertyclass_singleton import PropertyClassSingleton
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes, XsdValidator
from omaslib.src.model import Model
from omaslib.src.propertyrestriction import PropertyRestrictionType, PropertyRestrictions


@unique
class OwlPropertyType(Enum):
    OwlDataProperty = 'owl:DatatypeProperty'
    OwlObjectProperty = 'owl:ObjectProperty'

@unique
class PropertyClassProp(Enum):
    SUBPROPERTY_OF = 'rdfs:subPropertyOf'
    PROPERTY_TYPE = 'rdf:type'
    EXCLUSIVE_FOR = 'omas:exclusive'
    TO_NODE_IRI = 'sh:class'
    DATATYPE = 'sh:datatype'
    RESTRICTIONS = 'omas:restrictions'
    NAME = 'sh:name'
    DESCRIPTION = 'sh:description'
    ORDER = 'sh:order'


PropTypes = Union[QName, OwlPropertyType, XsdDatatypes, PropertyRestrictions, LangString, int]
PropertyClassPropsContainer = Dict[PropertyClassProp, PropTypes]


@strict
class PropertyClass(Model, metaclass=PropertyClassSingleton):
    """
    This class implements the SHACL/OWL property definition that OMAS supports

    The class implements the *__str__* method.
    """
    _property_class_iri: Union[QName, None]
    _props: PropertyClassPropsContainer

    _changeset: Set[Tuple[PropertyClassProp, Action]]
    _test_in_use: bool

    __datatypes: Dict[PropertyClassProp, PropTypes] = {
        PropertyClassProp.SUBPROPERTY_OF: QName,
        PropertyClassProp.PROPERTY_TYPE: OwlPropertyType,
        PropertyClassProp.EXCLUSIVE_FOR: QName,
        PropertyClassProp.TO_NODE_IRI: QName,
        PropertyClassProp.DATATYPE: XsdDatatypes,
        PropertyClassProp.RESTRICTIONS: PropertyRestrictions,
        PropertyClassProp.NAME: LangString,
        PropertyClassProp.DESCRIPTION: LangString,
        PropertyClassProp.ORDER: int
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
                if type(prop) != PropertyClassProp:
                    raise OmasError(
                        f'Unsupported Property prop "{prop}"'
                    )
                if type(value) not in PropertyClass.__datatypes[prop]:
                    raise OmasError(
                        f'Datatype of prop "{prop.value}": "{type(value)}" ({value}) is not valid'
                    )
            self._props = props

        # setting property type for OWL which distinguished between Data- and Object-^properties
        if self._props.get(PropertyClassProp.TO_NODE_IRI) is not None:
            self._property_type = OwlPropertyType.OwlObjectProperty
            dt = self._props.get(PropertyClassProp.DATATYPE)
            if dt and (dt != XsdDatatypes.anyURI or dt != XsdDatatypes.QName):
                raise OmasError(f'Datatype "{dt}" not valid for OwlObjectProperty')
        else:
            self._props[PropertyClassProp.PROPERTY_TYPE] = OwlPropertyType.OwlDataProperty
        self._changeset = set()  # initialize changeset to empty set
        self._test_in_use = False

    def __str__(self):
        propstr = f'Property: {str(self._property_class_iri)};'
        for prop, value in self._props.items():
            propstr += f' {prop.value}: {value};'
        return propstr

    def __getitem__(self, prop: PropertyClassProp) -> PropTypes:
        return self._props[prop]


    def get(self, prop: PropertyClassProp) ->Union[PropTypes, None]:
        return self.get(prop)

    def __setitem__(self, prop: PropertyClassProp, value: PropTypes) -> None:
        if type(prop) != PropertyClassProp:
            raise OmasError(f'Unsupported prop {prop}')
        if type(value) != PropertyClass.__datatypes[prop]:
            raise OmasError(f'Datatype of {prop.value} is not {PropertyClass.__datatypes[prop]}')
        if self._props.get(prop) is None:
            self._props[prop] = value
            self._changeset.add((prop, Action.CREATE))
        else:
            if self._props.get(prop) != value:
                self._props[prop] = value
                self._changeset.add((prop, Action.REPLACE))

    def __delitem__(self, prop: PropertyClassProp):
        if self._props.get(prop) is not None:
            del self._props[prop]
            self._changeset.add((prop, Action.DELETE))

    @property
    def property_class_iri(self) -> QName:
        return self._property_class_iri

    @property_class_iri.setter
    def property_class_iri(self, value: Any):
        OmasError(f'property_class_iri_class cannot be set!')


    @property
    def changeset(self) -> set[tuple[str, Action]]:
        return self._changeset

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

        self._restrictions = PropertyRestrictions()
        for key, val in properties.items():
            if key == 'rdf:type':
                if val[0] == 'sh:PropertyShape':
                    continue
                else:
                    raise OmasError(f'Inconsistency, expected "sh:PropertyType", got "{val[0]}".')
            elif key == 'sh:path':
                self._property_class_iri = val[0]
            elif key == 'sh:datatype':
                self._datatype = XsdDatatypes(str(val[0]))
            elif key == 'sh:class':
                self._to_node_iri = val[0]
            elif key == QName('sh:name'):
                self._name = LangString()
                for ll in val:
                    self._name.add(ll)
            elif key == 'sh:description':
                self._description = LangString()
                for ll in val:
                    self._description.add(ll)
            elif key == "sh:order":
                self._order = val[0]
            else:
                try:
                    self._restrictions[PropertyRestrictionType(key)] = val if key == "sh:languageIn" else val[0]
                except (ValueError, TypeError) as err:
                    OmasError(f'Invalid shacl definition: "{key} {val}"')

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
                    self._property_type = OwlPropertyType.OwlDataProperty
                elif str(obj) == 'owl:ObjectProperty':
                    self._property_type = OwlPropertyType.OwlObjectProperty
            elif prop == 'owl:subPropertyOf':
                self._subproperty_of = obj
            elif prop == 'rdfs:range':
                if obj.prefix == 'xsd':
                    datatype = obj
                else:
                    to_node_iri = obj
            elif prop == 'rdfs:domain':
                self._exclusive_for_class = obj
        # Consistency checks
        if self._property_type == OwlPropertyType.OwlDataProperty and not self._datatype:
            OmasError(f'OwlDataProperty "{self._property_class_iri}" has no rdfs:range datatype defined!')
        if self._property_type == OwlPropertyType.OwlObjectProperty and not to_node_iri:
            OmasError(f'OwlObjectProperty "{self._property_class_iri}" has no rdfs:range resource class defined!')
        if self._property_type == OwlPropertyType.OwlObjectProperty:
            if to_node_iri != self._to_node_iri:
                OmasError(f'Property has inconstent object type definition: OWL: {to_node_iri} vs SHACL: {self._to_node_iri}.')

    def read(self):
        self.__read_shacl()
        self.__read_owl()

    def property_node(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{(indent + 1)*indent_inc}}sh:path {self._property_class_iri}'
        if self._datatype:
            sparql += f' ;\n{blank:{(indent + 1)*indent_inc}}sh:datatype {self._datatype.value}'
        if self._restrictions:
            sparql += self._restrictions.create_shacl(indent + 1, indent_inc)
        if self._to_node_iri:
            sparql += f' ;\n{blank:{(indent + 1)*indent_inc}}sh:class {self._to_node_iri}'
        if self._name:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}sh:name {self._name}'
        if self._description:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}sh:description {self._description}'
        if self._order:
            sparql += f' ;\n{blank:{(indent + 1)*indent_inc}}sh:order {self._order}'
        return sparql


    def create_owl_part1(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent*indent_inc}}{self._property_class_iri} rdf:type {self._property_type.value}'
        if self._subproperty_of:
            sparql += f' ;\n{blank:{(indent + 1)*indent_inc}} rdfs:subPropertyOf {self._subproperty_of}'
        if self._exclusive_for_class:
            sparql += f' ;\n{blank:{(indent + 1)*indent_inc}} rdfs:domain {self._exclusive_for_class}'
        if self._property_type == OwlPropertyType.OwlDataProperty:
            sparql += f' ;\n{blank:{(indent + 1)*indent_inc}} rdfs:range {self._datatype.value}'
        elif self._property_type == OwlPropertyType.OwlObjectProperty:
            sparql += f' ;\n{blank:{(indent + 1)*indent_inc}} rdfs:range {self._to_node_iri}'
        sparql += ' .\n'
        return sparql

    def create_shacl(self, indent: int = 0, indent_inc: int = 4, as_string: bool = False) -> Union[str, None]:
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent*indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._property_class_iri.prefix}:shacl {{\n'

        sparql += f'{blank:{(indent + 2)*indent_inc}}{self._property_class_iri}Shape a sh:PropertyShape ;\n'
        sparql += self.property_node(indent + 3, indent_inc)

        sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
        sparql += f'{blank:{indent*indent_inc}}}}\n'
        if as_string:
            return sparql
        else:
            #print(sparql)
            self._con.update_query(sparql)


    def create_owl_part2(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent*indent_inc}}[\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}rdf:type owl:Restriction ;\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}owl:onProperty {self._property_class_iri}'
        sparql += self._restrictions.create_owl(indent + 1, indent_inc)
        if self._property_type == OwlPropertyType.OwlDataProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:onDataRange {self._datatype.value}'
        elif self._property_type == OwlPropertyType.OwlObjectProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:onClass {self._to_node_iri}'
        sparql += f' ;\n{blank:{indent * indent_inc}}]'
        return sparql

    def update_shacl(self,
                     indent: int = 0, indent_inc: int = 4):
        blank = ''
        sparql_insert = ''
        sparql_delete = ''
        sparql_where = ''
        for change in self._changeset:
            if change[1] == Action.DELETE:
                pass
            elif change[1] == Action.CREATE:
                sparql_insert += f'{blank:{indent*indent_inc}}INSERT {{\n'
                sparql_insert += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._property_class_iri}:shacl {{\n'
                sparql_insert += f'{blank:{(indent + 2)*indent_inc}}{change[0]} '
                sparql_insert += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql_insert += f'{blank:{indent * indent_inc}}}}\n'
                pass
            elif change[2] == Action.REPLACE:
                pass
            elif change[2] == Action.EXTEND:  # TODO: May be unused....
                pass

    def delete_shacl(self, indent: int = 0, indent_inc: int = 4) -> None:
        pass

    def read(self) -> None:
        self.__read_shacl()
        self.__read_owl()


if __name__ == '__main__':
    con = Connection('http://localhost:7200', 'omas')
    pclass1 = PropertyClass(con=con, property_class_iri=QName('omas:comment'))
    pclass1.read()
    print(pclass1)

    pclass2 = PropertyClass(con=con, property_class_iri=QName('omas:test'))
    pclass2.read()
    print(pclass2)

