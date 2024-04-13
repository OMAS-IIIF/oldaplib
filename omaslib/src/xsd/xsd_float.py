import math
import re
from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.floatingpoint import FloatingPoint
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_float(FloatingPoint):
    """
    Implements the XML Schema [xsd:float](https://www.w3.org/TR/xmlschema11-2/#float) datatype
    """

    def __init__(self, value: Self | float | str):
        """
        Constructor for Xsd_float class
        :param value: A Xsd_float value, a floating point or a string containing a valid float value
        :type value: Xsd_float | float | str
        :raises OmasErrorValue: If the value is not a float or a string containing a valid float value
        """
        if isinstance(value, str):
            if not re.match("^([-+]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][-+]?\\d+)?|[Nn]a[Nn]|[-+]?(inf|INF))$", value):
                raise OmasErrorValue(f'"{value}" is not a xsd:float.')
            value = float(value)
        super().__init__(value)

    @property
    def toRdf(self) -> str:
        return self._toRdf('xsd:float')
