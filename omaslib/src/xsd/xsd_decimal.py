import re
from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue, OmasErrorType
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.floatingpoint import FloatingPoint
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_decimal(FloatingPoint):

    def __init__(self, value: Self | float | str):
        if isinstance(value, str):
            if not re.match("^[+-]?[0-9]*\\.?[0-9]*$", value):
                raise OmasErrorValue(f'"{value}" is not a xsd:decimal.')
            value = float(value)
        super().__init__(value)

    @property
    def toRdf(self) -> str:
        return self._toRdf('xsd:decimal')

