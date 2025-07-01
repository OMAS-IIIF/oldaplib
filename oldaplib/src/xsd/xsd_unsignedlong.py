from pystrict import strict

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_integer import Xsd_integer


#@strict
@serializer
class Xsd_unsignedLong(Xsd_integer):
    """
    Implements the XML Schema [xsd:unsignedLong](https://www.w3.org/TR/xmlschema11-2/#unsignedLong) datatype.
    Inherits from Xsd_integer.
    """

    def __init__(self, value: Xsd_integer | int | str, validate: bool = False):
        """
        Constructor of the Xsd_unsignedLong class.
        :param value: A Xsd_integer instance, an int or a string representation.
        :type value: Xsd_integer | int | str
        :raises OldapErrorValue: If the value is not a valid unsigned long value.
        """
        super().__init__(value)
        if self._value < 0 or self._value > 18446744073709551615:
            raise OldapErrorValue('Value must be in the range of [0 - 18446744073709551615].')
