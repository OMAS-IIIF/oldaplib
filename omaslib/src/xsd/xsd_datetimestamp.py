import re
from datetime import datetime
from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_dateTimeStamp(Xsd):
    """
    Implements the XML Schema [xsd:dateTimeStamp](https://www.w3.org/TR/xmlschema11-2/#dateTimeStamp) datatype
    """
    __value: datetime

    def __init__(self, value: datetime | Self | str):
        """
        Constructor for the Xsd_dateTimeStamp instance
        :param value: A Xsd_dateTimeStamp instance, or a datetime object or a string
        containing a datetimestmp in OS format
        :type value: datetime | Self | str
        :raises OmasErrorValue: If the value is not a datetimestamp object
        """
        if isinstance(value, Xsd_dateTimeStamp):
            self.__value = value.__value
        elif isinstance(value, datetime):
            self.__value = value
        else:
            if re.match(
                    r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]|60)(\.\d+)?(Z|[+-]([01][0-9]|2[0-3]):[0-5][0-9])$',
                    value) is None:
                raise OmasErrorValue(f'DateTimeStamp "{value}" not a valid ISO 8601.')
            try:
                self.__value = datetime.fromisoformat(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))

    def __str__(self) -> str:
        """
        String representation of the Xsd_dateTimeStamp instance as ISO datetimestamp
        :return:
        """
        return self.__value.isoformat()

    def __repr__(self) -> str:
        """
        Constructor string representation of the Xsd_dateTimeStamp instance as ISO datetimestamp
        :return: Constructor string
        """
        return f'Xsd_dateTimeSTamp("{self.__value.isoformat()}")'

    def __eq__(self, other: Self | datetime | str | None) -> bool:
        """
        Equality check of the Xsd_dateTimeStamp instance with another value
        :param other: A Xsd_dateTimeStamp instance, or a datetime object or a string, or None
        :type other: Xsd_dateTimeStamp | datetime | str | None
        :return: True of False
        :raise OmasErrorValue: If the value is not a valid datetimestamp object
        """
        if other is None:
            return False
        if isinstance(other, Xsd_dateTimeStamp):
            return self.__value == other.__value
        if isinstance(other, datetime):
            return self.__value == other
        else:
            if re.match(
                    r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]|60)(\.\d+)?(Z|[+-]([01][0-9]|2[0-3]):[0-5][0-9])$',
                    other) is None:
                raise OmasErrorValue(f'DateTimeStamp "{other}" not a valid ISO 8601.')
            other = datetime.fromisoformat(other)
            return self.__value == other

    def __hash__(self) -> int:
        """
        Hashing of the Xsd_dateTimeStamp instance
        :return: Hash value
        """
        return hash(self.__value)

    def _as_dict(self) -> dict:
        """
        Internal method for the JSON serialization (@serializer decorator)
        :return: dict
        """
        return {'value': self.__value.isoformat()}

    @property
    def toRdf(self) -> str:
        """
        Converts the Xsd_dateTimeStamp instance to a RDF string
        :return: RDF string
        """
        return f'"{self.__value.isoformat()}"^^xsd:dateTimeStamp'

    @property
    def value(self) -> datetime:
        """
        Converts the Xsd_dateTimeStamp instance to a datetimestamp object
        :return: datetimestamp object
        """
        return self.__value
