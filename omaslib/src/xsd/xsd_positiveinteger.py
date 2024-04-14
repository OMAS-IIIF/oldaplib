from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_integer import Xsd_integer


@strict
@serializer
class Xsd_positiveInteger(Xsd_integer):
    """
    Implements the XML Schema [xsd:positiveinteger](https://www.w3.org/TR/xmlschema11-2/#positiveInteger) datatype.
    Inherits from Xsd_integer.
    """

    def __init__(self, value: Xsd_integer | int | str):
        """
        Constructor of Xsd_positiveInteger class.
        :param value: A valid XSD instance, a positive int or a valid string
        :type value: Xsd_integer | int | str
        :raises OmasErrorValue: If the value is invalid.
        """
        super().__init__(value)
        if not self._value > 0:
            raise OmasErrorValue('Value must be greater 0.')
