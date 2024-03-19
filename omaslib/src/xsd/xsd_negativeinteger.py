from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_negativeInteger(Xsd):
    __value: int

    def __init__(self, value: int | str):
        if isinstance(value, int):
            self.__value = value
        else:
            try:
                self.__value = int(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))
        if not self.__value < 0:
            raise OmasErrorValue('Value must negative.')

    def __str__(self) -> str:
        return str(self.__value)

    def __repr__(self) -> str:
        return f'"{str(self.__value)}"^^xsd:negativeInteger'

    def __hash__(self) -> int:
        return hash(self.__value)

    def __int__(self) -> int:
        return self.__value

    def _as_dict(self) -> dict:
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        return f'"{str(self.__value)}"^^xsd:negativeInteger'

    @property
    def value(self) -> int:
        return self.__value
