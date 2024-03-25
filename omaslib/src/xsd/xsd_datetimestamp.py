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
    __value: datetime

    def __init__(self, value: datetime | Self | str):
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
        return self.__value.isoformat()

    def __repr__(self) -> str:
        return f'Xsd_dateTimeSTamp("{self.__value.isoformat()}")'

    def __eq__(self, other: Self | str | None) -> bool:
        if other is None:
            return False
        if isinstance(other, str):
            if re.match(
                    r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]|60)(\.\d+)?(Z|[+-]([01][0-9]|2[0-3]):[0-5][0-9])$',
                    other) is None:
                raise OmasErrorValue(f'DateTimeStamp "{other}" not a valid ISO 8601.')
            other = datetime.fromisoformat(other)
        elif isinstance(other, Xsd_dateTimeStamp):
            return self.__value == other.__value
        else:
            raise OmasErrorValue(f'Cannot not compare to "{type(other).__name__}"')

    def __hash__(self) -> int:
        return hash(self.__value)

    def _as_dict(self) -> dict:
        return {'value': self.__value.isoformat()}

    @property
    def toRdf(self) -> str:
        return f'"{self.__value.isoformat()}"^^xsd:dateTimeStamp'

    @property
    def value(self) -> datetime:
        return self.__value
