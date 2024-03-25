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
    __value: timedelta

    def __init__(self, value: timedelta | Self | str):
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
        return isodate.duration_isoformat(self.__value)

    def __repr__(self) -> str:
        return f'"{isodate.duration_isoformat(self.__value)}"^^xsd:duration'

    def __eq__(self, other: Self | str | None) -> bool:
        if other is None:
            return False
        if isinstance(other, str):
            other = isodate.parse_duration(other)
        return self.__value == other.__value

    def __hash__(self) -> int:
        return hash(self.__value)

    @classmethod
    def from_dict(cls, value: str) -> Self:
        return cls(isodate.parse_duration(value))

    @property
    def toRdf(self) -> str:
        return f'"{isodate.duration_isoformat(self.__value)}"^^xsd:duration'

    def _as_dict(self) -> dict:
        return {'value': isodate.duration_isoformat(self.__value)}

    @property
    def value(self) -> timedelta:
        return self.__value
