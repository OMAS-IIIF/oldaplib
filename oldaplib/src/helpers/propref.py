from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.xsd.floatingpoint import FloatingPoint
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_float import Xsd_float
from oldaplib.src.xsd.xsd_integer import Xsd_integer


class PropRef:
    """
    This class represents a numeric value that eiter can be a subclass of Xsd_integer (and it's subclasses) or
    a subclass of FloatingPoint (and it's subclasses). FLoatingPoint is the superclass of all XML Schema datatypes
    with a floating point content (e.g. Xsd_float, Xsd_decimal etc.)
    """
    def __new__(cls, value: PropertyClass | Iri | str):
        if isinstance(value, (PropertyClass)):
            return value
        elif isinstance(value, (Iri, str)):
            return Iri(value)


if __name__ == '__main__':
    a = PropRef("sh:gaga")
    print(type(a).__name__)
