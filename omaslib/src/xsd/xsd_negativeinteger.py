from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_integer import Xsd_integer


@strict
@serializer
class Xsd_negativeInteger(Xsd_integer):
    """
    Implements the XML Schema [xsd:negativeInteger](https://www.w3.org/TR/xmlschema11-2/#negativeInteger) datatype.
    This class inherits from Xsd_integer
    """

    def __init__(self, value: Xsd_integer | int | str):
        """
        Constructor of the Xsd_negativeInteger class.
        :param value: Any valid Xsd value, an int or a string reprenting a negative integer.
        :type value: Xsd_integer | int | str
        :raises OmasErrorValue: If the value is not a valid Xsd or negative integer.
        """
        super().__init__(value)
        if not self._value < 0:
            raise OmasErrorValue('Value must negative.')
