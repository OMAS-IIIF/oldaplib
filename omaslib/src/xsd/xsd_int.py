from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_int(Xsd):
    __value: int

    def __init__(self, value: Self | int | str):
        if isinstance(value, Xsd_int):
            self.__value = value.__value
        if isinstance(value, int):
            self.__value = value
        else:
            try:
                self.__value = int(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))
        if self.__value < -2147483648 or self.__value > 2147483647:
            raise OmasErrorValue(f"Value must be between -2147483648 and 2147483647")

    def __str__(self) -> str:
        return str(self.__value)

    def __repr__(self) -> str:
        return f'Xsd_int({str(self.__value)})'

    def __hash__(self) -> int:
        return hash(self.__value)

    def __int__(self) -> int:
        return self.__value

    def __eq__(self, other: Self | int) -> bool:
        if isinstance(other, Xsd_int):
            return self.__value == other.__value
        elif isinstance(other, int):
            return self.__value == other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __ne__(self, other: Self | int) -> bool:
        if isinstance(other, Xsd_int):
            return self.__value != other.__value
        elif isinstance(other, int):
            return self.__value != other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __gt__(self, other: Self | int) -> bool:
        if isinstance(other, Xsd_int):
            return self.__value > other.__value
        elif isinstance(other, int):
            return self.__value > other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __ge__(self, other: Self | int) -> bool:
        if isinstance(other, Xsd_int):
            return self.__value >= other.__value
        elif isinstance(other, int):
            return self.__value >= other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __lt__(self, other: Self | int) -> bool:
        if isinstance(other, Xsd_int):
            return self.__value < other.__value
        elif isinstance(other, int):
            return self.__value < other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __le__(self, other: Self | int) -> bool:
        if isinstance(other, Xsd_int):
            return self.__value <= other.__value
        elif isinstance(other, int):
            return self.__value <= other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def _as_dict(self) -> dict:
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        return f'"{str(self.__value)}"^^xsd:int'

    @property
    def value(self) -> int:
        return self.__value
