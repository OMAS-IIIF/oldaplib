from typing import Iterator, Self

from omaslib.src.enums.language import Language
from omaslib.src.helpers.omaserror import OmasErrorValue, OmasErrorType
from omaslib.src.xsd.xsd_string import Xsd_string


class LanguageIn:
    """
    This class implements the SHACL sh:languageIn datatype. It completely validates the input.
    If the validations failes, an OmasErrorValue is raised.
    """
    __data: set[Language]

    def __init__(self, *args):
        __data: set[Language]

        """
        Constructor for the LanguageIn
        :param args: Either the languages as 2-letter short strings, or a set of
        """
        self.__data = set()
        try:
            if len(args) > 1:
                for arg in args:
                    if isinstance(arg, Language):
                        self.__data.add(arg)
                    elif isinstance(arg, str):
                        self.__data.add(Language[arg.upper()])
            elif len(args) == 1:
                if isinstance(args[0], Language):
                    self.__data.add(args[0])
                elif isinstance(args[0], str):
                    self.__data.add(Language[args[0].upper()])
                else:
                    try:
                        iter(args[0])
                    except:
                        raise OmasErrorValue("Parameter must be iterable.")
                    for arg in args[0]:
                        if isinstance(arg, Language):
                            self.__data.add(arg)
                        elif isinstance(arg, str):
                            self.__data.add(Language[arg.upper()])
        except KeyError:
            raise OmasErrorValue("Non valid language in set.")

    def __eq__(self, other: Self | set | None) -> bool:
        if other is None:
            return False
        if isinstance(other, LanguageIn):
            return self.__data == other.__data
        else:
            return self.__data == other

    def __ne__(self, other: Self | None):
        if other is None:
            return False
        if isinstance(other, LanguageIn):
            return self.__data != other.__data
        else:
            return self.__data != other

    def __gt__(self, other: Self) -> bool:
        if not isinstance(other, LanguageIn):
            raise OmasErrorType(f'Cannot compare {type(self).__name__} to {type(other).__name__}')
        return self.__data > other.__data

    def __ge__(self, other: Self) -> bool:
        if not isinstance(other, LanguageIn):
            raise OmasErrorType(f'Cannot compare {type(self).__name__} to {type(other).__name__}')
        return self.__data >= other.__data

    def __lt__(self, other: Self) -> bool:
        if not isinstance(other, LanguageIn):
            raise OmasErrorType(f'Cannot compare {type(self).__name__} to {type(other).__name__}')
        return self.__data < other.__data

    def __le__(self, other: Self) -> bool:
        if not isinstance(other, LanguageIn):
            raise OmasErrorType(f'Cannot compare {type(self).__name__} to {type(other).__name__}')
        return self.__data <= other.__data

    def __str__(self):
        langlist = {f'"{x.name.lower()}"' for x in self}
        return f'({", ".join(langlist)})'

    def __repr__(self):
        langlist = {f'"{x.name.lower()}"^^xsd:string' for x in self}
        return 'LanguageIn(' + ", ".join(langlist) + ')'

    def __contains__(self, language: Language):
        return language in self.__data

    def __iter__(self) -> Iterator[Language]:
        return iter(self.__data)

    def add(self, language: Language | Xsd_string | str):
        if not isinstance(language, Language):
            try:
                language = Language[str(language).upper()]
            except ValueError as err:
                raise OmasErrorValue(str(err))
        self.__data.add(language)

    def discard(self, language: Language | Xsd_string | str):
        if not isinstance(language, Language):
            try:
                language = Language[str(language).upper()]
            except ValueError as err:
                raise OmasErrorValue(str(err))
        self.__data.discard(language)

    @property
    def toRdf(self) -> str:
        langlist = {f'"{x.name.lower()}"^^xsd:string' for x in self}
        return f'({" ".join(langlist)})'

    def _as_dict(self):
        return {'value': [x for x in self.__data]}

    @property
    def value(self) -> set[Language]:
        return self.__data
