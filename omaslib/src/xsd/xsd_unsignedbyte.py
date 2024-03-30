from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_integer import Xsd_integer


@strict
@serializer
class Xsd_unsignedByte(Xsd_integer):

    def __init__(self, value: Xsd | int | str):
        super().__init__(value)
        if self._value < 0 or self._value > 255:
            raise OmasErrorValue('Value must be in the range of [0 - 255].')

