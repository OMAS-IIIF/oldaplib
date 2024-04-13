from datetime import timedelta
from typing import Self

import isodate
from isodate import ISO8601Error
from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_duration(Xsd):
    """
    Implements the XML Schema [xsd:duration](https://www.w3.org/TR/xmlschema11-2/#duration) datatype
    """
    __value: timedelta

    def __init__(self, value: timedelta | Self | str):
        """
        Constructor of the Xsd_duration class.
        :param value: a Xsd_duration instance, or a timedelta instance, or a string for a timedelta
        in ISO8601 format.
        :type value: Self | timedelta | str
        :raises OmasErrorValue: if the value is not a valid timedelta
        """
        if isinstance(value, Xsd_duration):
            self.__value = value.__value
        elif isinstance(value, timedelta):
            self.__value = value
        else:
            try:
                self.__value = isodate.parse_duration(value)
            except ISO8601Error as err:
                raise OmasErrorValue(str(err))

    def __str__(self) -> str:
        """
        String representation of the Xsd_duration instance.
        :return: String representation
        """
        return isodate.duration_isoformat(self.__value)

    def __repr__(self) -> str:
        """
        Constructor string representation of the Xsd_duration instance.
        :return: Constructor string
        """
        return f'"{isodate.duration_isoformat(self.__value)}"^^xsd:duration'

    def __eq__(self, other: Self | timedelta | str | None) -> bool:
        """
        Compares two Xsd_duration instances for equality.
        :param other: Xsd_duration instance, a timedelta instance, or a string for a timedelta
        :type other: Self | timedelta | str | None
        :return: True or False
        :raise OmasErrorValue: if the value is not a valid timedelta
        """
        if other is None:
            return False
        if isinstance(other, Xsd_duration):
            return self.__value == other.__value
        if isinstance(other, timedelta):
            return self.__value == other
        else:
            try:
                other = isodate.parse_duration(str(other))
            except ISO8601Error as err:
                raise OmasErrorValue(str(err))
            return self.__value == other

    def __hash__(self) -> int:
        """
        Hash the Xsd_duration instance.
        :return: Hast value
        """
        return hash(self.__value)

    @property
    def toRdf(self) -> str:
        """
        Converts the Xsd_duration instance to a RDF string.
        :return: RDF string
        """
        return f'"{isodate.duration_isoformat(self.__value)}"^^xsd:duration'

    def _as_dict(self) -> dict:
        """
        Internal method to convert for JSON serialization. (@serializer decorater)
        :return:
        """
        return {'value': isodate.duration_isoformat(self.__value)}

    @property
    def value(self) -> timedelta:
        """
        Converts the Xsd_duration instance to a timedelta instance.
        :return: timedelta instance
        """
        return self.__value
