from typing import Self

from pystrict import strict

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_integer import Xsd_integer


#@strict
@serializer
class Xsd_negativeInteger(Xsd_integer):
    """
    Implements the XML Schema [xsd:negativeInteger](https://www.w3.org/TR/xmlschema11-2/#negativeInteger) datatype.
    This class inherits from Xsd_integer
    """

    def __init__(self, value: Xsd_integer | int | str, validate: bool = False):
        """
        Constructor of the Xsd_negativeInteger class.
        :param value: Any valid Xsd value, an int or a string reprenting a negative integer.
        :type value: Xsd_integer | int | str
        :raises OldapErrorValue: If the value is not a valid Xsd or negative integer.
        """
        super().__init__(value)
        if not self._value < 0:
            raise OldapErrorValue('Value must negative.')
