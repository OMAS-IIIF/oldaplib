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

    def __init__(self, value: float | str):
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
            return '"NaN"^^xsd:float'
        elif math.isinf(self.__value):
            if self.__value < 0.0:
                return '"-INF"^^xsd:float'
            else:
                return '"INF"^^xsd:float'
        else:
            return f'"{self.__value}"^^xsd:float'

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
