import re
from datetime import time
from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_time(Xsd):
    """
    Implements the XML Schema [xsd:time](https://www.w3.org/TR/xmlschema11-2/#time) datatype
    """
    __value: time

    __pattern = r'^([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]|60)(\.\d+)?(Z|[+-]([01][0-9]|2[0-3]):[0-5][0-9])?$'

    def __init__(self, value: time | Self | str):
        """
        Constructor for the Xsd_time class
        :param value: Either a Xsd_time instance, a Python time object, or a valid string representing a time
        :type value: Xsd_time | time | str
        :raises OmasErrorValue: If the value is not a valid time
        """
        if isinstance(value, Xsd_time):
            self.__value = value.__value
        elif isinstance(value, time):
            self.__value = value
        else:
            if re.match(self.__pattern, value) is None:
                raise OmasErrorValue(f'{value} wrong format for xsd:time.')
            try:
                self.__value = time.fromisoformat(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))

    def __str__(self) -> str:
        """
        String representation of the Xsd_time instance in ISO 8601 format
        :return: String representation of the Xsd_time instance in ISO 8601 format
        :rtype: str
        """
        return self.__value.isoformat()

    def __repr__(self) -> str:
        """
        Python constructor string representation of the Xsd_time instance in ISO 8601 format
        :return: Python constructor string representation of the Xsd_time instance in ISO 8601 format
        :rtype: str
        """
        return f'Xsd_time("{self.__value.isoformat()}")'

    def __eq__(self, other: Self | time | str | None) -> bool:
        """
        Equality check for Xsd_time instance
        :param other: An Xsd_time instance, a Python time object, or a valid string representing a time
        :type other: Xsd_time | time | str | None
        :return: True or False
        :rtype: bool
        :raises OmasErrorValue: If the value is not a valid time
        """
        if other is None:
            return False
        if isinstance(other, Xsd_time):
            return self.__value == other.__value
        if isinstance(other, time):
            return self.__value == other
        if isinstance(other, str):
            if re.match(self.__pattern, other) is None:
                raise OmasErrorValue(f'{other} wrong format for xsd:time.')
            other = time.fromisoformat(other)

    def __hash__(self) -> int:
        """
        Hash representation of the Xsd_time instance in ISO 8601 format
        :return: Hash value
        """
        return hash(str(self))

    def _as_dict(self) -> dict:
        """
        Internal method for serialization to JSON (@serializer decorator)
        :return:
        """
        return {'value': self.__value.isoformat()}

    @property
    def toRdf(self) -> str:
        """
        RDF representation of the Xsd_time instance in ISO 8601 format
        :return: RDF representation of the Xsd_time instance in ISO 8601 format
        :rtype: str
        """
        return f'"{self.__value.isoformat()}"^^xsd:time'

    @property
    def value(self) -> time:
        """
        Time value as Python time object
        :return: Python time value
        """
        return self.__value
