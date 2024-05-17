from typing import Self

from pystrict import strict

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_integer import Xsd_integer


#@strict
@serializer
class Xsd_unsignedByte(Xsd_integer):
    """
    Implements the XSD Schema [xsd:unsignedByte](https://www.w3.org/TR/xmlschema11-2/#unsignedByte) datatype.
    Inherits from Xsd_integer.
    """

    def __init__(self, value: Xsd_integer | int | str, validate: bool = True):
        """
        Constructor of the Xsd_unsignedByte class.
        :param value: A Xsd_integer instance, an int in the range [0, 255] or a valid string representation.
        :type value: Xsd_integer | int | str
        :raises OldapErrorValue: If the value is not a valid unsigned byte value.
        """
        super().__init__(value)
        if self._value < 0 or self._value > 255:
            raise OldapErrorValue('Value must be in the range of [0 - 255].')

