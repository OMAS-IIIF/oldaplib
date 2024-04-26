"""
This module provides the handling for language dependent strings. RDF allows to attach a language tag to
a string to identify which language is used. In turtle/trig notation it has the form "string"@lang,
eg "this is a string in english"@en. In order to handle such strings easily in OMAS,
the Language class provides all necessary enumerations.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Callable, Self

from pystrict import strict

from omaslib.src.helpers.Notify import Notify
from omaslib.src.enums.action import Action
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_datetime import Xsd_dateTime
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.enums.language import Language
from omaslib.src.helpers.omaserror import OmasError, OmasErrorValue
from omaslib.src.enums.propertyclassattr import PropClassAttr
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd_string import Xsd_string


@dataclass
class LangStringChange:
    old_value: str | None
    action: Action

@strict
@serializer
class LangString(Notify):
    """
    Implements a multi-language representation of a string.

    RDF allows to tag strings with language identifieres, e.g. "this is a text"@en . To support multiple languages it
    may make sense to allow for some string properties a cardinality > 1 so that multiple strings in different labguages
    may be assigned. The SHACL restriction sh:uniqueLang allows to restrict the string to a unique value for each
    language. This class uses a Dict with the language as key (see Language.py) and the string as value. For strings
    with no attached language the Language.XX tag is used. Methods that require a language parameter, it can usually
    be given as member of the enum class *Language*, e.g. ``Language.EN`` as 2-character shortname, e.g. ``"en"``. The
    use of the enumeration is strongly recommended.
    An instance of this class implements some dictionary behaviours:

    - access to a specific language string representation: `myvar[Language.FR]` or `myvar["fr"]`
    - to add or replace a specific language string representation: `myvar[Language.DE] = "Ein neuer string"` or
      `myvar["de"] = "Ein neuer string"`.
    - to delete a language: `del myvar[Language.FR]`

    The class implements the following methods:

    - _LangString()_: Initiate a language string instance (`__init__()`)
    - _len()_: (see `__len__()_`) Return the number of language strings present in the instance
    - _str()_: (see `__str__()`) Return the string representation of the Langstring as it would be used in a SPARQL insert statement
    - _get()_: (see `__get__()`)Return the language string or None, if it does not exist
    - _==_: (see `__eq__()`) Test for equality of 2 langstrings
    - _!=_: (see `__ne__()`) Test for inequality of 2 langstrings
    - _items()_: (see `__items__()')Retuns an iterator over all strings in the LangString instance
    - _langstring_: Returns dict containing all languages present in the instance
    - _add()_: Add a string
    - _undo_(): Forget all changes
    - _changeset()_: Return the changeset dict (Note: this is not for generic use)
    - _changeset_clear()_: Clear changeset to an empty dict
    - _update_shacl_(): Return the SPARQL code piece that updates a Language string SHACL part of the triple store.
    - _delete_shacl_(): Return the SPARQL code piece that deletes an LanguageString
    """
    _langstring: Dict[Language, str]
    _changeset: Dict[Language, LangStringChange]
    _notifier: Callable[[type], None] | None

    defaultLanguage: Language = Language.EN
    priorities: list[Language] = [Language.EN, Language.DE, Language.FR]

    def __init__(self, *args: str | Xsd_string | List[str] | Dict[Language | str, str] | Self | None,
                 langstring: str | Xsd_string | List[str] | Dict[Language | str, str] | Self | None = None,
                 notifier: Optional[Callable[[PropClassAttr], None]] = None,
                 notify_data: Optional[PropClassAttr] = None):
        """
        Implements language dependent strings.

        The parameter `langstring`can either be

        - a string in the form `"string@ll"`, eg `"Lastname@en"`. A string without language qualifier has the
            language `Language.XX` associated.
        - A list of strings: `["Lastname@en", "Nachname@de"]`
        - A dict with language short names as key: `{'en': "Lastname", 'de': "Nachname"}`
        - A dict with Language enum values as keys: `{Language.EN: "Lastname, Language.DE: "Nachname"}`

        :param langstring: A definition of one or several langiage dependent strings.
        :param priorities: If a desired language is not found, then the next string is used given this priority list
          which as the form [Langguage.LL, ...], eg [Language.EN, Language.DE, Language.XX]. The default value
          is [Language.XX, Language.EN, Language.DE, Language.FR]
        """
        super().__init__(notifier, notify_data)
        self._changeset = {}
        self._langstring = {}

        if len(args) <= 1:
            if len(args) == 1:
                langstring = args[0]
            if langstring is None:
                return
            else:
                if isinstance(langstring, LangString):
                    self._langstring = langstring._langstring
                elif isinstance(langstring, Xsd_string):
                    if not langstring:
                        return
                    l = LangString.defaultLanguage if langstring.lang is None else langstring.lang
                    self._langstring[l] = langstring.value
                elif isinstance(langstring, str):
                    if not langstring:
                        return
                    xstr = Xsd_string(langstring)
                    l = LangString.defaultLanguage if xstr.lang is None else xstr.lang
                    self._langstring[l] = xstr.value
                elif isinstance(langstring, (list, tuple)):
                    for lstr in langstring:
                        xstr = Xsd_string(lstr)
                        if not xstr:
                            continue
                        l = LangString.defaultLanguage if xstr.lang is None else xstr.lang
                        self._langstring[l] = xstr.value
                elif isinstance(langstring, dict):
                    for lang, value in langstring.items():
                        xstr = Xsd_string(value, lang)
                        if not xstr:
                            continue
                        l = LangString.defaultLanguage if xstr.lang is None else xstr.lang
                        self._langstring[l] = xstr.value
                else:
                    raise OmasErrorValue(f'LangString parameter has wrong datatype: {type(langstring).__name__}, must be "str | Xsd_string | List[str] | Dict[Language | str, str] | LangString"')
        else:
            for langstring in args:
                if isinstance(langstring, Xsd_string):
                    if langstring:
                        l = LangString.defaultLanguage if langstring.lang is None else langstring.lang
                        self._langstring[l] = langstring.value
                elif isinstance(langstring, str):
                    xstr = Xsd_string(langstring)
                    if not xstr:
                        continue
                    l = LangString.defaultLanguage if xstr.lang is None else xstr.lang
                    self._langstring[l] = xstr.value
                else:
                    raise OmasErrorValue(
                        f'LangString parameter has wrong datatype: {type(langstring).__name__}, must be "str | Xsd_string | List[str] | Dict[Language | str, str] | LangString"')

    def __len__(self):
        """
        Returns the number of languages defined for the given the LangString instance
        :return: Number of languages defined
        """
        return len(self._langstring)

    def __bool__(self):
        return len(self._langstring) > 0

    def __getitem__(self, lang: str | Language) -> str:
        """
        Get the string of the given language.
        :param lang: The desired language, either as string shortname or as Language enum
        :return: The string – may return '--no string--' as placeholder of language is not available
        """
        if isinstance(lang, str):
            try:
                lang = Language[lang.upper()]
            except KeyError:
                raise OmasError(f'Language "{lang}" is invalid')
        s = self._langstring.get(lang)
        if s:
            return s
        else:
            for ll in self.priorities:
                if self._langstring.get(ll) is not None:
                    return self._langstring[ll]
            return '--no string--'

    def __setitem__(self, lang: Language | str, value: str) -> None:
        """
        Set a new or change an existing language steing
        :param lang: Language as shortname or Language enum
        :param value: The string value
        :return: None
        """
        if isinstance(lang, Language):
            if self._changeset.get(lang) is None:  # only the first change is recorded
                self._changeset[lang] = LangStringChange(self._langstring.get(lang),
                                                         Action.REPLACE if self._langstring.get(lang) else Action.CREATE)
            self._langstring[lang] = value
            self.notify()
        elif isinstance(lang, str):
            try:
                lobj = Language[lang.upper()]
                if self._changeset.get(lobj) is None:  # only the first change is recorded
                    self._changeset[lobj] = LangStringChange(self._langstring.get(lobj),
                                                             Action.REPLACE if self._langstring.get(lobj) else Action.CREATE)
                self._langstring[lobj] = value
                self.notify()
            except (KeyError, ValueError) as err:
                raise OmasError(f'Language "{lang}" is invalid: {err}.')
        else:
            raise OmasError(f'Language "{lang}" is invalid.')

    def __delitem__(self, lang: Language | str) -> None:
        """
        Delete a given language from a language string
         :param lang: The language (as short name of as Language enum) to be deleted
        :type lang: Language or str (shortname)
        :return: Does return nothing
        :rtype: None
        """
        if isinstance(lang, Language):
            try:
                if self._changeset.get(lang) is None:
                    self._changeset[lang] = LangStringChange(self._langstring[lang], Action.DELETE)
                del self._langstring[lang]
                self.notify()
            except KeyError as err:
                raise OmasError(f'No language string of language: "{lang}"!')
        elif isinstance(lang, str):
            try:
                lobj = Language[lang.upper()]
                if self._changeset.get(lobj) is None:
                    self._changeset[lobj] = LangStringChange(self._langstring[lobj], Action.DELETE)
                del self._langstring[lobj]
                self.notify()
            except (KeyError, ValueError) as err:
                raise OmasError(f'No language string of language: "{lang}"!')
        else:
            raise OmasError(f'Unsupported language value {lang}!')

    def __str__(self) -> str:
        """
        Return the language string as it would be used in a SPARQL insert statement
        :return: language string as it would be used in a SPARQL insert statement
        :rtype: str
        """
        langlist = [f'"{val}@{lang.name.lower()}"' for lang, val in self._langstring.items()]
        resstr = ", ".join(langlist)
        return resstr

    def __repr__(self) -> str:
        return f'LangString({self.__str__()})'

    @property
    def toRdf(self) -> str:
        langStringList = [Xsd_string(val, lang).toRdf for lang, val in self._langstring.items()]
        resstr = ", ".join(langStringList)
        return resstr

    def _as_dict(self) -> dict:
        """
        Return a dictionary used for JSONification of a LangString instance
        :return: Dict that can be serialized
        """
        return {
            'langstring': [f'"{val}@{lang.value.lower()}"' for lang, val in self._langstring.items()],
            'priorities': [lang.value.lower() for lang in self.priorities]
        }

    def get(self, lang: str | Language, default: str = None) -> str:
        """
        Return the language string or None, if it does not exist
        :param lang: Desired language
        :type lang: Either a string (shortname) or a Language enum element.
        :return: language string
        :rtype: str
        """
        if isinstance(lang, str):
            lang = Language[lang.upper()]
        return self._langstring.get(lang, default)

    def __bool__(self) -> bool:
        return len(self._langstring) > 0

    def __eq__(self, other: Self | None) -> bool:
        """
        Test for equality of two language strings
        :param other: The other Language string to compare to
        :type other: LanguageString
        :return: True or False
        :rtype: bool
        """
        if other is None:
            return False
        if len(self._langstring) != len(other._langstring):
            return False
        for lang in self._langstring:
            if other.langstring.get(lang) is None:
                return False
            if self._langstring.get(lang) != other.langstring.get(lang):
                return False
        return True

    def __ne__(self, other: Self) -> bool:
        """
        Test for inequality of two language strings
        :param other: The other Language string to compare to
        :type other: LanguageString
        :return: True if inequal, otherweise False
        :rtype: bool
        """
        if len(self._langstring) != len(other._langstring):
            return True
        for lang in self._langstring:
            if other.langstring.get(lang) is None:
                return True
            if self._langstring.get(lang) != other.langstring.get(lang):
                return True
        return False

    def items(self):
        """
        Return an iterator over the language strings
        :return: iterator over the language strings
        :rtype: iterator
        """
        return self._langstring.items()

    @property
    def langstring(self) -> Dict[Language, str]:
        """
        All language strings as Dict
        :return: A dictionary of all language strings
        :rtype: Dict
        """
        return self._langstring

    def add(self, *args: str | Xsd_string | List[str] | Dict[Language | str, str] | Self) -> None:
        """
        Add one or several new languages to a lang string. The method accepts several forms:
        * ``mylstr.add("a new string@en")``
        * ``mylstr.add(["a new string@en", "eine neue Zeichenketter@de])``
        * ``mylstr.add({"fr": "Nouveau", "de": "Neue Zeichenketter"})``
        * ``mylstr.add({Language.FR: "Nouveau", Language.DE: "Neue Zeichenketter"})
        As this, it's a very versatile method for adding new languages to a LanguageString instance
        :param langs: The language/string pairs as single value, list or dict
        :type langs: str | List[str] | Dict[str, str] | Dict[Language, str]
        :return: No return value
        :rtype: None
        """
        if len(args) == 0:
            return
        elif len(args) == 1:
            if isinstance(args[0], LangString):
                for lang, val in args[0].langstring.items():
                    oldval = self._langstring.get(lang)
                    self._langstring[lang] = val
                    if self._changeset.get(lang) is None:  # only the first change is recorded
                        self._changeset[lang] = LangStringChange(oldval,
                                                                 Action.REPLACE if oldval is not None else Action.CREATE)
            elif isinstance(args[0], Xsd_string):
                l = LangString.defaultLanguage if args[0].lang is None else args[0].lang
                oldval = self._langstring.get(l)
                self._langstring[l] = args[0].value
                if self._changeset.get(l) is None:  # only the first change is recorded
                    self._changeset[l] = LangStringChange(oldval,
                                                             Action.REPLACE if oldval is not None else Action.CREATE)
            elif isinstance(args[0], str):
                xstr = Xsd_string(args[0])
                l = xstr.lang or LangString.defaultLanguage
                oldval = self._langstring.get(l)
                self._langstring[l] = xstr.value
                if self._changeset.get(l) is None:  # only the first change is recorded
                    self._changeset[l] = LangStringChange(oldval, Action.REPLACE if oldval is not None else Action.CREATE)
            elif isinstance(args[0], (list, tuple)):
                for lstr in args[0]:
                    xstr = Xsd_string(lstr)
                    l = xstr.lang or LangString.defaultLanguage
                    oldval = self._langstring.get(l)
                    self._langstring[l] = xstr.value
                    if self._changeset.get(l) is None:  # only the first change is recorded
                        self._changeset[l] = LangStringChange(oldval, Action.REPLACE if oldval is not None else Action.CREATE)
            elif isinstance(args[0], dict):
                for lang, value in args[0].items():
                    xstr = Xsd_string(value, lang)
                    l = xstr.lang or LangString.defaultLanguage
                    oldval = self._langstring.get(l)
                    self._langstring[l] = xstr.value
                    if self._changeset.get(l) is None:  # only the first change is recorded
                        self._changeset[l] = LangStringChange(oldval,
                                                              Action.REPLACE if oldval is not None else Action.CREATE)
            else:
                raise OmasErrorValue(
                    f'LangString parameter has wrong datatype: {type(args[0]).__name__}, must be "str | Xsd_string | List[str] | Dict[Language | str, str] | LangString"')
        else:
            for langstring in args:
                if isinstance(langstring, Xsd_string):
                    l = langstring.lang or LangString.defaultLanguage
                    oldval = self._langstring.get(l)
                    self._langstring[l] = langstring.value
                    if self._changeset.get(l) is None:  # only the first change is recorded
                        self._changeset[l] = LangStringChange(oldval,
                                                              Action.REPLACE if oldval is not None else Action.CREATE)
                elif isinstance(langstring, str):
                    xstr = Xsd_string(langstring)
                    l = xstr.lang or LangString.defaultLanguage
                    oldval = self._langstring.get(l)
                    self._langstring[l] = xstr.value
                    if self._changeset.get(l) is None:  # only the first change is recorded
                        self._changeset[l] = LangStringChange(oldval,
                                                              Action.REPLACE if oldval is not None else Action.CREATE)
                else:
                    raise OmasErrorValue(
                        f'LangString parameter has wrong datatype: {type(langstring).__name__}, must be "str | Xsd_string | List[str] | Dict[Language | str, str] | LangString"')

    def undo(self) -> None:
        """
        Undo all changes made since last update/creation/read
        :return: Nothing
        :rtype: None
        """
        for lang, change in self._changeset.items():
            if change.action == Action.CREATE:
                del self._langstring[lang]
            else:
                self._langstring[lang] = change.old_value
        self._changeset = {}

    @property
    def changeset(self) -> Dict[Language, LangStringChange]:
        """
        Return the changeset dict (Note: this is not for generic use)
        :return: The changeset information
        :rtype: Dict[Language, LangStringChange]
        """
        return self._changeset

    def changeset_clear(self) -> None:
        """
        Clear changeset to an empty dict
        :return: Nothing
        :rtype: None
        """
        self._changeset = {}

    def create(self, *,
               graph: Xsd_QName,
               subject: Iri,
               field: Xsd_QName,
               indent: int = 0, indent_inc: int = 4):
        blank = ''
        sparql_list = []
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {graph} {{\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}{subject.toRdf} {field.toRdf} {self.toRdf} .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        return sparql

    def delete(self, *,
               graph: Xsd_QName,
               subject: Iri,
               field: Xsd_QName,
               indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql_list = []
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}DELETE WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {graph} {{\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}{subject.toRdf} {field.toRdf} ?o .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        return sparql

    def update(self, *,
               graph: Xsd_QName,
               subject: Iri,
               subjectvar: str,
               field: Xsd_QName,
               indent: int = 0, indent_inc: int = 4) -> List[str]:
        blank = ''
        sparql_list = []
        for lang, change in self._changeset.items():
            if change.action != Action.CREATE:
                sparql = f'{blank:{indent * indent_inc}}DELETE DATA {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {graph} {{\n'
                tmpstr = f'"{change.old_value}"'
                tmpstr += "@" + lang.name.lower()
                sparql += f'{blank:{(indent + 2) * indent_inc}}{subject.toRdf} {field.toRdf} {tmpstr} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql_list.append(sparql)
            if change.action != Action.DELETE:
                sparql = f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {graph} {{\n'
                langstr = f'"{self._langstring[lang]}"'
                langstr += "@" + lang.name.lower()
                sparql += f'{blank:{(indent + 2) * indent_inc}}{subject.toRdf} {field.toRdf} {langstr} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql_list.append(sparql)

            # sparql = ''
            # sparql += f'{blank:{indent * indent_inc}}WITH {graph}\n'
            # if change.action != Action.CREATE:
            #     sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
            #     tmpstr = f'"{change.old_value}"'
            #     if lang != Language.XX:
            #         tmpstr += "@" + lang.name.lower()
            #     sparql += f'{blank:{(indent + 1) * indent_inc}}{subjectvar} {repr(field)} {tmpstr} .\n'
            #     sparql += f'{blank:{indent * indent_inc}}}}\n'
            #
            # if change.action != Action.DELETE:
            #     sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
            #     langstr = f'"{self._langstring[lang]}"'
            #     if lang != Language.XX:
            #         langstr += "@" + lang.name.lower()
            #     sparql += f'{blank:{(indent + 1) * indent_inc}}{subjectvar} {repr(field)} {langstr} .\n'
            #     sparql += f'{blank:{indent * indent_inc}}}}\n'
            #
            # sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            # sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({repr(subject)} as {subjectvar}) .\n'
            # if change.action != Action.CREATE:
            #     tmpstr = f'"{change.old_value}"'
            #     if lang != Language.XX:
            #         tmpstr += "@" + lang.name.lower()
            #     sparql += f'{blank:{(indent + 1) * indent_inc}}{subjectvar} {repr(field)} {tmpstr} .\n'
            # sparql += f'{blank:{indent * indent_inc}}}}'
            # sparql_list.append(sparql)
        return sparql_list

    def update_shacl(self, *,
                     graph: Xsd_NCName,
                     owlclass_iri: Iri | None = None,
                     prop_iri: Iri,
                     attr: PropClassAttr,
                     modified: Xsd_dateTime,
                     indent: int = 0, indent_inc: int = 4) -> str:
        """
        Return the SPARQL code piece that updates a Language string SHACL part of the triple store.
        :param graph: SPARQL graph as described in the introduction to OMASLIB
        :type graph: Xsd_NCName
        :param owlclass_iri: The OWL class IRI of the associated ResourceClass. May be omitted for standalone properties
        :type owlclass_iri: Xsd_QName | None
        :param prop_iri: The property IRI of the associated PropertyClass
        :type prop_iri: Xsd_QName
        :param attr: The QName of the associated attribute
        :type attr: Xsd_QName
        :param modified: timestamp that should be applied
        :type modified: datetime
        :param indent: The indent for the generated SPARQL code
        :type indent: int
        :param indent_inc: The indent increment for the generated SPARQL code
        :type indent_inc: int
        :return: SPARQL code piece
        :rtype: str
        """

        blank = ''
        sparql_list = []
        for lang, change in self._changeset.items():
            sparql = f'# LangString: Process "{lang.name}" with Action "{change.action.value}"\n'
            sparql += f'{blank:{indent * indent_inc}}WITH {graph}:shacl\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                tmpstr = f'"{change.old_value}"'
                tmpstr += "@" + lang.name.lower()
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {attr.value} {tmpstr} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'

            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                langstr = f'"{self._langstring[lang]}"'
                langstr += "@" + lang.name.lower()
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {attr.value} {langstr} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'

            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            if owlclass_iri:
                sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:path {prop_iri.toRdf} .\n'
            else:
                sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({prop_iri}Shape as ?prop) .\n'
            if change.action != Action.CREATE:
                tmpstr = f'"{change.old_value}"'
                tmpstr += "@" + lang.name.lower()
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {attr.value} {tmpstr} .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {modified.toRdf})\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        sparql = ";\n".join(sparql_list)
        return sparql

    def delete_shacl(self, *,
                     graph: Xsd_NCName,
                     owlclass_iri: Iri | None = None,
                     prop_iri: Iri,
                     attr: PropClassAttr,
                     modified: datetime,
                     indent: int = 0, indent_inc: int = 4) -> str:
        # TODO: Include into unit tests!
        """
        Return the SPARQL code piece that deletes an LanguageString
        :param graph: SPARQL graph as described in the introduction to OMASLIB
        :type graph: Xsd_NCName
        :param owlclass_iri: The OWL class IRI of the associated ResourceClass. May be omitted for standalone properties
        :type owlclass_iri: NCName or None
        :param prop_iri: The property IRI of the associated PropertyClass
        :type prop_iri: Xsd_QName
        :param attr: The QName of the associated attribute
        :type attr: Xsd_QName
        :param modified: Modification date to apply
        :type modified: datetime
        :param indent: The indent for the generated SPARQL code
        :type indent: int
        :param indent_inc: The indent increment for the generated SPARQL code
        :type indent_inc: int
        :return: Piece of SPARQL code that deletes the Language String from the SHACL definition
        :rtype: str
        """
        blank = ''
        sparql = f'#\n# Deleting the complete LangString data for {prop_iri} {attr.value}\n#\n'
        sparql += f'{blank:{indent * indent_inc}}WITH {graph}:shacl'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {attr.value} ?langval'
        sparql += f'{blank:{indent * indent_inc}}}}'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{'
        if owlclass_iri:
            sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:path {prop_iri.toRdf} .\n'
        else:
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({prop_iri}Shape as ?prop)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {attr.value} ?langval'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql


if __name__ == '__main__':
    l0 = LangString()
    print("l0: ", l0, len(l0))
    l1 = LangString([])
    print("l1 : ", l1, len(l1))
    l2 = LangString([""])
    print("l2 : ", l2, len(l2))

