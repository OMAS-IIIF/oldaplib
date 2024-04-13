import re
from datetime import datetime
from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_dateTime(Xsd):
    """
    Implements the XML Schema [xsd:dateTime](https://www.w3.org/TR/xmlschema11-2/#dateTime) datatype
    """
    __value: datetime

    def __init__(self, value: datetime | Self | str | None = None):
        """
        Constructor of a Xsd_dateTime instance
        :param value: a Xsd_dateTime instance, Python datetime
        object or a string representation of a datetime in ISO format, or None.
        If the parameter is None or omitted, the current datetime is used.
        :type value: datetime | Self | str | None
        :raises OmasErrorValue: if the parameter cannot be converted to a datetime
        """
        if value is None:
            self.__value = datetime.now()
        elif isinstance(value, Xsd_dateTime):
            self.__value = value.__value
        elif isinstance(value, datetime):
            self.__value = value
        else:
            if re.match(
                    r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]|60)(\.\d+)?(Z|[+-]([01][0-9]|2[0-3]):[0-5][0-9])?$',
                    value) is None:
                raise OmasErrorValue(f'DateTime "{value}" not a valid ISO 8601.')
            try:
                self.__value = datetime.fromisoformat(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))

    def __str__(self) -> str:
        """
        String representation of the Xsd_dateTime instance in ISO format
        :return: ISO string
        """
        return self.__value.isoformat()

    def __repr__(self) -> str:
        """
        String representation of the Xsd_dateTime instance in ISO format as constructor
        :return: Constructor string representation of the Xsd_dateTime instance in ISO format
        """
        return f'Xsd_dateTime("{self.__value.isoformat()}")'

    def __eq__(self, other: Self | str | None) -> bool:
        """
        Equality test for Xsd_dateTime instance
        :param other: Value to compare instance to
        :return: True or False
        :raises OmasErrorValue: if the parameter cannot be converted to a datetime
        """
        if other is None:
            return False
        if isinstance(other, Xsd_dateTime):
            return self.__value == other.__value
        if isinstance(other, datetime):
            return self.__value == other
        else:
            if re.match(
                    r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]|60)(\.\d+)?(Z|[+-]([01][0-9]|2[0-3]):[0-5][0-9])?$',
                    str(other)) is None:
                raise OmasErrorValue(f'DateTime "{other}" not a valid ISO 8601.')
            other = datetime.fromisoformat(other)
            return self.__value == other

    def _as_dict(self) -> dict:
        """
        Used internall for JSON serialization (@serializer decorator)
        :return: dict
        """
        return {'value': self.__value.isoformat()}

    @property
    def toRdf(self) -> str:
        """
        Converts the Xsd_dateTime instance to a RDF string
        :return: RDF string
        """
        return f'"{self.__value.isoformat()}"^^xsd:dateTime'

    @property
    def value(self) -> datetime:
        """
        Converts the Xsd_dateTime instance to a Python datetime object and returns it
        :return: datetime object
        """
        return self.__value

    @classmethod
    def now(cls) -> Self:
        """
        Return a Xsd_dateTime instance set to now()
        :return: Xsd_dateTime instance
        """
        return cls(datetime.now())
