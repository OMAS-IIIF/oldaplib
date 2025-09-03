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
    This class implements the SHACL sh:languageIn datatype, providing complete validation
    of the input. It ensures the input conforms to the required datatype, and raises
    an error if validation fails.

    This class is primarily designed to work with sets of languages, defining operations
    such as containment checks, addition, and removal. It validates inputs against the
    "Language" type to guarantee compatibility and correctness.

    It inherits from `RdfSet` and `Notify` to enable integration with RDF and notification
    mechanisms. Its usage aids in validating language-based constraints in SHACL data
    models.

    :ivar value: The internal parameter used for serialization/deserialization of
        language values.
    :type value: Self | set[Language | str] | list[Language | str] | tuple[Language | str] | Language | str | None
    """

    def __init__(self,
                 *args: Self | set[Language | str] | list[Language | str] | tuple[Language | str] | Language | str,
                 value: Self | set[Language | str] | list[Language | str] | tuple[Language | str] | Language | str | None = None,
                 validate: bool = False):
        """
        Represents the SHACL sh:languageIn datatype. This class validates input fully
        against provided language definitions, ensuring compliance with SHACL language
        requirements. The class accepts a variety of input formats, including
        individual language values, lists, sets, or tuples, and performs necessary
        checks to ensure all elements conform to the Language type or a valid string.

        :param args: A set of languages to be included in the LanguageIn instance.
        :type args: Self | set[Language | str] | list[Language | str] |
            tuple[Language | str] | Language | str
        :param value: An optional parameter used internally for serialization or
            deserialization purposes.
        :type value: Self | set[Language | str] | list[Language | str] |
            tuple[Language | str] | Language | str | None
        :param validate: Flag indicating whether validation checks should be applied
            on initialization.
        :type validate: bool
        :raises OldapErrorType: Raised if elements in an iterable, or provided value,
            are not an instance of "Language" or valid string representations thereof.
        :raises OldapErrorKey: Raised if a provided language string is not recognized
            or does not exist in the Language enum.
        """
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

    def __contains__(self, val: Language | str) -> bool:
        """
        Tests if the given language is contained in the given language set.

        This method is used to verify whether a specific language, represented by
        the `Language` type or its string equivalent, exists in the language set.
        If a string is provided, it converts the string to the corresponding
        `Language` enumeration before performing the containment check.

        :param val: Language to be tested
        :type val: Language | str
        :return: True if the given language is contained in the given language set.
        :rtype: bool
        """
        if not isinstance(val, Language):
            val = Language[str(val).upper()]
        return super().__contains__(val)

    def add(self, language: Language | Xsd_string | str) -> None:
        """
        Add a language to the given language set.

        This method attempts to add a language to the current set. If the input
        language is not an instance of the Language class, the method will
        attempt to convert the input to a Language instance using its string
        representation. Conversion errors are propagated as specific exceptions.

        :param language: The Language to be added to the given language set.
        :type language: Language | Xsd_string | str
        :return: None
        :rtype: None
        :raises OldapErrorValue: If conversion of the input to a Language fails
            due to invalid value.
        :raises OldapErrorKey: If conversion of the input to a Language fails
            due to an invalid key.
        """
        if not isinstance(language, Language):
            try:
                language = Language[str(language).upper()]
            except ValueError as err:
                raise OldapErrorValue(str(err))
            except KeyError as err:
                raise OldapErrorKey(str(err))
        super().add(language)

    def discard(self, language: Language | Xsd_string | str) -> None:
        """
        Remove a language from the given language set.

        This method attempts to discard a language from the language set. If `language`
        is not a member, it raises an OldapErrorValue exception.

        :param language: The Language to be removed from the given language set.
        :return: None
        :raises OldapErrorValue: If the given language is not contained in the given
            language set.
        """
        if not isinstance(language, Language):
            try:
                language = Language[str(language).upper()]
            except ValueError as err:
                raise OldapErrorValue(str(err))
        super().discard(language)

