from enum import unique, Enum
from typing import Dict, List, Optional, Union, Set

from pystrict import strict

from omaslib.src.helpers.language import Language
from omaslib.src.helpers.omaserror import OmasError


@strict
class LangString:
    _langstring: Dict[Language, str]
    _priorities: List[Language]
    _changeset: Set[Language]

    def __init__(self,
                 langstring: Optional[Union[str, List[str], Dict[str, str], Dict[Language, str]]] = None,
                 priorities: Optional[List[Language]] = None):
        """
        Implements language dependent strings

        :param langstring: A definition of one or several langiage dependent strings. The parameter can either be
          - a string in the form "string@ll", eg "Lastname@en". A string without language qualifier has the language
            Language.XX associated
          - a list of strings: ["Lastname@en", "Nachname@de"]
          - a dict with language short names as key: {'en': "Lastname", 'de': "Nachname"}
          - a dict with Language enum values as keys: {Language.EN: "Lastname, Language.DE: "Nachname"}
        :param priorities: If a desired language is not found, then the next string is used given this priority list
          which as the form [Langguage.LL, ...], eg [Language.EN, Language.DE, Language.XX]. The default value
          is [Language.XX, Language.EN, Language.DE, Language.FR]
        """
        self._changeset = set()
        if isinstance(langstring, str):
            index = langstring.find('@')
            if index >= 0:
                tmpls: str = langstring[(index + 1):].upper()
                try:
                    self._langstring = {Language[tmpls]: langstring[:index]}
                except KeyError as er:
                    raise OmasError(f'Language in string "{langstring}" is invalid')
            else:
                self._langstring = {Language.XX: langstring}
        elif isinstance(langstring, List):
            self._langstring = {}
            for lstr in langstring:
                index = lstr.find('@')
                if index >= 0:
                    tmpls: str = lstr[(index + 1):].upper()
                    try:
                        self._langstring[Language[tmpls]] = lstr[:index]
                    except KeyError as er:
                        raise OmasError(f'Language in string "{lstr}" is invalid')
                else:
                    self._langstring[Language.XX] = lstr
        elif langstring is None:
            self._langstring = {}
        else:
            self._langstring = {}
            for lang, value in langstring.items():
                if isinstance(lang, Language):
                    self._langstring[lang] = value
                else:
                    try:
                        self._langstring[Language[lang.upper()]] = value
                    except KeyError as er:
                        raise OmasError(f'Language "{lang}" is invalid')
        if priorities is not None:
            self._priorities = priorities
        else:
            self._priorities = [Language.XX, Language.EN, Language.DE, Language.FR]

    def __getitem__(self, lang: Union[str, Language]) -> str:
        if isinstance(lang, str):
            try:
                lang = Language[lang.upper()]
            except KeyError:
                raise OmasError(f'Language "{lang}" is invalid')
        s = self._langstring.get(lang)
        if s:
            return s
        else:
            for ll in self._priorities:
                if self._langstring.get(ll) is not None:
                    return self._langstring.get(ll)
            return '--no string--'

    def __setitem__(self, lang: Union[Language, str], value: str) -> None:
        if isinstance(lang, Language):
            self._langstring[lang] = value
            self._changeset.add(lang)
        elif isinstance(lang, str):
            try:
                lobj = Language[lang.upper()]
                self._langstring[lobj] = value
                self._changeset.add(lobj)
            except (KeyError, ValueError) as err:
                raise OmasError(f'Language "{lang}" is invalid')
        else:
            raise OmasError(f'Language "{lang}" is invalid')

    def __delitem__(self, lang: Union[Language, str]) -> None:
        if isinstance(lang, Language):
            try:
                del self._langstring[lang]
                self._changeset.add(lang)
            except KeyError as err:
                raise OmasError(f'No language string of language: "{lang}"!')
        elif isinstance(lang, str):
            try:
                lobj = Language[lang.upper()]
                del self._langstring[lobj]
                self._changeset.add(lobj)
            except (KeyError, ValueError) as err:
                raise OmasError(f'No language string of language: "{lang}"!')
        else:
            raise OmasError(f'Unsupported language value {lang}!')

    def __str__(self) -> str:
        langlist = [f'"{val}"@{lang.name.lower()}' for lang, val in self._langstring.items()]
        resstr = ", ".join(langlist)
        return resstr

    def get(self, lang: Union[str, Language]):
        if isinstance(lang, str):
            lang = Language[lang.upper()]
        return self._langstring.get(lang)

    def __eq__(self, other) -> bool:
        if len(self._langstring) != len(other._langstring):
            return False
        for lang in self._langstring:
            if other.langstring.get(lang) is None:
                return False
            if self._langstring.get(lang) != other.langstring.get(lang):
                return False
        return True

    def items(self):
        return self._langstring.items()

    @property
    def langstring(self) -> Dict[Language, str]:
        return self._langstring

    def add(self, langs: Union[str, List[str], Dict[str, str], Dict[Language, str]]):
        if isinstance(langs, str):
            index = langs.find('@')
            if index >= 0:
                lstr = langs[(index + 1):].upper()
                lobj = None
                try:
                    lobj = Language[lstr]
                except KeyError:
                    raise OmasError(f'Language "{lstr}" is invalid')
                self._langstring[lobj] = langs[:index]
                self._changeset.add(lobj)
            else:
                self._langstring[Language.XX] = langs
                self._changeset.add(Language.XX)
        elif isinstance(langs, list):
            for lang in langs:
                index = lang.find('@')
                if index >= 0:
                    lstr = lang[(index + 1):].upper()
                    lobj = None
                    try:
                        lobj = Language[lstr]
                    except KeyError:
                        raise OmasError(f'Language "{lstr}" is invalid')
                    self._langstring[lobj] = langs[:index]
                    self._changeset.add(lobj)
                else:
                    self._langstring[Language.XX] = lang
                    self._changeset.add(Language.XX)
        elif isinstance(langs, Dict):
            for lang, value in langs.items():
                lobj = None
                if isinstance(lang, Language):
                    lobj = lang
                else:
                    try:
                        lobj = Language[lang.upper()]
                    except KeyError:
                        raise OmasError(f'Language "{lang}" is invalid')
                self._langstring[lobj] = value
                self._changeset.add(lobj)
        else:
            raise OmasError(f'Invalid data type for langs')

    @property
    def changeset(self) -> Set[Language]:
        return self._changeset

if __name__ == '__main__':
    ls1 = LangString("gaga")
    print(str(ls1))
    ls2 = LangString({
        Language.DE: "Deutsch....",
        Language.EN: "German...."
    })
    print(str(ls2))
    print(ls2[Language.EN])
    print(ls1[Language.DE])
    ls1.add({Language.DE: "gaga auf deutsch", Language.EN: "gaga in english"})
    print(str(ls1))
