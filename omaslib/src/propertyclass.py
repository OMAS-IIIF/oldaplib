import re
from enum import Enum
from typing import Union, Set, Optional, Any, Tuple, Dict

from pystrict import strict

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import QName, AnyIRI, Languages
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes, XsdValidator
from omaslib.src.model import Model


class OwlPropertyType(Enum):
    OwlDataProperty = 'owl:DatatypeProperty'
    OwlObjectProperty = 'owl:ObjectProperty'

class PropertyRestrictionType(Enum):
    LANGUAGE_IN = 'sh:languageIn'
    UNIQUE_LANG = 'sh:uniqueLang'
    MIN_LENGTH = 'sh:minLength'
    MAX_LENGTH = 'sh:maxLength'
    PATTERN = 'sh:pattern'
    MIN_EXCLUSIVE = 'sh:minExclusive'
    MIN_INCLUSIVE = 'sh:minInclusive'
    MAX_EXCLUSIVE = 'sh:maxExcluisive'
    MAX_INCLUSIVE = 'sh:maxInclusive'
    LESS_THAN = 'sh:lessThan'
    LESS_THAN_OR_EQUALS = 'sh:lessThanOrEquals'

@strict
class PropertyRestrictions:
    _restrictions: Dict[PropertyRestrictionType, Union[int, float, str, Set[Languages], QName]]

    def __init__(self, *,
                 language_in: Optional[Set[Languages]] = None,
                 unique_lang: Optional[bool] = None,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None,
                 pattern: Optional[str] = None,
                 min_exclusive: Optional[Union[int, float]] = None,
                 min_inclusive: Optional[Union[int, float]] = None,
                 max_exclusive: Optional[Union[int, float]] = None,
                 max_inclusive: Optional[Union[int, float]] = None,
                 less_than: Optional[QName] = None,
                 less_than_or_equals: Optional[QName] = None):
        self._restrictions = {}
        if language_in:
            if type(language_in) != set:
                raise OmasError(f'Invalid value "{language_in}" for sh:languageIn restriction!')
            self._restrictions[PropertyRestrictionType.LANGUAGE_IN] = language_in
        if unique_lang:
            if type(unique_lang) != bool:
                raise OmasError(f'Invalid value "{unique_lang}" for sh:uniqueLang restriction!')
            self._restrictions[PropertyRestrictionType.UNIQUE_LANG] = unique_lang
        if min_length:
            if not XsdValidator.validate(XsdDatatypes.integer, min_length):
                raise OmasError(f'Invalid value "{min_length}" for sh:minLength restriction!')
            self._restrictions[PropertyRestrictionType.MIN_LENGTH] = min_length
        if max_length:
            if not XsdValidator.validate(XsdDatatypes.integer, max_length):
                raise OmasError(f'Invalid value "{max_length}" for sh:maxLength restriction!')
            self._restrictions[PropertyRestrictionType.MAX_LENGTH] = max_length
        if pattern:
            try:
                re.compile(pattern)
            except re.error as err:
                raise OmasError(f'Invalid value "{pattern}" for sh:pattern restriction. Message: {err.msg}')
            self._restrictions[PropertyRestrictionType.PATTERN] = pattern
        if min_exclusive:
            if not hasattr(min_exclusive, '__gt__'):
                raise OmasError(f'Invalid value "{min_exclusive}" for sh:minExclusive: No compare function defined!')
            self._restrictions[PropertyRestrictionType.MIN_EXCLUSIVE] = min_exclusive
        if min_inclusive:
            if not hasattr(min_inclusive, '__ge__'):
                raise OmasError(f'Invalid value "{min_inclusive}" for sh:minInlcusive: No compare function defined!')
            self._restrictions[PropertyRestrictionType.MIN_INCLUSIVE] = min_inclusive
        if max_exclusive:
            if not hasattr(max_exclusive, '__lt__'):
                raise OmasError(f'Invalid value "{max_exclusive}" for sh:maxExclusive: No compare function defined!')
            self._restrictions[PropertyRestrictionType.MAX_EXCLUSIVE] = max_exclusive
        if max_inclusive:
            if not hasattr(max_inclusive, '__le__'):
                raise OmasError(f'Invalid value "{max_inclusive}" for sh:maxInclusive: No compare function defined!')
            self._restrictions[PropertyRestrictionType.MAX_INCLUSIVE] = max_inclusive
        if less_than:
            if type(less_than) != QName:
                raise OmasError(f'Invalid value "{less_than}" for sh:lessThan: Not a QName!')
            self._restrictions[PropertyRestrictionType.LESS_THAN] = less_than
        if less_than_or_equals:
            if type(less_than_or_equals) != QName:
                raise OmasError(f'Invalid value "{less_than}" for sh:lessThanOrEquals: Not a QName!')
            self._restrictions[PropertyRestrictionType.LESS_THAN_OR_EQUALS] = less_than_or_equals


    def __str__(self) -> str:
        if len(self._restrictions) == 0:
            return ''
        rstr = ' Restrictions: ['
        for name, value in self._restrictions.items():
            if name == PropertyRestrictionType.LANGUAGE_IN:
                rstr += f'{name.value} ( '
                for lang in value:
                    rstr += f' "{lang.value}"'
                rstr += ' )'
            else:
                rstr += f' {name.value}: {value}'
        rstr += ' ]'
        return rstr

    def __len__(self) -> int:
        return len(self._restrictions)

    def __getattr__(self, restriction_type: PropertyRestrictionType) -> Union[int, float, str, Set[Languages], QName]:
        return self._restrictions[restriction_type]


    def __setattr__(self,
            restriction_type: PropertyRestrictionType,
            value: Union[int, float, str, Set[Languages], QName]) -> None:
        if restriction_type == PropertyRestrictionType.LANGUAGE_IN:
            if type(value) != set:
                raise OmasError(f'Invalid value "{value}" for sh:languageIn restriction!')
            if self._restrictions.get(PropertyRestrictionType.LANGUAGE_IN) is None:
                self._restrictions[PropertyRestrictionType.LANGUAGE_IN] = set()
            self._restrictions[PropertyRestrictionType.LANGUAGE_IN] |= value
        elif restriction_type == PropertyRestrictionType.UNIQUE_LANG:
            if type(value) != bool:
                raise OmasError(f'Invalid value "{value}" for sh:uniqueLang restriction!')
            self._restrictions[restriction_type] = value
        elif restriction_type == PropertyRestrictionType.MIN_LENGTH:
            if not XsdValidator.validate(XsdDatatypes.integer, value):
                raise OmasError(f'Invalid value "{value}" for sh:minLength restriction!')
            self._restrictions[restriction_type] = value
        elif restriction_type == PropertyRestrictionType.MAX_LENGTH:
            if not XsdValidator.validate(XsdDatatypes.integer, value):
                raise OmasError(f'Invalid value "{value}" for sh:maxLength restriction!')
            self._restrictions[restriction_type] = value
        elif restriction_type == PropertyRestrictionType.PATTERN:
            try:
                re.compile(value)
            except re.error as err:
                raise OmasError(f'Invalid value "{value}" for sh:pattern restriction. Message: {err.msg}')
            self._restrictions[restriction_type] = value
        elif restriction_type == PropertyRestrictionType.MIN_EXCLUSIVE:
            if not hasattr(value, '__gt__'):
                raise OmasError(f'Invalid value "{value}" for sh:minExclusive: No compare function defined!')
            self._restrictions[restriction_type] = value
        elif restriction_type == PropertyRestrictionType.MIN_INCLUSIVE:
            if not hasattr(value, '__ge__'):
                raise OmasError(f'Invalid value "{value}" for sh:minInlcusive: No compare function defined!')
            self._restrictions[restriction_type] = value
        elif restriction_type == PropertyRestrictionType.MAX_EXCLUSIVE:
            if not hasattr(value, '__lt__'):
                raise OmasError(f'Invalid value "{value}" for sh:maxExclusive: No compare function defined!')
            self._restrictions[restriction_type] = value
        elif restriction_type == PropertyRestrictionType.MAX_INCLUSIVE:
            if not hasattr(value, '__le__'):
                raise OmasError(f'Invalid value "{value}" for sh:maxInclusive: No compare function defined!')
            self._restrictions[restriction_type] = value
        elif restriction_type == PropertyRestrictionType.LESS_THAN:
            if type(value) != QName:
                raise OmasError(f'Invalid value "{value}" for sh:lessThan: Not a QName!')
            self._restrictions[restriction_type] = value
        elif restriction_type == PropertyRestrictionType.LESS_THAN_OR_EQUALS:
            if type(value) != QName:
                raise OmasError(f'Invalid value "{value}" for sh:lessThanOrEquals: Not a QName!')
            self._restrictions[restriction_type] = value

    def __delattr__(self, restriction_type: PropertyRestrictionType):
        del self._restrictions[restriction_type]

    def remove(self,
               restriction_type: PropertyRestrictionType,
               langs: Optional[Set[str]] = None) -> None:
        if self._restrictions.get(restriction_type) is None:
            return
        if restriction_type == PropertyRestrictionType.LANGUAGE_IN and langs is not None:
            self._restrictions[PropertyRestrictionType.LANGUAGE_IN] -= langs
        else:
            del self._restrictions[restriction_type]

    def shacl(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        shacl = ''
        for name, rval in self._restrictions.items():
            if name == PropertyRestrictionType.LANGUAGE_IN:
                tmp = [f'"{x.value}"' for x in rval]
                value = '(' + ' '.join(tmp) + ')'
            elif name == PropertyRestrictionType.UNIQUE_LANG:
                value = 'true' if rval else 'false'
            else:
                value = rval
            shacl += f'{blank:{indent*indent_inc}}{name.value} {value} ;\n'
        return shacl



@strict
class PropertyClass(Model):
    _property_class_iri: Union[QName, None]
    _subproperty_of: Union[QName, None]
    _property_type: Union[OwlPropertyType, None]
    _exclusive_for_class: Union[QName, None]
    _required: Union[bool, None]
    _multiple: Union[bool, None]
    _to_node_iri: Union[AnyIRI, None]
    _datatype: Union[XsdDatatypes, None]
    _restrictions: Union[PropertyRestrictions, None]
    _name: Union[str, None]
    _description: Union[str, None]
    _order: int

    def __init__(self,
                 con: Connection,
                 property_class_iri: Optional[QName] = None,
                 subproperty_of: Optional[QName] = None,
                 exclusive_for_class: Optional[QName] = None,
                 datatype: Optional[XsdDatatypes] = None,
                 to_node_iri: Optional[AnyIRI] = None,
                 required: Optional[bool] = None,
                 multiple: Optional[bool] = None,
                 restrictions: Optional[PropertyRestrictions] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 order: Optional[int] = None):
        super().__init__(con)
        if not XsdValidator.validate(XsdDatatypes.QName, property_class_iri):
            raise OmasError("Invalid format of property IRI")
        self._property_class_iri = property_class_iri
        self._subproperty_of = subproperty_of
        self._exclusive_for_class = exclusive_for_class
        self._datatype = datatype
        self._to_node_iri = to_node_iri
        self._required = required
        self._multiple = multiple
        self._restrictions = restrictions
        self._name = name
        self._description = description
        self._order = order
        if self._datatype:
            self._property_type = OwlPropertyType.OwlDataProperty
        elif self._to_node_iri:
            self._property_type = OwlPropertyType.OwlObjectProperty
        else:
            self._property_type = None

    def __str__(self):
        required = '✅' if self._required else '❌'
        multiple = '✅' if self._multiple else '❌'
        propstr = f'Property: {str(self._property_class_iri)};'
        if self._subproperty_of:
            propstr += f' Subproperty of {self._subproperty_of};'
        if self._exclusive_for_class:
            propstr += f' Exclusive for {self._exclusive_for_class};'
        if self._to_node_iri:
            propstr += f' Datatype: => {self._to_node_iri});'
        else:
            propstr += f' Datatype: {self._datatype.value};'
        propstr += f' Required: {required} Multiple: {multiple};'
        if len(self._restrictions) > 0:
            propstr += f'{self._restrictions};'
        if self._name:
            propstr += f' Name: {self._name}'
        if self._description:
            propstr += f' Description: {self._description}'
        if self._order:
            propstr += f' Order: {self._order}'
        return propstr

    @property
    def property_class_iri(self) -> QName:
        return self._property_class_iri

    @property_class_iri.setter
    def property_class_iri(self, value: Any):
        OmasError(f'property_class_iri_class cannot be set!')

    @property
    def required(self):
        return self._required

    @required.setter
    def required(self, value: bool):
        self._required = value

    @property
    def multiple(self):
        return self._multiple

    @multiple.setter
    def multiple(self, value: bool):
        self._multiple = value

    def get_restriction(self, restriction_type: PropertyRestrictionType) -> Union[int, float, str, Set[Languages], QName]:

    @property
    def languages(self) -> Set[Languages]:
        return self._languages

    def add_language(self, lang: Languages) -> None:
        self._languages.add(lang)

    def remove_language(self, lang: Languages) -> None:
        self._languages.discard(lang)

    def valid_language(self, lang: Languages) -> bool:
        return lang in self._languages

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

    def create_shacl(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent*indent_inc}}[\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}sh:path {str(self._property_class_iri)} ;\n'
        if self._datatype:
            sparql += f'{blank:{(indent + 1)*indent_inc}}sh:datatype {self._datatype.value} ;\n'
        if self._required:
            sparql += f'{blank:{(indent + 1)*indent_inc}}sh:minCount 1 ;\n'
        if not self._multiple:
            sparql += f'{blank:{(indent + 1)*indent_inc}}sh:maxCount 1 ;\n'
        if self._restrictions:
            sparql += self._restrictions.shacl(indent + 1, indent_inc)
        if self._to_node_iri:
            sparql += f'{blank:{(indent + 1)*indent_inc}}sh:class {str(self._to_node_iri)} ;\n'
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
        if self._required:
            sparql += f' ;\n{blank:{(indent + 1)*indent_inc}}owl:minQualifiedCardinality "1"^^xsd:nonNegativeInteger'
        if not self._multiple:
            sparql += f' ;\n{blank:{(indent + 1)*indent_inc}}owl:maxQualifiedCardinality "1"^^xsd:nonNegativeInteger'
        if self._property_type == OwlPropertyType.OwlDataProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:onDataRange {self._datatype.value}'
        elif self._property_type == OwlPropertyType.OwlObjectProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:onClass {self._to_node_iri}'
        sparql += f' ;\n{blank:{indent * indent_inc}}]'
        return sparql
