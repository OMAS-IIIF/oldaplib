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
    __value: time

    def __init__(self, value: time | Self | str):
        if isinstance(value, Xsd_time):
            self.__value = value.__value
        elif isinstance(value, time):
            self.__value = value
        else:
            if re.match(
                    r'^([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]|60)(\.\d+)?(Z|[+-]([01][0-9]|2[0-3]):[0-5][0-9])?$',
                    value) is None:
                raise OmasErrorValue(f'{value} wrong format for xsd:time.')
            try:
                self.__value = time.fromisoformat(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))

    def __str__(self) -> str:
        return self.__value.isoformat()

    def __repr__(self) -> str:
        return f'Xsd_time("{self.__value.isoformat()}")'

    def __eq__(self, other: Self | str | None) -> bool:
        if other is None:
            return False
        if isinstance(other, str):
            if re.match(
                    r'^([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]|60)(\.\d+)?(Z|[+-]([01][0-9]|2[0-3]):[0-5][0-9])?$',
                    other) is None:
                raise OmasErrorValue(f'{other} wrong format for xsd:time.')
            other = time.fromisoformat(other)
        return self.__value == other.__value

    def __hash__(self) -> int:
        return hash(str(self))

    def _as_dict(self) -> dict:
        return {'value': self.__value.isoformat()}

    @property
    def toRdf(self) -> str:
        return f'"{self.__value.isoformat()}"^^xsd:time'

    @property
    def value(self) -> time:
        return self.__value
