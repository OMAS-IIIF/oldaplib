from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_integer import Xsd_integer


@strict
@serializer
class Xsd_unsignedLong(Xsd_integer):
    """
    Implements the XML Schema [xsd:unsignedLong](https://www.w3.org/TR/xmlschema11-2/#unsignedLong) datatype.
    Inherits from Xsd_integer.
    """

    def __init__(self, value: Xsd_integer | int | str):
        """
        Constructor of the Xsd_unsignedLong class.
        :param value: A Xsd_integer instance, an int or a string representation.
        :type value: Xsd_integer | int | str
        :raises OmasErrorValue: If the value is not a valid unsigned long value.
        """
        super().__init__(value)
        if self._value < 0 or self._value > 18446744073709551615:
            raise OmasErrorValue('Value must be in the range of [0 - 18446744073709551615].')
