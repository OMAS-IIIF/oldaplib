from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_integer import Xsd_integer


@strict
@serializer
class Xsd_nonNegativeInteger(Xsd_integer):
    """
    Implements the XML Schema [xsd:nonNegativeInteger](https://www.w3.org/TR/xmlschema11-2/#nonNegativeInteger) datatype. Inherits from Xsd_integer.
    """
    __value: int

    def __init__(self, value: Xsd_integer | int | str):
        """
        Constructor of the Xsd_nonNegativeInteger class.
        :param value: Another valid Xsd instance, a non-negative integer or a valid string representation.
        :type value: Xsd_integer | int | str
        :raises OmasErrorValue: If the value does not represent a valid non-negative integer.
        """
        super().__init__(value)
        if self._value < 0:
            raise OmasErrorValue('Value must be "0" or positive.')
