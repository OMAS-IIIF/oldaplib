from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_integer import Xsd_integer


@strict
@serializer
class Xsd_unsignedShort(Xsd_integer):
    """
    Implements the XSD Schema [xsd:unsignedShort](https://www.w3.org/TR/xmlschema11-2/#unsignedShort) datatype.
    Inherits from Xsd_integer.
    """

    def __init__(self, value: Xsd_integer | int | str):
        """
        Constructor for the Xsd_unsignedShort class.
        :param value: A Xsd_integer instance, a valid int or a valid string representation. Valid range [0 - 65535].
        :type value: Xsd_integer | int | str
        :raises OmasErrorValue: If the value is not a valid unsigned short
        """
        super().__init__(value)
        if self._value < 0 or self._value > 65535:
            raise OmasErrorValue('Value must be in the range of [0 - 65535].')
