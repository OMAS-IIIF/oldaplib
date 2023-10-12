import re
from enum import Enum, unique
from typing import Dict, Union, Set, Optional, Tuple

from pystrict import strict

from omaslib.src.helpers.datatypes import QName, Action
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.xsd_datatypes import XsdValidator, XsdDatatypes

@unique
class PropertyRestrictionType(Enum):
    MIN_COUNT = 'sh:minCount'
    MAX_COUNT = 'sh:maxCount'
    LANGUAGE_IN = 'sh:languageIn'
    UNIQUE_LANG = 'sh:uniqueLang'
    MIN_LENGTH = 'sh:minLength'
    MAX_LENGTH = 'sh:maxLength'
    PATTERN = 'sh:pattern'
    MIN_EXCLUSIVE = 'sh:minExclusive'
    MIN_INCLUSIVE = 'sh:minInclusive'
    MAX_EXCLUSIVE = 'sh:maxExclusive'
    MAX_INCLUSIVE = 'sh:maxInclusive'
    LESS_THAN = 'sh:lessThan'
    LESS_THAN_OR_EQUALS = 'sh:lessThanOrEquals'

@unique
class Compare(Enum):
    LT = '<'
    LE = '<='
    GT = '>'
    GE = '>='
    XX = 'x'

@strict
class PropertyRestrictions:
    """
    This class implements the SHACL/OWL restriction that omaslib supports

    SHACl allows to restrict the tha value range of properties. The following restrictions ate
    supported by *omaslib*.

    * cardinality
        - minCount: in OMAS, 0 or 1 is allowed. If omitted, a minCount of 0 is assumed
        - maxCount: in OMAS, 0 or 1 is allowed. If omitted, any number is allowed
    * for strings:
        - languageIn: A set of languages that are allowed for a string property
        - uniqueLang: if "true", each language may occur only once
        - minLength: Minimal length the string must have
        - maxLength: Maximal length that is allowed for the string
        - pattern: A regex expression that the string must fullfill
    * for values that are comparable with "<", ">", ...:
        - minInclusive: The value must be greater-equal than the given value
        - minExclusive: The value must be greater than the given value
        - maxInclusive: Thevalue must be less-equal than the given value
        - maxExclusive: The value must be less than the given value
    * relative comparisons:
        - lessThan: The value must be less that the value of the given property
        - lessThatOrEquals: The value must be less or equal that the one of teh given property

    The class implements the *Dict* semantics: *__len__*, *__getitem__*, *__setitem__* and *__delitem__*
    are implemented as well as the *__str__* method.

    Other methods:

    * shacl(...): Create a trig-formatted fragment to define the restrictions

    """
    _restrictions: Dict[PropertyRestrictionType, Union[int, float, str, Set[Language], QName]]
    _test_in_use: Set[PropertyRestrictionType]
    _changeset: Set[Tuple[PropertyRestrictionType, Action]]
    _compare: Dict[PropertyRestrictionType, Compare]

    def __init__(self, *,
                 language_in: Optional[Set[Language]] = None,
                 unique_lang: Optional[bool] = None,
                 min_count: Optional[int] = None,
                 max_count: Optional[int] = None,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None,
                 pattern: Optional[str] = None,
                 min_exclusive: Optional[Union[int, float]] = None,
                 min_inclusive: Optional[Union[int, float]] = None,
                 max_exclusive: Optional[Union[int, float]] = None,
                 max_inclusive: Optional[Union[int, float]] = None,
                 less_than: Optional[QName] = None,
                 less_than_or_equals: Optional[QName] = None):
        """
        Constructor for restrictions

        :param language_in: A set of allowed languages
        :param unique_lang: True if each language is alloed only once
        :param min_count: Minimal cardinality for property
        :param max_count: Maximal cardinality for property
        :param min_length: Minimal length of value (if applicable to datatype, e.g. xsd:string)
        :param max_length: Maximal length of value (if applicable to datatype, e.g. xsd:string)
        :param pattern: A regex pattern the value must fulfill
        :param min_exclusive: Minimal value allowed (exclusive)
        :param min_inclusive: Minimal value allowed (inclusive)
        :param max_exclusive: Maximal value allowed (exclusive)
        :param max_inclusive: Maximal value allowed (inclusive)
        :param less_than: Compare to other value (<)
        :param less_than_or_equals: Compare to other value (<=)
        """
        self._compare = {
            PropertyRestrictionType.LANGUAGE_IN: Compare.XX,
            PropertyRestrictionType.UNIQUE_LANG: Compare.XX,
            PropertyRestrictionType.MIN_COUNT: Compare.GT,
            PropertyRestrictionType.MAX_COUNT: Compare.LT,
            PropertyRestrictionType.MIN_LENGTH: Compare.GT,
            PropertyRestrictionType.MAX_LENGTH: Compare.LT,
            PropertyRestrictionType.PATTERN: Compare.XX,
            PropertyRestrictionType.MIN_EXCLUSIVE: Compare.GT,
            PropertyRestrictionType.MIN_INCLUSIVE: Compare.GE,
            PropertyRestrictionType.MAX_EXCLUSIVE: Compare.LT,
            PropertyRestrictionType.MAX_INCLUSIVE: Compare.LE,
            PropertyRestrictionType.LESS_THAN: Compare.XX,
            PropertyRestrictionType.LESS_THAN_OR_EQUALS: Compare.XX
        }
        self._restrictions = {}
        if language_in:
            if type(language_in) != set:
                raise OmasError(f'Invalid value "{language_in}" for sh:languageIn restriction!')
            self._restrictions[PropertyRestrictionType.LANGUAGE_IN] = language_in
        if unique_lang:
            if type(unique_lang) != bool:
                raise OmasError(f'Invalid value "{unique_lang}" for sh:uniqueLang restriction!')
            self._restrictions[PropertyRestrictionType.UNIQUE_LANG] = unique_lang
        if min_count:
            if not XsdValidator.validate(XsdDatatypes.integer, min_count):
                raise OmasError(f'Invalid value "{min_count}" for sh:minCount restriction!')
            self._restrictions[PropertyRestrictionType.MIN_COUNT] = min_count
        if max_count:
            if not XsdValidator.validate(XsdDatatypes.integer, max_count):
                raise OmasError(f'Invalid value "{max_count}" for sh:maxCount restriction!')
            self._restrictions[PropertyRestrictionType.MAX_COUNT] = max_count
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
            # if not hasattr(min_exclusive, '__gt__'):
            #     raise OmasError(f'Invalid value "{min_exclusive}" for sh:minExclusive: No compare function defined!')
            self._restrictions[PropertyRestrictionType.MIN_EXCLUSIVE] = min_exclusive
        if min_inclusive:
            # if not hasattr(min_inclusive, '__ge__'):
            #     raise OmasError(f'Invalid value "{min_inclusive}" for sh:minInlcusive: No compare function defined!')
            self._restrictions[PropertyRestrictionType.MIN_INCLUSIVE] = min_inclusive
        if max_exclusive:
            # if not hasattr(max_exclusive, '__lt__'):
            #     raise OmasError(f'Invalid value "{max_exclusive}" for sh:maxExclusive: No compare function defined!')
            self._restrictions[PropertyRestrictionType.MAX_EXCLUSIVE] = max_exclusive
        if max_inclusive:
            # if not hasattr(max_inclusive, '__le__'):
            #     raise OmasError(f'Invalid value "{max_inclusive}" for sh:maxInclusive: No compare function defined!')
            self._restrictions[PropertyRestrictionType.MAX_INCLUSIVE] = max_inclusive
        if less_than:
            if type(less_than) != QName:
                raise OmasError(f'Invalid value "{less_than}" for sh:lessThan: Not a QName!')
            self._restrictions[PropertyRestrictionType.LESS_THAN] = less_than
        if less_than_or_equals:
            if type(less_than_or_equals) != QName:
                raise OmasError(f'Invalid value "{less_than}" for sh:lessThanOrEquals: Not a QName!')
            self._restrictions[PropertyRestrictionType.LESS_THAN_OR_EQUALS] = less_than_or_equals
        self._test_in_use = set()
        self._changeset = set()

    def __str__(self) -> str:
        if len(self._restrictions) == 0:
            return ''
        rstr = ' Restrictions: ['
        for name, value in self._restrictions.items():
            if name == PropertyRestrictionType.LANGUAGE_IN:
                rstr += f'{name.value} {{'
                for lang in value:
                    rstr += f' "{lang.name.lower()}"'
                rstr += ' }'
            else:
                rstr += f' {name.value}: {value}'
        rstr += ' ]'
        return rstr

    def __len__(self) -> int:
        return len(self._restrictions)

    def __getitem__(self, restriction_type: PropertyRestrictionType) -> Union[int, float, str, Set[Language], QName]:
        return self._restrictions[restriction_type]

    def __setitem__(self,
                    restriction_type: PropertyRestrictionType,
                    value: Union[int, float, str, Set[Language], QName]):
        valid = {int, float, str, Set, QName}
        if type(value) not in valid:
            raise OmasError(f"Invalid type for restriction value")
        if self._restrictions.get(restriction_type):
            if self._compare[restriction_type] == Compare.GT:
                if not hasattr(value, '__gt__'):
                    raise OmasError(f'Invalid value "{value}" for {restriction_type.value}: No compare function defined!')
                if value > self._restrictions[restriction_type]:
                    self._test_in_use.add(restriction_type)
            elif self._compare[restriction_type] == Compare.GE:
                if not hasattr(value, '__ge__'):
                    raise OmasError(f'Invalid value "{value}" for sh:maxExclusive: No compare function defined!')
                if value >= self._restrictions[restriction_type]:
                    self._test_in_use.add(restriction_type)
            elif self._compare[restriction_type] == Compare.LT:
                if not hasattr(value, '__lt__'):
                    raise OmasError(f'Invalid value "{value}" for sh:maxExclusive: No compare function defined!')
                if value < self._restrictions[restriction_type]:
                    self._test_in_use.add(restriction_type)
            elif self._compare[restriction_type] == Compare.LE:
                if not hasattr(value, '__le__'):
                    raise OmasError(f'Invalid value "{value}" for sh:maxExclusive: No compare function defined!')
                if value <= self._restrictions[restriction_type]:
                    self._test_in_use.add(restriction_type)
            else:
                self._test_in_use.add(restriction_type)
            self._changeset.add((restriction_type, Action.REPLACE))
        else:
            self._test_in_use.add(restriction_type)
            self._changeset.add((restriction_type, Action.CREATE))
        self._restrictions[restriction_type] = value

    def __delitem__(self, restriction_type: PropertyRestrictionType):  # TODO: Sparql.....
        if self._restrictions.get(restriction_type) is not None:
            del self._restrictions[restriction_type]
            self._test_in_use.add(restriction_type)
            self._changeset.add((restriction_type, Action.DELETE))

    @property
    def changeset(self) -> Set[Tuple[PropertyRestrictionType, Action]]:
        return self._changeset

    @property
    def test_in_use(self) -> Set[PropertyRestrictionType]:
        return self._test_in_use

    def get(self, restriction_type: PropertyRestrictionType) -> Union[int, float, str, Set[Language], QName, None]:
        """
        Get the given restriction
        :param restriction_type: The restriction type
        :return: Value or None
        """
        return self._restrictions.get(restriction_type)

    def clear(self) -> None:
        """
        Clear all restrictions
        :return: None
        """
        for restriction_type in self._restrictions:
            self._changeset.add(restriction_type, Action.DELETE)
        for restriction_type in self._changeset:
            self._restrictions[restriction_type] = None

    def create_shacl(self, indent: int = 0, indent_inc: int = 4) -> str:
        """
        Return the SHACL fragment for creating the SHACL restrictions

        :param indent: Indent for formatting
        :param indent_inc: Indent increment for formatting
        :return: SHACL fragment string
        """
        blank = ''
        shacl = ''
        for name, rval in self._restrictions.items():
            if name == PropertyRestrictionType.LANGUAGE_IN:
                tmp = [f'"{x.name.lower()}"' for x in rval]
                value = '(' + ' '.join(tmp) + ')'
            elif name == PropertyRestrictionType.UNIQUE_LANG:
                value = 'true' if rval else 'false'
            else:
                value = rval
            shacl += f' ;\n{blank:{indent*indent_inc}}{name.value} {value}'
        return shacl

    def create_owl(self, indent: int = 0, indent_inc: int = 4) -> str:
        """
        Return OWL fragment for creating the ontology of the restrictions
        :param indent: Indent for formatting
        :param indent_inc: Indent increment for formatting
        :return: OWL fragment string
        """
        blank = ''
        sparql = ''
        mincnt = self._restrictions.get(PropertyRestrictionType.MIN_COUNT)
        maxcnt = self._restrictions.get(PropertyRestrictionType.MAX_COUNT)
        if mincnt is not None and maxcnt is not None and mincnt == maxcnt:
            sparql += f' ;\n{blank:{indent*indent_inc}}owl:cardinality {mincnt}'
        else:
            if mincnt is not None:
                sparql += f' ;\n{blank:{indent*indent_inc}}owl:minCardinality {mincnt}'
            if maxcnt is not None:
                sparql += f' ;\n{blank:{indent*indent_inc}}owl:maxCardinality {maxcnt}'
        return sparql

    def update_shacl(self,
                     owlclass_iri: QName,
                     prop_iri: QName,
                     indent: int = 0, indent_inc: int = 4) -> str:
        # TODO: Include into unittest!
        blank = ''
        sparql_list = []
        for restriction_type, action in self._changeset:
            sparql = ''
            if restriction_type == PropertyRestrictionType.LANGUAGE_IN:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?z rdf:first ?head ;\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}rdf:rest ?tail .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:path {prop_iri} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {restriction_type.value} ?bnode .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?bnode rdf:rest* ?z .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?z rdf:first ?head ;\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}rdf:rest ?tail .\n'
                sparql += f'{blank:{indent * indent_inc}}}}'
                sparql_list.append(sparql)
                sparql = ''

            sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {owlclass_iri.prefix}:shacl {{\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {restriction_type.value} ?rval .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

            if action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {owlclass_iri.prefix}:shacl {{\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {restriction_type.value} {self._restrictions[restriction_type]} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'

            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {owlclass_iri.prefix}:shacl {{\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop sh:path {prop_iri} .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {restriction_type.value} ?rval\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        sparql = " ;\n".join(sparql_list)
        return sparql

    def delete_shacl(self,
                     owlclass_iri: QName,
                     prop_iri: QName,
                     restriction_type: PropertyRestrictionType,
                     indent: int = 0, indent_inc: int = 4) -> str:
        # TODO: Include into unittest!
        blank = ''
        sparql = ''
        if restriction_type == PropertyRestrictionType.LANGUAGE_IN:
            sparql += f'{blank:{indent*indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?z rdf:first ?head ;\n'
            sparql += f'{blank:{(indent + 2)*indent_inc}}rdf:rest ?tail .\n'
            sparql += f'{blank:{indent*indent_inc}}}}\n'
            sparql += f'{blank:{indent*indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?prop sh:path {prop_iri} .\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?prop {restriction_type.value} ?bnode .\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?bnode rdf:rest* ?z .\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?z rdf:first ?head ;\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}rdf:rest ?tail .\n'
            sparql += f'{blank:{indent*indent_inc}}}} ;\n'

        sparql += f'{blank:{indent*indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {restriction_type.value} ?rval .\n'
        sparql += f'{blank:{indent*indent_inc}}}}\n'
        sparql += f'{blank:{indent*indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}?prop sh:path {prop_iri} .\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}?prop {restriction_type.value} ?rval\n'
        sparql += f'{blank:{indent*indent_inc}}}}\n'
        return sparql

    def delete_owl(self, indent: int = 0, indent_inc: int = 4):
        # TODO: Include into unittest!
        pass



