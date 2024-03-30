from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_integer import Xsd_integer


@strict
@serializer
class Xsd_nonNegativeInteger(Xsd_integer):
    __value: int

    def __init__(self, value: Xsd | int | str):
        super().__init__(value)
        if self._value < 0:
            raise OmasErrorValue('Value must be "0" or positive.')
