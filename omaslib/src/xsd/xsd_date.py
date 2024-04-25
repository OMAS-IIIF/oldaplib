import re
from datetime import date, time, datetime
from typing import Self, Optional

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_date(Xsd):
    """
    Implements the XSD Schema [xsd:date](https://www.w3.org/TR/xmlschema11-2/#date) datatype
    """
    __value: date

    def __init__(self, value: date | Self | str | int, month: int | None = None, day: int | None = None):
        """
        Constructor of a Xsd_date object
        :param value: Either the year as int, or an ISO date string, or a Python date value, or a Xsd_date instance
        :type value: date | Self | str | int
        :param month: The month number in the range 1-12 [optional]
        :type month: int
        :param day: The day number in the range 1-31 [optional]
        :type day: int
        :raises OmasErrorValue: If the string passed is not a valid ISO date string
        """
        if isinstance(value, Xsd_date):
            self.__value = value.__value
        elif isinstance(value, date):
            self.__value = value
        elif isinstance(value, int) and isinstance(month, int) and isinstance(day, int):
            if month < 1 or month > 12:
                raise OmasErrorValue(f'({value}, {month}, {day}) wrong format for xsd:date.')
            if day < 1 or day > 31:
                raise OmasErrorValue(f'({value}, {month}, {day}) wrong format for xsd:date.')
            self.__value = date(value, month, day)
        else:
            if re.match(r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$', str(value)) is None:
                raise OmasErrorValue(f'"{value}" wrong format for xsd:date – correct format is "yyyy-mm-dd" .')
            try:
                self.__value = date.fromisoformat(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))

    def __str__(self) -> str:
        """
        String representation of the Xsd_date object as ISO date string
        :return: string
        """
        return self.__value.isoformat()

    def __repr__(self) -> str:
        """
        String representation of the Xsd_date object as ISO date string
        :return: string
        """
        return f'Xsd_date("{self.__value.isoformat()}")'

    def __str2date(self, value: str) -> date:
        """
        Internal method for converting a string to a Python date object
        :param value: Date string
        :return: Python date instance
        :raises OmasErrorValue: If the input string is not a valid date string
        """
        if re.match(r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$', str(value)) is None:
            raise OmasErrorValue(f'{value} wrong format for xsd:date.')
        return date.fromisoformat(str(value))

    def __eq__(self, other: Self | date | str | None) -> bool:
        """
        Equality check for Xsd_date object
        :param other: another Xsd_date object or ISO string
        :type other: Xsd_date | date | str | None
        :return: True or False
        :raises OmasErrorValue: If the input string is not a valid date string
        """
        if other is None:
            return False
        if isinstance(other, Xsd_date):
            return self.__value == other.__value
        if isinstance(other, date):
            return self.__value == other
        else:
            other = self.__str2date(str(other))
            return self.__value == other

    def __gt__(self, other: Self | date | str | None) -> bool:
        """
        Compare greater than for Xsd_date object
        :param other: Value to compare to
        :type other: Xsd_date | date | str | None
        :return: True or False
        :raises OmasErrorValue: If the input string is not a valid date string
        """
        if other is None:
            return False
        if isinstance(other, Xsd_date):
            return self.__value > other.__value
        if isinstance(other, date):
            return self.__value > other
        else:
            other = self.__str2date(str(other))
            return self.__value > other

    def __ge__(self, other: Self | date | str | None) -> bool:
        """
        Compare greater or equal than for Xsd_date object
        :param other: Value to compare to
        :type other: Xsd_date | date | str | None
        :return: True or False
        :raises OmasErrorValue: If the input string is not a valid date string
        """
        if other is None:
            return False
        if isinstance(other, Xsd_date):
            return self.__value >= other.__value
        if isinstance(other, date):
            return self.__value >= other
        else:
            other = self.__str2date(str(other))
            return self.__value >= other

    def __lt__(self, other: Self | str | None) -> bool:
        """
        Compare less than for Xsd_date object
        :param other: Value to compare to
        :type other: Xsd_date | date | str | None
        :return: True or False
        :raises OmasErrorValue: If the input string is not a valid date string
        """
        if other is None:
            return False
        if isinstance(other, Xsd_date):
            return self.__value < other.__value
        if isinstance(other, date):
            return self.__value < other
        else:
            other = self.__str2date(str(other))
            return self.__value < other

    def __le__(self, other: Self | str | None) -> bool:
        """
        Compare less or equal than for Xsd_date object
        :param other: Value to compare to
        :return: True or False
        :raises OmasErrorValue: If the input string is not a valid date string
        """
        if other is None:
            return False
        if isinstance(other, Xsd_date):
            return self.__value <= other.__value
        if isinstance(other, date):
            return self.__value <= other
        else:
            other = self.__str2date(str(other))
            return self.__value <= other

    def __hash__(self) -> int:
        """
        Internal method for hashing Xsd_date object
        :return: Hash value
        """
        return hash(self.__value)

    def _as_dict(self) -> dict:
        """
        Internal method for converting Xsd_date for the JSON serialization
        :return: dict
        """
        return {'value': self.__value.isoformat()}

    @property
    def toRdf(self) -> str:
        """
        Internal method for converting Xsd_date for the RDF serialization
        :return: RDF string
        """
        return f'"{self.__value.isoformat()}"^^xsd:date'

    @property
    def value(self) -> date:
        """
        Return the internal date instance
        :return: date
        """
        return self.__value

    @classmethod
    def now(cls):
        """
        Create a instance with the current date
        :return: Instance of the Xsd_date object
        """
        return cls(datetime.now().date())
