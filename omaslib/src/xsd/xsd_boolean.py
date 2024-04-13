from typing import Any, Self, Dict

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_boolean(Xsd):
    """
    Implements the XML Schema [xsd:boolean](https://www.w3.org/TR/xmlschema11-2/#boolean) datatype
    """
    __value: bool

    def __init__(self, value: Any):
        """
        Constructor of Xsd_boolean
        :param value: Any value that can be interpreted as boolean
        :type value: Any
        :raises OmasErrorValue: If the value is not a boolean
        """
        if isinstance(value, str):
            if value.lower() in ('yes', 'true', 't', 'y', '1'):
                self.__value = True
            elif value.lower() in ('no', 'false', 'f', 'n', '0'):
                self.__value = False
            else:
                raise OmasErrorValue('No valid string for boolean value.')
        else:
            self.__value = bool(value)

    def __str__(self) -> str:
        """
        String representation of Xsd_boolean
        :return: string
        """
        return str(self.__value).lower()

    def __repr__(self) -> str:
        """
        String representation of Xsd_boolean as constructor
        :return:
        """
        return f"Xsd_boolean('{str(self.__value).lower()}')"

    def __bool__(self) -> bool:
        """
        Boolean representation of Xsd_boolean
        :return: bool
        """
        return self.__value

    def __eq__(self, other: Any | None) -> bool:
        """
        Equality check for Xsd_boolean
        :param other: Value to compare with
        :type other: Any
        :return: True or False
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
        """
        return f'"{str(self.__value).lower()}"^^xsd:boolean'

    def _as_dict(self) -> dict[str, str]:
        """
        Used internally for JSON serialization using @serialisation decorator
        :return: dict
        """
        return {'value': str(self.__value)}

    @property
    def value(self) -> bool:
        """
        Boolean representation of Xsd_boolean
        :return: bool
        """
        return self.__value
