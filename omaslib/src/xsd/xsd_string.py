from typing import Optional, Self
from pystrict import strict

from omaslib.src.enums.language import Language
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_string(Xsd):
    """
    Implements the XML Schema [xsd:string(https://www.w3.org/TR/xmlschema11-2/#string)] datatype.

    This class implements the handling of a single RDF/TRIG string that may have a language tag. It is
    serializable and manages the escaping/un-escaing of strings transfered to the triple store. This is
    an important part of the security conecpt of OLDAP.

    **No used-defined string may enter the triple store without being properly escaped to prevent
    SPARQL-injection!**

    The class implements the following methods:

    - `escaping(value: str)`: A static method that escapes a string
    - `unescaping(value: str)`: A static method that un-escapes a string
    - `Xsd_string(value: str, lang: Optional[str | Language] = None)`: Constructor with an optional
      language. The Language can be given either as [Language](/python_docstrings/language) enum or as
      2-letter ISO 639-1 language.
    - `fromRdf(value: str)`: A static constructor method that is used to convert an RDF/TRIG based string. It
      un-escapes the string retrieved from the triple store! This constructor is used by the
      [QueryProcessor](/python_docstrings/query_processor) class.
    - `str(Xsd_string)`: Returns a string with the langauge tag appended as `@ll`
      (ll as the 2-letter ISO languages), e.g. `'dies ist deutsch@de'`
    - `repr(Xsd_string)`: Returns a string with the langauge tag as it is beeiing used in TRIG/SPARQL
      queries, e.g. `'"dies ist deutsch"@de'`
    - `value`: Property returning the string value (without language tag)
    - `lang`: Property returning the language tag
    """
    __value: str
    __lang: Language | None

    @staticmethod
    def escaping(value: str) -> str:
        """
        Escape the given string to be suitable to be used in an RDF/SPARQL representation
        :param value: String ti be escaped
        :type value: str
        :return: Escaped string
        :rtype: str
        """
        value = value.replace('\\', '\\\\')
        value = value.replace("'", "\\'")
        value = value.replace('"', '\\"')
        value = value.replace('\n', '\\n').replace('\r', '\\r')
        return value

    @staticmethod
    def unescaping(value: str) -> str:
        """
        Unescape the given string
        :param value: Escaped string
        :type value: str
        :return: Unescpaed string
        :rtype: str
        """
        value = value.replace('\\\\', '\\')
        value = value.replace("\\'", "'")
        value = value.replace('\\"', '"')
        value = value.replace('\\n', '\n').replace('\\r', '\r')
        return value

    def __init__(self, value: Self | str, lang: str | Language | None = None):
        """
        Constructor of Xsd_string.
        :param value: String value
        :type value: str
        :param lang: Language the sting is in [optional]
        :type lang: str | Language
        :raises OmasErrorValue: If the given language is invalid
        """
        if isinstance(value, Xsd_string):
            self.__value = value.__value
            self.__lang = value.__lang
        else:
            self.__value = str(value)
            if lang is None:
                self.__lang = Language.XX
            if isinstance(lang, Language):
                self.__lang = lang
            else:
                try:
                    self.__lang = Language[lang.upper()] if lang else None
                except (ValueError, KeyError) as err:
                    raise OmasErrorValue(str(err))

    @classmethod
    def fromRdf(cls, value: str, lang: Optional[str] = None):
        """
        Constructor of Xsd_string that takes a RDF/SPARQL representation of the string and un-escapes it
        :param value: String from RDF/SPARQL representation
        :type value: str
        :param lang: Language ISO short (lowercased) [optional]
        :type lang: str
        :return: OldapStringLiteral instance
        :rtype: StringLiteral
        """
        value = Xsd_string.unescaping(value)
        return cls(value, lang)

    def __str__(self) -> str:
        """
        Returns the string representation of the Xsd_string instance with the languages appended "@ll"
        :return: Language string
        :rtype: str
        """
        if self.__lang and self.__lang != Language.XX:
            return f'{self.__value}@{self.__lang.name.lower()}'
        else:
            return self.__value

    def __repr__(self) -> str:
        """
        Returns the Xsd_string instance as string as used in a RDF/SPARQL representation
        :return: SPARQL/RDF/TRIG representation of the language string
        :rtype: str
        """
        if self.__lang and self.__lang != Language.XX:
            return f'Xsd_string("{self.__value}", "{self.__lang.name.lower()}")'
        else:
            return f'Xsd_string("{self.__value}")'

    def __eq__(self, other: str | Self | None) -> bool:
        """
        Check for equality of two Xsd_strings (both strings and languages must be equal)
        :param other: Other OldapStringLiteral
        :type other: StringLiteral
        :return: True or False
        :rtype: bool
        """
        if other is None:
            return False
        if isinstance(other, Xsd_string):
            return self.__value == other.__value and self.__lang == other.__lang
        elif isinstance(other, str):
            return self.__value == str(other)

    def __ne__(self, other: str | Self | None) -> bool:
        """
        Check for inequality of two Xsd_strings (both strings and languages must be equal)
        :param other: An Xsd_string or a string value
        :type other: Xsd_string
        :return: True or False
        :rtype: bool
        """
        if other is None:
            return True
        if isinstance(other, Xsd_string):
            return self.__value != other.__value and self.__lang == other.__lang
        elif isinstance(other, str):
            return self.__value != other

    def __getitem__(self, key: int | slice) -> str | None:
        """
        Get the character(s) at the given position (slicing or indexing supported).
        :param key: Index or slice
        :type key: int | slice
        :return: Character or slice as string
        :rtype: str | None
        """
        return self.__value[key]

    def __hash__(self) -> int:
        """
        Returns the Xsd_string hash value as an integer
        :return: Hash value
        :rtype: int
        """
        if self.__lang and self.__lang != Language.XX:
            return hash(self.__value + '@' + self.__lang.value)
        else:
            return hash(self.__value)

    @property
    def toRdf(self):
        """
        RDF representation of the Xsd_string instance
        :return: RDF representation of the Xsd_string instance
        :rtype: str
        """
        if self.__lang and self.__lang != Language.XX:
            return f'"{Xsd_string.escaping(self.__value)}"@{self.__lang.name.lower()}'
        else:
            return f'"{Xsd_string.escaping(self.__value)}"^^xsd:string'

    def _as_dict(self) -> dict:
        """
        Used for the JSON serializer (@serializer decorator)
        :return: Dictionary representation of the OldapStringLiteral
        :rtype: dict
        """
        return {
                "value": self.__value,
                "lang": self.__lang
        }

    @property
    def value(self) -> str:
        """
        Returns the Xsd_string string value only
        :return: string representation of the Xsd_string without language
        :rtype: str
        """
        return self.__value

    @property
    def lang(self) -> Language | None:
        """
        Returns the Language if available (or None
        :return: Language
        :rtype: Language | None
        """
        return self.__lang if self.__lang != Language.XX else None
