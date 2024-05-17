import json
from typing import Iterator, Self, Iterable

from pystrict import strict

from oldaplib.src.dtypes.rdfset import RdfSet
from oldaplib.src.enums.language import Language
from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorType, OldapErrorKey
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd_string import Xsd_string


@serializer
class LanguageIn(RdfSet[Language], Notify):
    """
    This class implements the SHACL sh:languageIn datatype. It completely validates the input.
    If the validations failes, an OldapErrorValue is raised.
    """

    def __init__(self,
                 *args: Self | set[Language | str] | list[Language | str] | tuple[Language | str] | Language | str,
                 value: Self | set[Language | str] | list[Language | str] | tuple[Language | str] | Language | str | None = None):
        nargs = tuple()
        nvalue = None
        if len(args) == 0:
            if value is None:
                pass
            else:
                if isinstance(value, LanguageIn):
                    nvalue = value
                elif isinstance(value, (set, list, tuple)):
                    for v in value:
                        if not isinstance(v, (Language, str)):
                            raise OldapErrorType(f'Iterable contains element that is not an instance of "Language", but "{type(v).__name__}".')
                    try:
                        nvalue = [x if isinstance(x, Language) else Language[x.upper()] for x in value]
                    except KeyError as err:
                        raise OldapErrorKey(str(err))
                else:
                    if not isinstance(value, (Language, str)):
                        raise OldapErrorType(f'Value is not an instance of "Language", but "{type(value).__name__}".')
                    try:
                        nvalue = value if isinstance(value, Language) else Language[value.upper()]
                    except KeyError as err:
                        raise OldapErrorKey(str(err))
        elif len(args) == 1:
            if isinstance(args[0], LanguageIn):
                nargs = args
            if isinstance(args[0], (set, list, tuple)):
                for v in args[0]:
                    if not isinstance(v, (Language, str)):
                        raise OldapErrorType(f'Iterable contains element that is not an instance of "Xsd", but "{type(v).__name__}".')
                    try:
                        nargs = tuple([x if isinstance(x, Language) else Language[x.upper()] for x in args[0]])
                    except KeyError as err:
                        raise OldapErrorKey(str(err))
            else:
                if not isinstance(args[0], (LanguageIn, Language, str)):
                    raise OldapErrorType(f'Value is not an instance of "Language", but "{type(args[0]).__name__}".')
                if isinstance(args[0], LanguageIn):
                    nargs = args
                else:
                    try:
                        nargs = args if isinstance(args[0], Language) else (Language[args[0].upper()],)
                    except KeyError as err:
                        raise OldapErrorKey(str(err))
        else:
            for v in args:
                if not isinstance(v, (Language, str)):
                    raise OldapErrorType(f'Iterable contains element that is not an instance of "Xsd", but "{type(v).__name__}".')
                try:
                    nargs = tuple([x if isinstance(x, Language) else Language[x.upper()] for x in args])
                except KeyError as err:
                    raise OldapErrorKey(str(err))

        super().__init__(*nargs, value=nvalue)

    # def __str__(self):
    #     langlist = {f'{x.name.lower()}' for x in self}
    #     return f'({", ".join(langlist)})'
    #
    # def __repr__(self):
    #     langlist = {f'"{x.name.lower()}"' for x in self}
    #     return 'LanguageIn(' + ", ".join(langlist) + ')'

    def __contains__(self, val: Language | str) -> bool:
        if not isinstance(val, Language):
            val = Language[str(val).upper()]
        return super().__contains__(val)

    def add(self, language: Language | Xsd_string | str):
        if not isinstance(language, Language):
            try:
                language = Language[str(language).upper()]
            except ValueError as err:
                raise OldapErrorValue(str(err))
            except KeyError as err:
                raise OldapErrorKey(str(err))
        super().add(language)

    def discard(self, language: Language | Xsd_string | str):
        if not isinstance(language, Language):
            try:
                language = Language[str(language).upper()]
            except ValueError as err:
                raise OldapErrorValue(str(err))
        super().discard(language)

