from enum import unique, Enum
from typing import Dict, List, Optional, Union, Set

from omaslib.src.helpers.omaserror import OmasError


@unique
class Languages(Enum):
    EN = "en"
    DE = "de"
    FR = "fr"
    IT = "it"
    XX = "xx"


class LangString:
    _langstring: Dict[Languages, str]
    _priorities: List[Languages]
    _changeset: Set[Languages]

    def __init__(self,
                 langstring: Optional[Union[str, Dict[Languages, str]]] = None,
                 priorities: Optional[List[Languages]] = None):
        """
        Implements langage dependent strings

        :param langstring: A Dict with the language (as Languages enum) as key and a string as value
        :param priorities: If a desired language is not found, then the next string is used given this priority list
        """
        self._changeset = set()
        if isinstance(langstring, str):
            self._langstring = {
                Languages.XX: langstring
            }
        elif langstring is None:
            self._langstring = {}
        else:
            self._langstring = langstring
        self._priorities = priorities if priorities is not None else [x for x in Languages]
        tmp = [x for x in Languages if x not in self._priorities]
        self._priorities.append(tmp)

    def __getitem__(self, lang: Languages) -> str:
        s = self._langstring.get(lang)
        if s:
            return s
        else:
            for ll in self._priorities:
                if self._langstring.get(ll) is not None:
                    return self._langstring.get(ll)
            return '--no string--'

    def __setitem__(self, lang: Union[Languages, str], value: str) -> None:
        if isinstance(lang, Languages):
            self._langstring[lang] = value
            self._changeset.add(lang)
        elif isinstance(lang, str):
            try:
                self._langstring[Languages(lang)] = value
                self._changeset.add(Languages(lang))
            except (KeyError, ValueError) as err:
                raise OmasError(f'Unsupported language or no string of given lang: {lang}!')
        else:
            raise OmasError(f'Unsupported language value: {lang}!')

    def __delitem__(self, lang: Union[Languages, str]) -> None:
        if isinstance(lang, Languages):
            try:
                del self._langstring[lang]
                self._changeset.add(lang)
            except KeyError as err:
                raise OmasError(f'No language string of language: "{lang}"!')
        elif isinstance(lang, str):
            try:
                del self._langstring[Languages(lang)]
                self._changeset.add(Languages(lang))
            except (KeyError, ValueError) as err:
                raise OmasError(f'Unsupported language or no string of given lang: {lang}!')
        else:
            raise OmasError(f'Unsupported language value {lang}!')

    def __str__(self) -> str:
        langlist = [f'"{val}"@{lang.value}' for lang, val in self._langstring.items() if lang != Languages.XX]
        resstr = ", ".join(langlist)
        if self._langstring.get(Languages.XX):
            if resstr:
                resstr += ', '
            resstr += f'"{self._langstring[Languages.XX]}"'
        return resstr

    def __eq__(self, other) -> bool:
        equal = True
        for lang in Languages:
            equal = self._langstring.get(lang) == other._langstring.get(lang)
            if not equal:
                break
        return equal

    def items(self):
        return self._langstring.items()

    @property
    def langstring(self) -> Dict[Languages, str]:
        return self._langstring

    def add(self, langs: Dict[Languages, str]):
        for lang, value in langs.items():
            self._langstring[lang] = value
            self._changeset.add(lang)


if __name__ == '__main__':
    ls1 = LangString("gaga")
    print(str(ls1))
    ls2 = LangString({
        Languages.DE: "Deutsch....",
        Languages.EN: "German...."
    })
    print(str(ls2))
    print(ls2[Languages.EN])
    print(ls1[Languages.DE])
    ls1.add({Languages.DE: "gaga auf deutsch", Languages.EN: "gaga in english"})
    print(str(ls1))
