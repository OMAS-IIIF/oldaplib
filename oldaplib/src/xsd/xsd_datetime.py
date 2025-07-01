import re
from datetime import datetime
from typing import Self

from pystrict import strict

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd


#@strict
@serializer
class Xsd_dateTime(Xsd):
    """
    Implements the XML Schema [xsd:dateTime](https://www.w3.org/TR/xmlschema11-2/#dateTime) datatype
    """
    __value: datetime

    def __init__(self, value: datetime | Self | str | None = None, validate: bool = False):
        """
        Constructor of a Xsd_dateTime instance. If no value is given, `datetime.new()` will be used.
        :param value: a Xsd_dateTime instance, Python datetime
        object or a string representation of a datetime in ISO format, or None.
        If the parameter is None or omitted, the current datetime is used.
        :type value: datetime | Self | str | None
        :param validate: whether to validate the value before instantiation. Validtaion relies on regex pattern.
        :type validate: bool
        :raises OldapErrorValue: if the parameter cannot be converted to a datetime
        """
        if value is None:
            self.__value = datetime.now().astimezone()
        elif isinstance(value, Xsd_dateTime):
            self.__value = value.__value
        elif isinstance(value, datetime):
            self.__value = value
        else:
            if validate:
                if re.match(
                        r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]|60)(\.\d+)?(Z|[+-]([01][0-9]|2[0-3]):[0-5][0-9])?$',
                        value) is None:
                    raise OldapErrorValue(f'DateTime "{value}" not a valid ISO 8601.')
            try:
                self.__value = datetime.fromisoformat(value)
            except ValueError as err:
                raise OldapErrorValue(str(err))

    def __str__(self) -> str:
        """
        String representation of the Xsd_dateTime instance in ISO format
        :return: ISO string
        :rtype: str
        """
        return self.__value.isoformat()

    def __repr__(self) -> str:
        """
        String representation of the Xsd_dateTime instance in ISO format as constructor
        :return: Constructor string representation of the Xsd_dateTime instance in ISO format
        :rtype: str
        """
        return f'Xsd_dateTime("{self.__value.isoformat()}")'

    def __hash__(self) -> int:
        """
        Calculates the hash of the Xsd_dateTime instance
        :return: hash value
        :rtype: int
        """
        return hash(self.__value.isoformat())

    def __eq__(self, other: Self | str | None) -> bool:
        """
        Equality test for Xsd_dateTime instance
        :param other: Value to compare instance to
        :return: True or False
        :rtype: bool
        :raises OldapErrorValue: if the parameter cannot be converted to a datetime
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
                raise OldapErrorValue(f'DateTime "{other}" not a valid ISO 8601.')
            other = datetime.fromisoformat(other)
            return self.__value == other

    def _as_dict(self) -> dict:
        """
        Used internally for JSON serialization using @serialisation decorator
        :return: dict
        :rtype: dict
        """
        return {'value': self.__value.isoformat()}

    @property
    def toRdf(self) -> str:
        """
        Converts the Xsd_dateTime instance to a RDF string
        :return: RDF string
        :rtype: str
        """
        return f'"{self.__value.isoformat()}"^^xsd:dateTime'

    @property
    def value(self) -> datetime:
        """
        Converts the Xsd_dateTime instance to a Python datetime object and returns it
        :return: datetime object
        :rtype: datetime
        """
        return self.__value

    @classmethod
    def now(cls) -> Self:
        """
        Return a Xsd_dateTime instance set to now()
        :return: Xsd_dateTime instance
        :rtype: Xsd_dateTime
        """
        return cls(datetime.now().astimezone())
