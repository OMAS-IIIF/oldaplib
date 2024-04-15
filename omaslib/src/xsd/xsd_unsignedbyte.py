from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_integer import Xsd_integer


@strict
@serializer
class Xsd_unsignedByte(Xsd_integer):
    """
    Implements the XSD Schema [xsd:unsignedByte](https://www.w3.org/TR/xmlschema11-2/#unsignedByte) datatype.
    Inherits from Xsd_integer.
    """

    def __init__(self, value: Xsd_integer | int | str):
        """
        Constructor of the Xsd_unsignedByte class.
        :param value: A Xsd_integer instance, an int in the range [0, 255] or a valid string representation.
        :type value: Xsd_integer | int | str
        :raises OmasErrorValue: If the value is not a valid unsigned byte value.
        """
        super().__init__(value)
        if self._value < 0 or self._value > 255:
            raise OmasErrorValue('Value must be in the range of [0 - 255].')

