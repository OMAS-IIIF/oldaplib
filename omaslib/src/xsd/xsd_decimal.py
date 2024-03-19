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

    def __init__(self, value: float | str):
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
        return f'"{str(self.__value)}"^^xsd:decimal'

    def __float__(self) -> float:
        return self.__value

    @property
    def toRdf(self) -> str:
        return str(self.__value)

    def _as_dict(self) -> dict[str, float]:
        return {'value': self.__value}

    @property
    def value(self) -> float:
        return self.__value
