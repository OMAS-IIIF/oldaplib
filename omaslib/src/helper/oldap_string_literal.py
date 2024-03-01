from typing import Optional, Self

from pystrict import strict

from omaslib.src.enums.language import Language
from omaslib.src.helpers.serializer import serializer


@strict
@serializer
class OldapStringLiteral:
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

    def __init__(self, value: str, lang: Optional[str | Language] = None):
        """
        Constructor of OldapStringLiteral.
        :param value: String value
        :type value: str
        :param lang: Language the sting is in [optional]
        :type lang: str | Language
        """
        self.__value = value
        if isinstance(lang, Language):
            self.__lang = lang
        else:
            self.__lang = Language[lang.upper()] if lang else None

    @classmethod
    def fromRdf(cls, value: str, lang: Optional[str] = None):
        """
        Constructor of OldapStringLiteral that takes a RDF/SPARQL representation of the string and un-escapes it
        :param value: String from RDF/SPARQL representation
        :type value: str
        :param lang: Language ISO short (lowercased) [optional]
        :type lang: str
        :return: OldapStringLiteral instance
        :rtype: OldapStringLiteral
        """
        value = OldapStringLiteral.escaping(value)
        return cls(value, lang)

    def __str__(self) -> str:
        """
        Returns the string representation of the OldapStringLiteral instance with the languages appended "@ll"
        :return: Language string
        :rtype: str
        """
        if self.__lang:
            return f'{self.__value}@{self.__lang.name.lower()}'
        else:
            return self.__value

    def __repr__(self) -> str:
        """
        Returns the OldapStringLiteral instance as string as used in a RDF/SPARQL representation
        :return: SPARQL/RDF/TRIG representation of the language string
        :rtype: str
        """
        if self.__lang:
            return f'"{OldapStringLiteral.escaping(self.__value)}"@{self.__lang.name.lower()}'
        else:
            return f'"{self.__value}"'

    def __eq__(self, other: str | Self) -> bool:
        """
        Check for equality of two OldapStringLiterals (both strings and languages must be equal)
        :param other: Other OldapStringLiteral
        :type other: OldapStringLiteral
        :return: True or False
        :rtype: bool
        """
        if isinstance(other, OldapStringLiteral):
            return self.__value == other.__value and self.__lang == other.__lang
        elif isinstance(other, str):
            return self.__value == other

    def __hash__(self) -> int:
        """
        Returns the OldapStringLiteral hash value as an integer
        :return: Hast value
        :rtype: int
        """
        if self.__lang:
            return hash(self.__value + '@' + self.__lang.value)
        else:
            return hash(self.__value)

    def _as_dict(self) -> dict:
        """
        Used for the JSON serializer
        :return: Dictionary representation of the OldapStringLiteral
        :rtype: Dict[str,str]
        """
        return {
                "value": self.__value,
                "lang": self.__lang
        }

    @property
    def value(self) -> str:
        """
        Returns the OldapStringLiteral string value only
        :return: string representation of the OldapStringLiteral without language
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
        return self.__lang
