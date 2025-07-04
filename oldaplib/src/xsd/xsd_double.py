import math
import re
from typing import Self

from pystrict import strict

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.floatingpoint import FloatingPoint
from oldaplib.src.xsd.xsd import Xsd


#@strict
@serializer
class Xsd_double(FloatingPoint):
    """
    Implements the XML Schema [xsd:double](https://www.w3.org/TR/xmlschema11-2/#double) datatype.
    """
    _value: float

    def __init__(self, value: FloatingPoint | float | str, validate: bool = False):
        """
        Constructor for the Xsd_double class.
        :param value: a FloatinPoint instance, a float or a valid string for a float number
        :type value: FloatingPoint | float | str
        :raises OldapErrorValue: if the value cannot be converted to a floating point value
        """
        if isinstance(value, str):
            if validate:
                if not re.match("^([-+]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][-+]?\\d+)?|[Nn]a[Nn]|[-+]?(inf|INF))$", str(value)):
                    raise OldapErrorValue(f'"{value}" is not convertible to a Xsd_float.')
            value = float(value)
        super().__init__(value=value, validate=validate)

    @property
    def toRdf(self) -> str:
        """
        Converts the Xsd_double instance to a RDF string.
        :return: RDF string
        """
        return super()._toRdf('xsd:double')

