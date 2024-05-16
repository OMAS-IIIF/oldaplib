from typing import Self

from pystrict import strict

from oldap.src.helpers.oldaperror import OldapErrorValue
from oldap.src.helpers.serializer import serializer
from oldap.src.xsd.xsd import Xsd
from oldap.src.xsd.xsd_integer import Xsd_integer


#@strict
@serializer
class Xsd_nonPositiveInteger(Xsd_integer):
    """
    IMplements the XML Schema [xsd:nonPositiveInteger](https://www.w3.org/TR/xmlschema11-2/#nonPositiveInteger) datatype. Inherits from Xsd_integer.
    """

    def __init__(self, value: Xsd_integer | int | str, validate: bool = True):
        """
        Constructor of the Xsd_nonPositiveInteger class.
        :param value: A Xsd instance or an integer value <= 0.
        :type value: Xsd_integer | int | str
        :raises OmasErrorValue: If the value is not a non-positive integer.
        """
        super().__init__(value)
        if self._value > 0:
            raise OldapErrorValue('Value must be "0" or negative')

