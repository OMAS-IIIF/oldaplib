import re
from typing import Self

from pystrict import strict

from oldaplib.src.enums.language import Language
from oldaplib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd


#@strict
@serializer
class Xsd_language(Xsd):
    """
    Implements the [xsd:language](https://www.w3.org/TR/xmlschema11-2/#language) datatype,
    which is used to define human language tags
    conforming to [IETF BCP 47](https://en.wikipedia.org/wiki/IETF_language_tag).
    It supports a format based on RFC 4646 language tags,
    typically composed of primary language subtags optionally followed by subtags
    denoting country, region, or variant.
    """
    __value: str

    def __init__(self, value: Self | Language | str, validate: bool = False):
        """
        Constructs a new Xsd_language instance. It checks if the syntax is valid, but it does
        not test if the language tag is a valid language!
        :param value: Either a Xsd_language or a Language instance, or a string representing the language
        short name.
        :type value: Xsd_language | Language | str
        :raises ValueError: If the syntax is invalid.
        """
        if isinstance(value, Xsd_language):
            self.__value = value.__value
        elif isinstance(value, Language):
            self.__value = value.name.lower()
        else:
            if validate:
                if not XsdValidator.validate(XsdDatatypes.language, value):
                    raise OldapErrorValue(f'Invalid string "{value}" for xsd:language.')
                if not re.match('^[a-zA-Z]{2}(-[a-zA-Z]{2})?$', value):
                    raise OldapErrorValue(f'Invalid string "{value}" for xsd:language.')
            self.__value = value

    def __str__(self):
        """
        Returns the string representation of the Xsd_language instance.
        :return:
        """
        return self.__value

    def __repr__(self):
        """
        Returns the constructor string representation of the Xsd_language instance.
        :return:
        """
        return f'Xsd_language("{self.__value}")'

    def __eq__(self, other: Self | str | None) -> bool:
        """
        Checks if the Xsd_language instance is equal to the other Xsd_language instance.
        :param other: A Xsd_language instance.
        :return: True or False
        :rtype: bool
        :raises OldapErrorValue: If the syntax is invalid.
        """
        if other is None:
            return False
        if isinstance(other, Xsd_language):
            return self.__value == other.__value
        if isinstance(other, Language):
            other = other.name.lower()
        else:
            other = Xsd_language(other)
        return self.__value == other

    def __hash__(self) -> int:
        """
        Returns the hash of the Xsd_language instance.
        :return: Hash value
        :rtype: int
        """
        return hash(self.__value)

    def _as_dict(self) -> dict[str, str]:
        """
        Internal method used for JSON serialization (@serializer decorator)
        :return: dict
        """
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        """
        Returns the Xsd_language instance as a RDF string.
        :return: RDF string
        :rtype: str
        """
        return f'"{self.__value}"^^xsd:language'

