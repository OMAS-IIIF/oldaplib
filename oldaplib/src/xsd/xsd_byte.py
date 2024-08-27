from typing import Self

from pystrict import strict

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_integer import Xsd_integer


#@strict
@serializer
class Xsd_byte(Xsd_integer):
    """
    Xsd_byte is a class that represents an XML Schema [xsd:byte datatype](https://www.w3.org/TR/xmlschema11-2/#byte). It is derived from Xsd_integer
    and inherits most methods from Xsd_integer.
    """

    def __init__(self, value: Xsd | int | str, validate: bool = True):
        """
        Xsd_byte constructor
        :param value: a byte value >= -128 and <= 127
        :type value: Xsd | int | str
        :raises OldapErrorValue: if the value is not valid or cannot be converted to Xsd_byte type.
        """
        super().__init__(value, validate=validate)
        if self._value < -128 or self._value > 127:
            raise OldapErrorValue(f'Value must be between -128 and 127')
