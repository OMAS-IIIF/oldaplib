import math
import re

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_double(Xsd):
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
        return str(self.__value)

    def __repr__(self) -> str:
        if math.isnan(self):
            return '"NaN"^^xsd:double'
        elif math.isinf(self):
            if self < 0.0:
                return '"-INF"^^xsd:double'
            else:
                return '"INF"^^xsd:double'
        else:
            return f'"{self}"^^xsd:double'

    def __hash__(self) -> int:
        return hash(self.__value)

    def __float__(self):
        return self.__value

    @property
    def toRdf(self) -> str:
        if math.isnan(self):
            return '"NaN"^^xsd:double'
        elif math.isinf(self):
            if self < 0.0:
                return '"-INF"^^xsd:double'
            else:
                return '"INF"^^xsd:double'
        else:
            return f'"{self}"^^xsd:double'

    def _as_dict(self) -> dict:
        return {'value': float(self)}

    @property
    def value(self) -> float:
        return self.__value
