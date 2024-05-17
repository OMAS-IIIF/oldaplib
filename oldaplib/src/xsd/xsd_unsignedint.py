from pystrict import strict

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_integer import Xsd_integer


#@strict
@serializer
class Xsd_unsignedInt(Xsd_integer):
    """
    Implements the XML Schema [xsd:unsignedInt](https://www.w3.org/TR/xmlschema11-2/#unsignedInt) datatype.
    Inherits from Xsd_integer.
    """

    def __init__(self, value: Xsd_integer | int | str, validate: bool = True):
        """
        Constructor for the Xsd_unsignedInt class
        :param value: A Xsd_unsignedInt instance, an int in the range[0 - 4294967295] or a valid string representation.
        :type value: Xsd_unsignedInt | int | str
        :raises OldapErrorValue: If the value is not a valid representation of an unsigned int.
        """
        super().__init__(value)
        if self._value < 0 or self._value > 4294967295:
            raise OldapErrorValue('Value must be in the range of [0 - 4294967295].')
