from typing import Self

from pystrict import strict

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_integer import Xsd_integer


#@strict
@serializer
class Xsd_int(Xsd_integer):
    """
    Implements the XML Schema [xsd:int](https://www.w3.org/TR/xmlschema11-2/#int) class.
    It inherits from Xsd_integer. The xsd:int datatype has a limited range -2147483648 - 2147483647.
    """

    def __init__(self, value: Xsd_integer | int | str, validate: bool = False):
        """
        Constructor for Xsd_int class
        :param value: Int value. Must be in the range -2147483648 - 2147483647
        :type value: Xsd_integer | int | str
        :raises OldapValueError: If value is not in the range -2147483648 - 2147483647 or is not a valid
        integer representation.
        """
        super().__init__(value, validate=validate)
        if self._value < -2147483648 or self._value > 2147483647:
            raise OldapErrorValue(f"Value must be between -2147483648 and 2147483647")
