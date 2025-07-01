from typing import Self

from pystrict import strict

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_integer import Xsd_integer


#@strict
@serializer
class Xsd_long(Xsd_integer):
    """
    Implements the XML Schema [xsd:long](https://www.w3.org/TR/xmlschema11-2/#long) datatype. It has
    a range of -9223372036854775808 to 9223372036854775807. It subclasses Xsd_integer
    """

    def __init__(self, value: Xsd_integer | int | str, validate: bool = False):
        """
        Constructor for the Xsd_long datatype.
        :param value: The integer value as Xsd_long, int or string. It must be in the
        range of -9223372036854775808 to 9223372036854775807
        :type value: Xsd_integer | int | str
        :raises OldapErrorValue: If the value is not a valid long integer
        """
        super().__init__(value, validate=validate)
        if self._value < -9223372036854775808 or self._value > 9223372036854775807:
            raise OldapErrorValue('Value must be in the range of [-9223372036854775808 - 9223372036854775807].')
