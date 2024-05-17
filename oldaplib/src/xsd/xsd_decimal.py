import re
from typing import Self

from pystrict import strict

from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorType
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.floatingpoint import FloatingPoint
from oldaplib.src.xsd.xsd import Xsd


#@strict
@serializer
class Xsd_decimal(FloatingPoint):
    """
    Implements the XML Schema [xsd:decimal](https://www.w3.org/TR/xmlschema11-2/#decimal) datatype. Is a subclass of FloatingPoint class and
    inherits most methods from the FloatingPoint class.
    """

    def __init__(self, value: Self | float | str, validate: bool = True):
        """
        Constructor for the Xsd_decimal class.
        :param value: Either a Xsd_decimal, float or string in decimal format.
        :type value: Xsd_decimal | float | str
        :raises OldapErrorValue: If the value is not in a valid decimal format.
        """
        if isinstance(value, str):
            if validate:
                if not re.match("^[+-]?[0-9]*\\.?[0-9]*$", value):
                    raise OldapErrorValue(f'"{value}" is not a xsd:decimal.')
            value = float(value)
        super().__init__(value)

    @property
    def toRdf(self) -> str:
        """
        Converts the Xsd_decimal object to a RDF string.
        :return: RDF string
        """
        return self._toRdf('xsd:decimal')

