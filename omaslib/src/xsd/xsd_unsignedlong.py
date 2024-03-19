from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_unsignedLong(Xsd):
    __value: int

    def __init__(self, value: int | str):
        if isinstance(value, int):
            self.__value = value
        else:
            try:
                self.__value = int(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))
        if self.__value < 0 or self.__value > 18446744073709551615:
            raise OmasErrorValue('Value must be in the range of [0 - 18446744073709551615].')


    def __str__(self) -> str:
        return str(self.__value)

    def __repr__(self) -> str:
        return f'"{str(self.__value)}"^^xsd:unsignedLong'

    def __int__(self) -> int:
        return self.__value

    def __hash__(self):
        return hash(self.__value)

    @property
    def toRdf(self) -> str:
        return f'"{str(self.__value)}"^^xsd:unsignedLong'

    def _as_dict(self) -> dict:
        return {'value': self.__value}

    @property
    def value(self) -> int:
        return self.__value

