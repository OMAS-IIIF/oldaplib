from pystrict import strict

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_integer import Xsd_integer


#@strict
@serializer
class Xsd_unsignedShort(Xsd_integer):
    """
    Implements the XSD Schema [xsd:unsignedShort](https://www.w3.org/TR/xmlschema11-2/#unsignedShort) datatype.
    Inherits from Xsd_integer.
    """

    def __init__(self, value: Xsd_integer | int | str, validate: bool = False):
        """
        Constructor for the Xsd_unsignedShort class.
        :param value: A Xsd_integer instance, a valid int or a valid string representation. Valid range [0 - 65535].
        :type value: Xsd_integer | int | str
        :raises OldapErrorValue: If the value is not a valid unsigned short
        """
        super().__init__(value)
        if self._value < 0 or self._value > 65535:
            raise OldapErrorValue('Value must be in the range of [0 - 65535].')
