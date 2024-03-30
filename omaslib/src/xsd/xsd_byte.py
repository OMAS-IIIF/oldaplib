from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_integer import Xsd_integer


@strict
@serializer
class Xsd_byte(Xsd_integer):

    def __init__(self, value: Xsd | int | str):
        super().__init__(value)
        if self._value < -128 or self._value > 127:
            raise OmasErrorValue(f'Value must be between -128 and 127')
