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
    __value: date

    def __init__(self, value: date | Self | str | int, month: Optional[int] = None, day: Optional[int] = None):
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
            if re.match(r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$', value) is None:
                raise OmasErrorValue(f'{value} wrong format for xsd:date.')
            try:
                self.__value = date.fromisoformat(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))

    def __str__(self) -> str:
        return self.__value.isoformat()

    def __repr__(self) -> str:
        return f'Xsd_date("{self.__value.isoformat()}")'

    def __eq__(self, other: Self | str | None) -> bool:
        if other is None:
            return False
        if isinstance(other, str):
            if re.match(
                    r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$', other) is None:
                raise OmasErrorValue(f'{other} wrong format for xsd:date.')
            other = time.fromisoformat(other)
        return self.__value == other.__value

    def __hash__(self) -> int:
        return hash(self.__value)

    def _as_dict(self) -> dict:
        return {'value': self.__value.isoformat()}

    @property
    def toRdf(self) -> str:
        return f'"{self.__value.isoformat()}"^^xsd:date'

    @property
    def value(self) -> date:
        return self.__value

    @classmethod
    def now(cls):
        return cls(datetime.now().date())
