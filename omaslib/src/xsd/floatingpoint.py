import math
from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue, OmasErrorType
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class FloatingPoint(Xsd):
    _value: float

    def __init__(self, value: Self | float | str):
        if isinstance(value, FloatingPoint):
            self._value = value._value
        elif isinstance(value, float):
            self._value = value
        else:
            try:
                self._value = float(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))
            except TypeError as err:
                raise OmasErrorType(str(err))

    def __float__(self) -> float:
        return self._value

    def __str__(self) -> str:
        match str(self._value):
            case 'nan':
                return 'NaN'
            case 'inf':
                return 'INF'
            case '-inf':
                return '-INF'
            case _:
                return str(self._value)

    def __repr__(self) -> str:
        if math.isnan(self._value):
            valstr = '"NaN"'
        elif math.isinf(self._value):
            if self._value < 0.0:
                valstr = '"-INF"'
            else:
                valstr = '"INF"'
        else:
            valstr = str(self._value)
        return f'{type(self).__name__}({valstr})'

    def __eq__(self, other: Self | float | str | None) -> bool:
        if other is None:
            return False
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, float):
            return self._value == other
        elif isinstance(other, FloatingPoint):
            return self._value == other._value
        else:
            raise OmasErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other)}')

    def __ne__(self, other: Self | float | str | None) -> bool:
        if other is None:
            return True
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, float):
            return self._value != other
        elif isinstance(other, FloatingPoint):
            return self._value != other._value
        else:
            raise OmasErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __lt__(self, other: Self | float | str) -> bool:
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, float):
            return self._value < other
        elif isinstance(other, FloatingPoint):
            return self._value < other._value
        else:
            raise OmasErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __le__(self, other: Self | float | str) -> bool:
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, float):
            return self._value <= other
        elif isinstance(other, FloatingPoint):
            return self._value <= other._value
        else:
            raise OmasErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __gt__(self, other: Self | float | str) -> bool:
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, float):
            return self._value > other
        elif isinstance(other, FloatingPoint):
            return self._value > other._value
        else:
            raise OmasErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __ge__(self, other: Self | float | str) -> bool:
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, float):
            return self._value >= other
        elif isinstance(other, FloatingPoint):
            return self._value >= other._value
        else:
            raise OmasErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __hash__(self) -> int:
        return hash(self._value)

    @property
    def value(self) -> float:
        return self._value

    def _toRdf(self, xsdtype: str = 'xsd:float') -> str:
        if math.isnan(self):
            return '"NaN"^^' + xsdtype
        elif math.isinf(self):
            if self < 0.0:
                return '"-INF"^^' + xsdtype
            else:
                return '"INF"^^' + xsdtype
        else:
            return f'"{self}"^^' + xsdtype

    @property
    def toRdf(self) -> str:
        return self._toRdf('xsd:float')

    def _as_dict(self) -> dict:
        return {'value': self._value}

if __name__ == '__main__':
    f = FloatingPoint("1.0")






