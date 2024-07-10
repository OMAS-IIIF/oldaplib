from oldaplib.src.xsd.floatingpoint import FloatingPoint
from oldaplib.src.xsd.xsd_float import Xsd_float
from oldaplib.src.xsd.xsd_integer import Xsd_integer


class Numeric:
    """
    This class represents a numeric value that eiter can be a subclass of Xsd_integer (and it's subclasses) or
    a subclass of FloatingPoint (and it's subclasses). FLoatingPoint is the superclass of all XML Schema datatypes
    with a floating point content (e.g. Xsd_float, Xsd_decimal etc.)
    """
    def __new__(cls, value: Xsd_integer | int | FloatingPoint | float | str):
        if isinstance(value, (Xsd_integer, int)):
            return Xsd_integer(value)
        elif isinstance(value, (FloatingPoint, float)):
            return Xsd_float(value)
        else:
            try:
                return Xsd_integer(str(value))
            except:
                return Xsd_float(str(value))

