from dataclasses import dataclass
from enum import Enum, unique
from typing import Dict, Union, Set, Optional, Callable

from pystrict import strict

from omaslib.src.dtypes.rdfset import RdfSet
from omaslib.src.enums.propertyrestrictiontype import PropertyRestrictionType
from omaslib.src.helpers.Notify import Notify
from omaslib.src.enums.action import Action
from omaslib.src.dtypes.languagein import LanguageIn
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_integer import Xsd_integer
from omaslib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.xsd.xsd_datetime import Xsd_dateTime
from omaslib.src.xsd.xsd_float import Xsd_float
from omaslib.src.xsd.xsd_string import Xsd_string
from omaslib.src.xsd.xsd_boolean import Xsd_boolean
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.enums.language import Language
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.enums.propertyclassattr import PropClassAttr


@unique
class Compare(Enum):
    LT = '__lt__'
    LE = '__le__'
    GT = '__gt__'
    GE = '__ge__'
    XX = '__x__'


RestrictionTypes = Xsd | RdfSet | LanguageIn | None

RestrictionContainer = Dict[PropertyRestrictionType, RestrictionTypes]


@dataclass
class PropertyRestrictionChange:
    old_value: RestrictionTypes
    action: Action
    test_in_use: bool




@strict
class PropertyRestrictions(Notify):
    """
    This class implements the SHACL/OWL restriction that omaslib supports

    SHACL allows to restrict the tha value range of properties. The following restrictions ate
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
    _restrictions: RestrictionContainer
    _test_in_use: Set[PropertyRestrictionType]
    _changeset: Dict[PropertyRestrictionType, PropertyRestrictionChange]
    _notifier: Callable[[type], None] | None

    datatypes = {
        PropertyRestrictionType.MIN_COUNT: {Xsd_integer},
        PropertyRestrictionType.MAX_COUNT: {Xsd_integer},
        PropertyRestrictionType.LANGUAGE_IN: {LanguageIn},
        PropertyRestrictionType.IN: {RdfSet},
        PropertyRestrictionType.UNIQUE_LANG: {Xsd_boolean},
        PropertyRestrictionType.MIN_LENGTH: {Xsd_integer},
        PropertyRestrictionType.MAX_LENGTH: {Xsd_integer},
        PropertyRestrictionType.PATTERN: {Xsd_string},
        PropertyRestrictionType.MIN_EXCLUSIVE: {Xsd_integer, Xsd_float},
        PropertyRestrictionType.MIN_INCLUSIVE: {Xsd_integer, Xsd_float},
        PropertyRestrictionType.MAX_EXCLUSIVE: {Xsd_integer, Xsd_float},
        PropertyRestrictionType.MAX_INCLUSIVE: {Xsd_integer, Xsd_float},
        PropertyRestrictionType.LESS_THAN: {Iri},
        PropertyRestrictionType.LESS_THAN_OR_EQUALS: {Iri},
    }
    compare = {
        PropertyRestrictionType.LANGUAGE_IN: Compare.XX,
        PropertyRestrictionType.IN: Compare.XX,
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

    def __init__(self, *,
                 restrictions: Optional[RestrictionContainer] = None,
                 notifier: Optional[Callable[[PropClassAttr], None]] = None,
                 notify_data: Optional[PropClassAttr] = None):
        """
        Constructor for restrictions
        :param restrictions: A Dict of restriction. See ~PropertyRestrictionType for SHACL-restriction supported
        """
        super().__init__(notifier, notify_data)
        self._changeset = {}
        if restrictions is None:
            self._restrictions = {}
        else:
            if restrictions.get(PropertyRestrictionType.UNIQUE_LANG) is not None:
                restrictions[PropertyRestrictionType.UNIQUE_LANG] = Xsd_boolean(restrictions[PropertyRestrictionType.UNIQUE_LANG])
            for restriction, value in restrictions.items():
                if restriction not in PropertyRestrictionType:
                    raise OmasError(f'Unsupported restriction "{restriction}"')
                if type(value) not in PropertyRestrictions.datatypes[restriction]:
                    raise OmasError(
                        f'Datatype of restriction "{restriction.value}": "{type(value)}" ({value}) is not valid'
                    )
            self._restrictions = restrictions
        self._test_in_use = set()

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

    def __getitem__(self, restriction_type: PropertyRestrictionType) -> RestrictionTypes:
        return self._restrictions[restriction_type]

    def __setitem__(self,
                    restriction_type: PropertyRestrictionType,
                    value: RestrictionTypes):
        if restriction_type not in PropertyRestrictionType:
            raise OmasError(f'Unsupported restriction "{restriction_type}"')
        if type(value) not in PropertyRestrictions.datatypes[restriction_type]:
            raise OmasError(
                f'Datatype of restriction "{restriction_type.value}": "{type(value)}" ({value}) is not valid'
            )
        if value == self._restrictions.get(restriction_type):
            return
        test_in_use: bool = True
        if self._restrictions.get(restriction_type):
            if PropertyRestrictions.compare[restriction_type] == Compare.GT:
                if value <= self._restrictions[restriction_type]:  # it's more restricting; not allowed if in use
                    test_in_use = False
            elif PropertyRestrictions.compare[restriction_type] == Compare.GE:
                if value < self._restrictions[restriction_type]:  # it's more restricting; not allowed if in use
                    test_in_use = False
            elif PropertyRestrictions.compare[restriction_type] == Compare.LT:
                if value >= self._restrictions[restriction_type]:  # it's more restricting; not allowed if in use
                    test_in_use = False
            elif PropertyRestrictions.compare[restriction_type] == Compare.LE:
                if value > self._restrictions[restriction_type]:  # it's more restricting; not allowed if in use
                    test_in_use = False
            elif restriction_type == PropertyRestrictionType.UNIQUE_LANG and value is False:
                test_in_use = False
            elif restriction_type == PropertyRestrictionType.LANGUAGE_IN:
                if not self._restrictions[restriction_type] > value:  # it's more restricting; not allowed if in use
                    test_in_use = False
            self.notify()
        if self._changeset.get(restriction_type) is None:
            self._changeset[restriction_type] = PropertyRestrictionChange(self._restrictions.get(restriction_type),
                                                                          Action.REPLACE if self._restrictions.get(restriction_type) else Action.CREATE,
                                                                          test_in_use)
        self.notify()
        self._restrictions[restriction_type] = value

    def __delitem__(self, restriction_type: PropertyRestrictionType):  # TODO: Sparql output for this case
        if self._restrictions.get(restriction_type) is not None:
            self._changeset[restriction_type] = PropertyRestrictionChange(self._restrictions.get(restriction_type), Action.DELETE, False)
            del self._restrictions[restriction_type]
            self.notify()

    def undo(self, restriction_type: Optional[PropertyRestrictionType] = None) -> None:
        """
        Undo the change of a given restriction or of all restrictions that changed
        :param restriction_type: The restriction to undo. If None, all changes will be undone
        :return: None
        """
        if restriction_type is None:
            for rt in self._changeset:
                if self._changeset[rt].action == Action.CREATE:
                    del self._restrictions[rt]
                else:
                    self._restrictions[rt] = self._changeset[rt].old_value
            self._changeset = {}
        else:
            if self._changeset.get(restriction_type) is not None:
                if self._changeset[restriction_type].action == Action.CREATE:
                    del self._restrictions[restriction_type]
                else:
                    self._restrictions[restriction_type] = self._changeset[restriction_type].old_value
                del self._changeset[restriction_type]

    @property
    def changeset(self) -> Dict[PropertyRestrictionType, PropertyRestrictionChange]:
        return self._changeset

    def changeset_clear(self) -> None:
        self._changeset = {}

    def get(self, restriction_type: PropertyRestrictionType) -> Union[int, float, str, Set[Language], Xsd_QName, None]:
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
            # since we remove restrictions, no test_in_use necessary!
            self._changeset[restriction_type] = PropertyRestrictionChange(self._restrictions.get(restriction_type), Action.DELETE, False)
            self.notify()
        self._restrictions = {}

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
            shacl += f' ;\n{blank:{indent * indent_inc}}{name.value} {rval.toRdf}'
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
        mincnt = None
        if self._restrictions.get(PropertyRestrictionType.MIN_COUNT) is not None:
            mincnt = Xsd_nonNegativeInteger(self._restrictions[PropertyRestrictionType.MIN_COUNT])
        maxcnt = None
        if self._restrictions.get(PropertyRestrictionType.MAX_COUNT) is not None:
            maxcnt = Xsd_nonNegativeInteger(self._restrictions[PropertyRestrictionType.MAX_COUNT])
        if mincnt is not None and maxcnt is not None and mincnt == maxcnt:
            sparql += f' ;\n{blank:{indent*indent_inc}}owl:cardinality {mincnt.toRdf}'
        else:
            if mincnt is not None:
                sparql += f' ;\n{blank:{indent*indent_inc}}owl:minCardinality {mincnt.toRdf}'
            if maxcnt is not None:
                sparql += f' ;\n{blank:{indent*indent_inc}}owl:maxCardinality {maxcnt.toRdf}'
        return sparql

    def update_shacl(self, *,
                     graph: Xsd_NCName,
                     owlclass_iri: Iri | None = None,
                     prop_iri: Iri,
                     modified: Xsd_dateTime,
                     indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql_list = []
        for restriction_type, change in self._changeset.items():
            sparql = f'#\n# (X) Process "{restriction_type.value}" with Action "{change.action.value}"\n#\n'
            sparql += f'WITH {graph}:shacl\n'
            if restriction_type == PropertyRestrictionType.LANGUAGE_IN or restriction_type == PropertyRestrictionType.IN:
                #
                # The SHACL property sh:languageIn is implemented as a RDF List with blank nodes having
                # a rdf:first and rdf:rest property. This makes the manipulation a bit complicated. If
                # sh:languageIn is modified we delete the complete list and replace it by the new list.
                #
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?z rdf:first ?head ;\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}rdf:rest ?tail .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
                if owlclass_iri:
                    sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:path {prop_iri.toRdf} .\n'
                else:
                    sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({prop_iri}Shape as ?prop)\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {restriction_type.value} ?bnode .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?bnode rdf:rest* ?z .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?z rdf:first ?head ;\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}rdf:rest ?tail .\n'
                sparql += f'{blank:{indent * indent_inc}}}}'
                sparql_list.append(sparql)
                sparql = f'WITH {graph}:shacl\n'

            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {restriction_type.value} ?rval .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {restriction_type.value} {self._restrictions[restriction_type].toRdf} .\n'

                sparql += f'{blank:{indent * indent_inc}}}}\n'

            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            if owlclass_iri:
                sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:path {prop_iri.toRdf} .\n'
            else:
                sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({prop_iri}Shape as ?prop)\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {restriction_type.value} ?rval .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {modified.toRdf})\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        sparql = ";\n".join(sparql_list)
        return sparql

    def update_owl(self, *,
                   graph: Xsd_NCName,
                   owlclass_iri: Iri | None = None,
                   prop_iri: Iri,
                   modified: Xsd_dateTime,
                   indent: int = 0, indent_inc: int = 4) -> str:
        """
        Updates the OWL restriction classes for the cardinality

        :param owlclass_iri:
        :param prop_iri:
        :param modified:
        :param indent:
        :param indent_inc:
        :return:
        """
        blank = ' '
        minmax_done = False
        sparql = ''
        for restriction_type, change in self._changeset.items():
            if minmax_done:
                continue
            if restriction_type == PropertyRestrictionType.MAX_COUNT or restriction_type == PropertyRestrictionType.MIN_COUNT:
                old_min_count: Union[Xsd_nonNegativeInteger, None]
                old_max_count: Union[Xsd_nonNegativeInteger, None]
                if self._changeset.get(PropertyRestrictionType.MIN_COUNT) is None:
                    old_min_count = Xsd_nonNegativeInteger(self._restrictions.get(PropertyRestrictionType.MIN_COUNT))
                else:
                    old_min_count = Xsd_nonNegativeInteger(self._changeset[PropertyRestrictionType.MIN_COUNT].old_value)
                if self._changeset.get(PropertyRestrictionType.MAX_COUNT) is None:
                    old_max_count = Xsd_nonNegativeInteger(self._restrictions.get(PropertyRestrictionType.MAX_COUNT))
                else:
                    old_max_count = Xsd_nonNegativeInteger(self._changeset[PropertyRestrictionType.MAX_COUNT].old_value)
                sparql += f'#\n# Process "sh:maxCount"/"sh:minCount"...\n#\n'
                sparql += f'WITH {graph}:onto\n'
                if old_max_count is not None and old_max_count == old_min_count:
                    sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:cardinality {old_max_count.toRdf} .\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                else:
                    sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                    if old_min_count is not None:
                        sparql += f'{blank:{(indent + 2) * indent_inc}}?prop owl:minCardinality {old_min_count.toRdf} .\n'
                    if old_max_count is not None:
                        sparql += f'{blank:{(indent + 2) * indent_inc}}?prop owl:maxCardinality {old_max_count.toRdf} .\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                # we have now removed all cardinality information
                new_max_count: Union[Xsd_nonNegativeInteger, None]
                new_min_count: Union[Xsd_nonNegativeInteger, None]
                if self._restrictions.get(PropertyRestrictionType.MIN_COUNT) is None:
                    new_min_count = None
                else:
                    new_min_count = Xsd_nonNegativeInteger(self._restrictions[PropertyRestrictionType.MIN_COUNT])
                if self._restrictions.get(PropertyRestrictionType.MAX_COUNT) is None:
                    new_max_count = None
                else:
                    new_max_count = Xsd_nonNegativeInteger(self._restrictions[PropertyRestrictionType.MAX_COUNT])
                if new_max_count is not None and new_max_count == new_min_count:
                    sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:cardinality {new_max_count.toRdf} .\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                else:
                    sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                    if new_max_count is not None:
                        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:maxCardinality {new_max_count.toRdf} .\n'
                    if new_min_count is not None and new_min_count > 0:
                        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:minCardinality {new_min_count.toRdf} .\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
                if owlclass_iri:
                    sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri} rdfs:subClassOf ?prop .\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:onProperty {prop_iri.toRdf} .\n'
                else:
                    sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({prop_iri.toRdf} as ?prop)\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {modified.toRdf})\n'
                sparql += f'{blank:{indent * indent_inc}}}}'
                minmax_done = True
        return sparql

    def delete_shacl(self, *,
                     graph: Xsd_NCName,
                     owlclass_iri: Iri | None = None,
                     prop_iri: Iri,
                     restriction_type: PropertyRestrictionType,
                     indent: int = 0, indent_inc: int = 4) -> str:
        # TODO: Include into unittest!
        blank = ''
        sparql = f'WITH {graph}:shacl\n'
        if restriction_type == PropertyRestrictionType.LANGUAGE_IN or restriction_type == PropertyRestrictionType.MIN_COUNT:
            sparql += f'{blank:{indent*indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?z rdf:first ?head ;\n'
            sparql += f'{blank:{(indent + 2)*indent_inc}}rdf:rest ?tail .\n'
            sparql += f'{blank:{indent*indent_inc}}}}\n'
            sparql += f'{blank:{indent*indent_inc}}WHERE {{\n'
            if owlclass_iri:
                sparql += f'{blank:{(indent + 1)*indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
                sparql += f'{blank:{(indent + 1)*indent_inc}}?prop sh:path {prop_iri.toRdf} .\n'
            else:
                sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({prop_iri.toRdf} as ?prop)\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?prop {restriction_type.value} ?bnode .\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?bnode rdf:rest* ?z .\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?z rdf:first ?head ;\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}rdf:rest ?tail .\n'
            sparql += f'{blank:{indent*indent_inc}}}} ;\n'

        sparql += f'{blank:{indent*indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {restriction_type.value} ?rval .\n'
        sparql += f'{blank:{indent*indent_inc}}}}\n'
        sparql += f'{blank:{indent*indent_inc}}WHERE {{\n'
        if owlclass_iri:
            sparql += f'{blank:{(indent + 1)*indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}?prop sh:path {prop_iri.toRdf} .\n'
        else:
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({prop_iri.toRdf} as ?prop)\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}?prop {restriction_type.value} ?rval\n'
        sparql += f'{blank:{indent*indent_inc}}}}\n'
        return sparql

    def delete_owl(self, indent: int = 0, indent_inc: int = 4):
        # TODO: Include into unittest!
        pass



