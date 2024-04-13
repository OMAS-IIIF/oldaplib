from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_integer import Xsd_integer


@strict
@serializer
class Xsd_byte(Xsd_integer):
    """
    Xsd_byte is a class that represents an XML Schema [xsd:byte datatype](https://www.w3.org/TR/xmlschema11-2/#byte). It is derived from Xsd_integer
    and inherits most methods from Xsd_integer.
    """

    def __init__(self, value: Xsd | int | str):
        """
        Xsd_byte constructor
        :param value: a byte value >= -128 and <= 127
        :raises OmasErrorValue: if the value is not valid or cannot be converted to Xsd_byte type.
        """
        super().__init__(value)
        if self._value < -128 or self._value > 127:
            raise OmasErrorValue(f'Value must be between -128 and 127')
