from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_integer import Xsd_integer


@strict
@serializer
class Xsd_short(Xsd_integer):
    """
    Implements the XML Schema [xsd:short](https://www.w3.org/TR/xmlschema11-2/#short) datatype. Inherits from
    Xsd_integer.
    """

    def __init__(self, value: Xsd_integer | int | str):
        """
        Constructor for the Xsd_short class
        :param value: A valid xsd class, an int in the range of -32768 - 32767, or a valid str
        :type value: Xsd_integer | int | str
        :raises OmasErrorValue: If the value is not a valid short value
        """
        super().__init__(value)
        if self._value < -32768 or self._value > 32767:
            raise OmasErrorValue('Value must be in the range of [-32768 - 32767].')
