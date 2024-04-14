from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_integer import Xsd_integer


@strict
@serializer
class Xsd_int(Xsd_integer):
    """
    Implements the XML Schema [xsd:int](https://www.w3.org/TR/xmlschema11-2/#int) class.
    It inherits from Xsd_integer. The xsd:int datatype has a limited range -2147483648 - 2147483647.
    """

    def __init__(self, value: Xsd_integer | int | str):
        """
        Constructor for Xsd_int class
        :param value: Int value. Must be in the range -2147483648 - 2147483647
        :type value: Xsd_integer | int | str
        :raises OmasValueError: If value is not in the range -2147483648 - 2147483647 or is not a valid
        integer representation.
        """
        super().__init__(value)
        if self._value < -2147483648 or self._value > 2147483647:
            raise OmasErrorValue(f"Value must be between -2147483648 and 2147483647")
