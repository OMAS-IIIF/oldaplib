from typing import Any, Self, Dict

from pystrict import strict

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd


#@strict
@serializer
class Xsd_boolean(Xsd):
    """
    Implements the XML Schema [xsd:boolean](https://www.w3.org/TR/xmlschema11-2/#boolean) datatype
    """
    __value: bool

    def __init__(self, value: Any, validate: bool = True):
        """
        Constructor of Xsd_boolean
        :param value: Any value that can be interpreted as boolean
        :type value: Any
        :param validate: Boolean value that determines whether or not the value should be validated (not used!)
        :raises OldapErrorValue: If the value is not a boolean
        """
        if isinstance(value, str):
            if value.lower() in ('yes', 'true', 't', 'y', '1'):
                self.__value = True
            elif value.lower() in ('no', 'false', 'f', 'n', '0'):
                self.__value = False
            else:
                raise OldapErrorValue('No valid string for boolean value.')
        else:
            self.__value = bool(value)

    def __str__(self) -> str:
        """
        String representation of Xsd_boolean
        :return: string
        :rtype: str
        """
        return str(self.__value).lower()

    def __repr__(self) -> str:
        """
        String representation of Xsd_boolean as constructor
        :return: string
        :rtype: str
        """
        return f"Xsd_boolean('{str(self.__value).lower()}')"

    def __bool__(self) -> bool:
        """
        Boolean representation of Xsd_boolean
        :return: bool
        :rtype: bool
        """
        return self.__value

    def __eq__(self, other: Any | None) -> bool:
        """
        Equality check for Xsd_boolean
        :param other: Value to compare with
        :type other: Any
        :return: True or False
        :rtype: bool
        """
        if other is None:
            return False
        if not isinstance(other, Xsd_boolean):
            other = Xsd_boolean(other)
        return self.__value == other.__value

    @property
    def toRdf(self) -> str:
        """
        String representation of Xsd_boolean for RDF representation
        :return: string for RDF
        :rtype: str
        """
        return f'"{str(self.__value).lower()}"^^xsd:boolean'

    @classmethod
    def fromRdf(cls, rdf: str) -> Self:
        return cls(rdf)

    def _as_dict(self) -> dict[str, str]:
        """
        Used internally for JSON serialization using @serialisation decorator
        :return: dict
        :rtype: dict[str, str]
        """
        return {'value': str(self.__value)}

    @property
    def value(self) -> bool:
        """
        Boolean representation of Xsd_boolean
        :return: bool
        """
        return self.__value
