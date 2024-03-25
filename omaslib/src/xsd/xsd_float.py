import math
import re
from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_float(Xsd):
    __value: float

    def __init__(self, value: Self | float | str):
        if isinstance(value, Xsd_float):
            self.__value = value.__value
        else:
            if isinstance(value, str):
                if not re.match("^([-+]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][-+]?\\d+)?|[Nn]a[Nn]|[-+]?(inf|INF))$", value):
                    raise OmasErrorValue(f'"{value}" is not a xsd:float.')
            try:
                self.__value = float(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))

    def __str__(self) -> str:
        if math.isnan(self.__value):
            return 'NaN'
        elif math.isinf(self.__value):
            if self.__value < 0.0:
                return '-INF'
            else:
                return 'INF'
        else:
            return str(self.__value)

    def __repr__(self) -> str:
        if math.isnan(self.__value):
            return 'Xsd_float("NaN")'
        elif math.isinf(self.__value):
            if self.__value < 0.0:
                return 'Xsd_float("-INF")'
            else:
                return 'Xsd_float("INF")'
        else:
            return f'Xsd_float({self.__value})'

    def __eq__(self, other: Self | float | None) -> bool:
        if other is None:
            return False
        if isinstance(other, float):
            return self.__value == other
        elif isinstance(other, Xsd_float):
            return self.__value == other.__value
        else:
            raise OmasErrorValue(f'Cannot compare Xsd_decimal("{self.__value}") to {type(other)}')

    def __ne__(self, other) -> bool:
        if isinstance(other, float):
            return self.__value != other
        elif isinstance(other, Xsd_float):
            return self.__value != other.__value
        else:
            raise OmasErrorValue(f'Cannot compare Xsd_decimal("{self._value}") to {type(other)}')

    def __lt__(self, other) -> bool:
        if isinstance(other, float):
            return self.__value < other
        elif isinstance(other, Xsd_float):
            return self.__value < other.__value
        else:
            raise OmasErrorValue(f'Cannot compare Xsd_decimal("{self._value}") to {type(other)}')

    def __le__(self, other) -> bool:
        if isinstance(other, float):
            return self.__value <= other
        elif isinstance(other, Xsd_float):
            return self.__value <= other.__value
        else:
            raise OmasErrorValue(f'Cannot compare Xsd_decimal("{self._value}") to {type(other)}')

    def __gt__(self, other) -> bool:
        if isinstance(other, float):
            return self.__value > other
        elif isinstance(other, Xsd_float):
            return self.__value > other.__value
        else:
            raise OmasErrorValue(f'Cannot compare Xsd_decimal("{self._value}") to {type(other)}')

    def __ge__(self, other) -> bool:
        if isinstance(other, float):
            return self.__value >= other
        elif isinstance(other, Xsd_float):
            return self.__value >= other.__value
        else:
            raise OmasErrorValue(f'Cannot compare Xsd_decimal("{self._value}") to {type(other)}')

    def __hash__(self) -> int:
        return hash(self.__value)

    def __float__(self) -> float:
        return self.__value

    @property
    def toRdf(self) -> str:
        if math.isnan(self.__value):
            return '"NaN"^^xsd:float'
        elif math.isinf(self.__value):
            if self.__value < 0.0:
                return '"-INF"^^xsd:float'
            else:
                return '"INF"^^xsd:float'
        else:
            return f'"{self.__value}"^^xsd:float'

    def _as_dict(self) -> dict:
        return {'value': self.__value}

    @property
    def value(self) -> float:
        return self.__value
