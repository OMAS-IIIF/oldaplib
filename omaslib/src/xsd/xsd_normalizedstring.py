import re
from typing import Self

from pystrict import strict

from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_string import Xsd_string


@strict
@serializer
class Xsd_normalizedString(Xsd):
    """
    Implements the XML Schema [xsd:normalizedstring](https://www.w3.org/TR/xmlschema11-2/#normalizedString) datatype.
    """
    __value: str

    def __init__(self, value: Self | str):
        """
        Constructor for Xsd_normalizedString class
        :param value: Another instance of the Xsd_normalizedString class or a valid string
        :type value: Xsd_normalizedString | str
        :raises OmasErrorValue: If the value is not a valid.
        """
        if isinstance(value, Xsd_normalizedString):
            self.__value = value.__value
        else:
            if not XsdValidator.validate(XsdDatatypes.normalizedString, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:normalizedString.')
            if re.match("^[^\r\n\t]*$", value) is None:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:normalizedString.')
            self.__value = value

    @classmethod
    def fromRdf(cls, value: str) -> Self:
        """
        Constructor for Xsd_normalizedString class based on a RDF string representation
        :param value: RDF string representation (without type specifier "^^xsd:normalizedString")
        :type value: str
        :return: Xsd_normalizedString instance
        :rtype: Xsd_normalizedString
        """
        value = Xsd_string.unescaping(value)
        return cls(value)

    def __str__(self):
        """
        Returns the string representation of the Xsd_normalizedString instance
        :return: String representation of the Xsd_normalizedString instance
        :rtype: str
        """
        return self.__value

    def __repr__(self):
        """
        Returns the Python constructor string representation of the Xsd_normalizedString instance
        :return: Python constructor string representation of the Xsd_normalizedString instance
        :rtype: str
        """
        return f'{type(self).__name__}("{self.__value}")'

    def __eq__(self, other: Self | str | None) -> bool:
        """
        Compares two Xsd_normalizedString instances.
        :param other: A Xsd_normalizedString instance or a valid string
        :return: True or False
        :rtype: bool
        :raises OmasErrorValue: If the value is not a valid.
        """
        if other is None:
            return False
        if not isinstance(other, Xsd_normalizedString):
            other = Xsd_normalizedString(other)
        return self.__value == other.__value

    def __hash__(self) -> int:
        """
        Returns the hash of the Xsd_normalizedString instance
        :return: Hash of the Xsd_normalizedString instance
        :rtype: int
        """
        return super().__hash__()

    @property
    def toRdf(self) -> str:
        """
        RDF string representation of the Xsd_normalizedString instance
        :return: RDF string representation of the Xsd_normalizedString instance
        :rtype: str
        """
        return f'"{Xsd_string.escaping(str(self))}"^^xsd:normalizedString'

    def _as_dict(self) -> dict[str, str]:
        """
        Internal method used for JSON serialization (@serializer decorator)
        :return: dict
        """
        return {'value': self.__value}

    @property
    def value(self) -> str:
        """
        Returns the string representation of the Xsd_normalizedString instance
        :return: String representation of the Xsd_normalizedString instance
        :rtype: str
        """
        return self.__value
