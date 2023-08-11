"""
:Author: Lukas Rosenthaler <lukas.rosenthaler@unibas.ch>
"""
from enum import Enum
from typing import Union, Set, Optional, Any, List

from pystrict import strict

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import QName, AnyIRI
from omaslib.src.helpers.langstring import Languages, LangString
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.propertyclass_singleton import PropertyClassSingleton
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes, XsdValidator
from omaslib.src.model import Model
from omaslib.src.propertyrestriction import PropertyRestrictionType, PropertyRestrictions


class OwlPropertyType(Enum):
    OwlDataProperty = 'owl:DatatypeProperty'
    OwlObjectProperty = 'owl:ObjectProperty'


@strict
class PropertyClass(Model, metaclass=PropertyClassSingleton):
    _property_class_iri: Union[QName, None]
    _subproperty_of: Union[QName, None]
    _property_type: Union[OwlPropertyType, None]
    _exclusive_for_class: Union[QName, None]
    _to_node_iri: Union[AnyIRI, None]
    _datatype: Union[XsdDatatypes, None]
    _restrictions: Union[PropertyRestrictions, None]
    _name: Union[LangString, None]
    _description: Union[LangString, None]
    _order: int

    _changeset: Set[str]
    _test_in_use: bool

    def __init__(self,
                 con: Connection,
                 property_class_iri: Optional[QName] = None,
                 subproperty_of: Optional[QName] = None,
                 exclusive_for_class: Optional[QName] = None,
                 datatype: Optional[XsdDatatypes] = None,
                 to_node_iri: Optional[AnyIRI] = None,
                 restrictions: Optional[PropertyRestrictions] = None,
                 name: Optional[LangString] = None,
                 description: Optional[LangString] = None,
                 order: Optional[int] = None):
        super().__init__(con)
        if not XsdValidator.validate(XsdDatatypes.QName, property_class_iri):
            raise OmasError("Invalid format of property IRI")
        self._property_class_iri = property_class_iri
        self._subproperty_of = subproperty_of
        self._exclusive_for_class = exclusive_for_class
        self._datatype = datatype
        self._to_node_iri = to_node_iri
        self._restrictions = restrictions
        if name is not None and not isinstance(name, LangString):
            raise OmasError(f'Parameter "name" must be a "LangString", but is "{type(name)}"!')
        self._name = name
        if description is not None and not isinstance(description, LangString):
            raise OmasError(f'Parameter "description" must be a "LangString", but is "{type(description)}"!')
        self._description = description
        self._order = order
        if self._datatype:
            self._property_type = OwlPropertyType.OwlDataProperty
        elif self._to_node_iri:
            self._property_type = OwlPropertyType.OwlObjectProperty
        else:
            self._property_type = None
        self._changeset = set()
        self._test_in_use = False

    def __str__(self):
        propstr = f'Property: {str(self._property_class_iri)};'
        if self._subproperty_of:
            propstr += f' Subproperty of {self._subproperty_of};'
        if self._exclusive_for_class:
            propstr += f' Exclusive for {self._exclusive_for_class};'
        if self._to_node_iri:
            propstr += f' Datatype: => {self._to_node_iri});'
        else:
            propstr += f' Datatype: {self._datatype.value};'
        if len(self._restrictions) > 0:
            propstr += f'{self._restrictions};'
        if self._name:
            propstr += f' Name: {self._name};'
        if self._description:
            propstr += f' Description: {self._description};'
        if self._order:
            propstr += f' Order: {self._order};'
        return propstr

    @property
    def property_class_iri(self) -> QName:
        return self._property_class_iri

    @property_class_iri.setter
    def property_class_iri(self, value: Any):
        OmasError(f'property_class_iri_class cannot be set!')

    @property
    def name(self) -> LangString:
        return self._name

    @name.setter
    def name(self, name: LangString) -> None:
        if name != self._name:
            self._changeset.add('name')
            if self._name:
                self._name.add(name.langstring)
            else:
                self._name = name

    def name_add(self, lang: Languages, name: str):
        if self._name:
            if self._name.langstring.get(lang) != name:
                self._name[lang] = name
                self._changeset.add('name')
        else:
            self._name = LangString({lang: name})
            self._changeset.add('name')

    @property
    def description(self) -> LangString:
        return self._description

    @description.setter
    def description(self, description: LangString) -> None:
        if description != self._description:
            self._changeset.add('description')
            if self._description:
                self._description.add(description.langstring)
            else:
                self._description = description

    def description_add(self, lang: Languages, description: str):
        if self._description:
            if self._description.langstring.get(lang) != description:
                self._description[lang] = description
                self._changeset.add('description')
        else:
            self._description = LangString({lang: description})
            self._changeset.add('description')

    def get_restriction(self, restriction_type: PropertyRestrictionType) -> Union[int, float, str, Set[Languages], QName]:
        return self._restrictions[restriction_type]

    def add_restriction(self,
                        restriction_type: PropertyRestrictionType,
                        value: Union[int, float, str, Set[Languages], QName]):
        self._restrictions[restriction_type] = value
        self._changeset.add('restrictions')
        self._test_in_use = True

    def clear_restrictions(self):
        self._restrictions.clear()
        self._changeset.add('restrictions')

    def set_new(self):
        self._changeset.add("new")

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

    def read_owl(self):
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
        print(self._property_class_iri)
        datatype = None
        to_node_iri = None
        obj_prop = False
        for r in res:
            pstr = str(context.iri2qname(r[0]))
            if pstr == 'owl:DatatypeProperty':
                self._property_type = OwlPropertyType.OwlDataProperty
            elif pstr == 'owl:ObjectProperty':
                self._property_type = OwlPropertyType.OwlObjectProperty
            elif pstr == 'owl:subPropertyOf':
                self._subproperty_of = r[1]
            elif pstr == 'rdfs:range':
                o = context.iri2qname(r[1])
                if o.prefix == 'xsd':
                    datatype = o
                else:
                    to_node_iri = o
            elif pstr == 'rdfs:domain':
                o = context.iri2qname(r[1])
                self._exclusive_for_class = o
        # Consistency checks
        if self._property_type == OwlPropertyType.OwlDataProperty and not self._datatype:
            OmasError(f'OwlDataProperty "{self._property_class_iri}" has no rdfs:range datatype defined!')
        if self._property_type == OwlPropertyType.OwlObjectProperty and not to_node_iri:
            OmasError(f'OwlObjectProperty "{self._property_class_iri}" has no rdfs:range resource class defined!')
        if self._property_type == OwlPropertyType.OwlObjectProperty:
            if to_node_iri != self._to_node_iri:
                OmasError(f'Property has inconstent object type definition: OWL: {to_node_iri} vs SHACL: {self._to_node_iri}.')

    def property_node(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent*indent_inc}}[\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}sh:path {self._property_class_iri} ;\n'
        if self._datatype:
            sparql += f'{blank:{(indent + 1)*indent_inc}}sh:datatype {self._datatype.value} ;\n'
        if self._restrictions:
            sparql += self._restrictions.create_shacl(indent + 1, indent_inc)
        if self._to_node_iri:
            sparql += f'{blank:{(indent + 1)*indent_inc}}sh:class {self._to_node_iri} ;\n'
        if self._name:
            sparql += f'{blank:{(indent + 1) * indent_inc}}sh:name "{self._name}" ;\n'
        if self._description:
            sparql += f'{blank:{(indent + 1) * indent_inc}}sh:description "{self._description}" ;\n'
        if self._order:
            sparql += f'{blank:{(indent + 1)*indent_inc}}sh:order {self._order} ;\n'
        sparql += f'{blank:{indent*indent_inc}}] ; \n'
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
                     owl_class: QName,
                     indent: int = 0, indent_inc: int = 4):
        blank = ''
        sparql_list: List[str] = []

    def delete_shacl(self, indent: int = 0, indent_inc: int = 4) -> None:
        pass


