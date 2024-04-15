from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_integer import Xsd_integer


@strict
@serializer
class Xsd_unsignedInt(Xsd_integer):
    """
    Implements the XML Schema [xsd:unsignedInt](https://www.w3.org/TR/xmlschema11-2/#unsignedInt) datatype.
    Inherits from Xsd_integer.
    """

    def __init__(self, value: Xsd_integer | int | str):
        """
        Constructor for the Xsd_unsignedInt class
        :param value: A Xsd_unsignedInt instance, an int in the range[0 - 4294967295] or a valid string representation.
        :type value: Xsd_unsignedInt | int | str
        :raises OmasErrorValue: If the value is not a valid representation of an unsigned int.
        """
        super().__init__(value)
        if self._value < 0 or self._value > 4294967295:
            raise OmasErrorValue('Value must be in the range of [0 - 4294967295].')
