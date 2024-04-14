import re
from typing import Self

from pystrict import strict

from omaslib.src.xsd.xsd_string import Xsd_string
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_Name(Xsd):
    """
    Implements the XML Schema [xsd:Name](https://www.w3.org/TR/xmlschema11-2/#Name) datatype
    """
    __value: str

    def __init__(self, value: Self | str):
        """
        Constructs an Xsd_Name instance.
        :param value: An Xsd_Name instance or a string conforming to the XML Schema [xsd:Name]
        :raises OmasErrorValue: If an invalid value is passed.
        """
        if isinstance(value, Xsd_Name):
            self.__value = value.__value
        else:
            if not re.match("^[a-zA-Z_][\\w.\\-:_]*$", value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:Name.')
            self.__value = value

    @classmethod
    def fromRdf(cls, value: str) -> Self:
        """
        Constructs an Xsd_Name instance from a RDF string.
        :param value: An RDF string conforming to the XML Schema [xsd:Name]
        :type value: str
        :return: an Xsd_Name instance.
        :rtype: Xsd_Name
        """
        value = Xsd_string.unescaping(value)
        return cls(value)

    def __str__(self):
        """
        Returns the string representation of the Xsd_Name instance.
        :return: String representation of the Xsd_Name instance.
        :rtype: str
        """
        return self.__value

    def __repr__(self):
        """
        Returns the constructor string representation of the Xsd_Name instance.
        :return: Constructor string representation of the Xsd_Name instance.
        :rtype: str
        """
        return f'Xsd_Name("{self.__value}")'

    def __eq__(self, other: Self | str | None) -> bool:
        """
        Returns true if the Xsd_Name instance is equal to the other Xsd_Name instance.
        :param other: An other Xsd_Name instance.
        :return: True or False
        :rtype: bool
        :raises OmasErrorValue: If an invalid value is passed.
        """
        if other is None:
            return False
        if isinstance(other, Xsd_Name):
            return self.__value == other.__value
        else:
            return self.__value == other

    def __hash__(self) -> int:
        """
        Returns the hash value of the Xsd_Name instance.
        :return: Hash value of the Xsd_Name instance.
        :rtype: int
        """
        return hash(self.__value)

    def _as_dict(self) -> dict[str, str]:
        """
        Internal method to serialize the Xsd_Name instance to JSON (@serializer decorator).
        :return: dict
        """
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        """
        Returns the string representation of the Xsd_Name instance.
        :return: RDF string representation of the Xsd_Name instance.
        :rtype: str
        """
        return f'"{Xsd_string.escaping(self.__value)}"^^xsd:Name'

    @property
    def value(self) -> str:
        """
        Returns the string representation of the Xsd_Name instance.
        :return: String representation of the Xsd_Name instance.
        :rtype: str
        """
        return self.__value
