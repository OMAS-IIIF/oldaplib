import re
from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_decimal(Xsd):
    __value: float

    def __init__(self, value: Self | float | str):
        if isinstance(value, Xsd_decimal):
            self.__value = value.__value
        else:
            if isinstance(value, str):
                if not re.match("^[+-]?[0-9]*\\.?[0-9]*$", value):
                    raise OmasErrorValue(f'"{value}" is not a xsd:decimal.')
            try:
                self.__value = float(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))

    def __str__(self) -> str:
        return str(self.__value)

    def __repr__(self) -> str:
        return f'Xsd_decimal("{str(self.__value)}")'

    def __eq__(self, other: Self | float | None) -> bool:
        if other is None:
            return False
        if isinstance(other, float):
            return self.__value == other
        elif isinstance(other, Xsd_decimal):
            return self.__value == other.__value
        else:
            raise OmasErrorValue(f'Cannot compare Xsd_decimal("{self._value}") to {type(other)}')

    def __ne__(self, other) -> bool:
        if isinstance(other, float):
            return self.__value != other
        elif isinstance(other, Xsd_decimal):
            return self.__value != other.__value
        else:
            raise OmasErrorValue(f'Cannot compare Xsd_decimal("{self._value}") to {type(other)}')

    def __lt__(self, other) -> bool:
        if isinstance(other, float):
            return self.__value < other
        elif isinstance(other, Xsd_decimal):
            return self.__value < other.__value
        else:
            raise OmasErrorValue(f'Cannot compare Xsd_decimal("{self._value}") to {type(other)}')

    def __le__(self, other) -> bool:
        if isinstance(other, float):
            return self.__value <= other
        elif isinstance(other, Xsd_decimal):
            return self.__value <= other.__value
        else:
            raise OmasErrorValue(f'Cannot compare Xsd_decimal("{self._value}") to {type(other)}')

    def __gt__(self, other) -> bool:
        if isinstance(other, float):
            return self.__value > other
        elif isinstance(other, Xsd_decimal):
            return self.__value > other.__value
        else:
            raise OmasErrorValue(f'Cannot compare Xsd_decimal("{self._value}") to {type(other)}')

    def __ge__(self, other) -> bool:
        if isinstance(other, float):
            return self.__value >= other
        elif isinstance(other, Xsd_decimal):
            return self.__value >= other.__value
        else:
            raise OmasErrorValue(f'Cannot compare Xsd_decimal("{self._value}") to {type(other)}')

    def __float__(self) -> float:
        return self.__value

    @property
    def toRdf(self) -> str:
        return f'"{self.__value}"^^xsd:decimal'

    def _as_dict(self) -> dict[str, float]:
        return {'value': self.__value}

    @property
    def value(self) -> float:
        return self.__value
