from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_integer(Xsd):
    _value: int

    def __init__(self, value: Xsd | int | str):
        if isinstance(value, Xsd_integer):
            self._value = value._value
        elif isinstance(value, int):
            self._value = value
        else:
            try:
                self._value = int(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f'{type(self).__name__}({str(self._value)})'

    def __hash__(self) -> int:
        return hash(self._value)

    def __int__(self) -> int:
        return self._value

    def __eq__(self, other: Self | int | None) -> bool:
        if other is None:
            return False
        if isinstance(other, Xsd_integer):
            return self._value == other._value
        elif isinstance(other, int):
            return self._value == other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __ne__(self, other: Self | int) -> bool:
        if other is None:
            return True
        if isinstance(other, Xsd_integer):
            return self._value != other._value
        elif isinstance(other, int):
            return self._value != other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __gt__(self, other: Self | int) -> bool:
        if isinstance(other, Xsd_integer):
            return self._value > other._value
        elif isinstance(other, int):
            return self._value > other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __ge__(self, other: Self | int) -> bool:
        if isinstance(other, Xsd_integer):
            return self._value >= other._value
        elif isinstance(other, int):
            return self._value >= other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __lt__(self, other: Self | int) -> bool:
        if isinstance(other, Xsd_integer):
            return self._value < other._value
        elif isinstance(other, int):
            return self._value < other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __le__(self, other: Self | int) -> bool:
        if isinstance(other, Xsd_integer):
            return self._value <= other._value
        elif isinstance(other, int):
            return self._value <= other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def _as_dict(self) -> dict[str, int]:
        return {'value': self._value}

    @property
    def toRdf(self) -> str:
        xsddummy, name = type(self).__name__.split('_')
        return f'"{str(self._value)}"^^xsd:{name}'

    @property
    def value(self) -> int:
        return self._value

