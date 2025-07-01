import math
from typing import Self

from pystrict import strict

from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorType
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd


#@strict
@serializer
class FloatingPoint(Xsd):
    """
    This is the superclass of all floating point based XML Schema classes. It implements the basic
    functionality of floating point XML Schema classes. These are:

    - Constructor method `__init__`
    - Comparison methods `==`, `!=`, `<__lt__>`, `<=`, `>`, `>=`
    - Serializer methods `str(XXX)`, `repr(XXX)`,
    - RDF property `toRdf`
    - Accessor methods `XXX.value`, `float(XX)`
    - Hashing methods `hash(XXX)`

    The validation flag does not have an effect.

    """
    _value: float

    def __init__(self, value: Self | float | str, validate: bool = False):
        """
        Constructor for Floating Point
        :param value: The initial value. May not be None
        :type value: A FloatingPoint value, a float value or a string that can be interpreted as float.
        :param validate: Whether to validate the initial value
        :type validate: bool
        :raises OldapErrorValue: If the value is not a float.
        :raises OldapErrorType: If the value is not a float.
        """
        if isinstance(value, FloatingPoint):
            self._value = value._value
        elif isinstance(value, float):
            self._value = value
        else:
            try:
                self._value = float(value)
            except ValueError as err:
                raise OldapErrorValue(str(err))
            except TypeError as err:
                raise OldapErrorType(str(err))

    def __float__(self) -> float:
        """
        Returns the value as a float.
        :return: float value of instance
        :rtype: float
        """
        return self._value

    def __str__(self) -> str:
        """
        Returns the value as a string. Special numbers are "NaN", "INF" and "-INF"
        :return: Value converted to string
        :rtype: str
        """
        match str(self._value):
            case 'nan':
                return 'NaN'
            case 'inf':
                return 'INF'
            case '-inf':
                return '-INF'
            case _:
                return str(self._value)

    def __repr__(self) -> str:
        """
        Returns the value as constructor statement string
        :return: Constructor statement string
        :rtype: str
        """
        if math.isnan(self._value):
            valstr = '"NaN"'
        elif math.isinf(self._value):
            if self._value < 0.0:
                valstr = '"-INF"'
            else:
                valstr = '"INF"'
        else:
            valstr = str(self._value)
        return f'{type(self).__name__}({valstr})'

    def __eq__(self, other: Self | float | int | str | None) -> bool:
        """
        Test for equality
        :param other: The value to compare with
        :type other: Self | float | str | None
        :return: True or False
        :rtype: bool
        :raises OldapErrorValue: If the value is not comparable to a float.
        """
        if other is None:
            return False
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, (float, int)):
            return self._value == other
        elif isinstance(other, FloatingPoint):
            return self._value == other._value
        else:
            raise OldapErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other)}')

    def __ne__(self, other: Self | float | int | str | None) -> bool:
        """
        Test for inequality
        :param other: The value to compare with
        :type other: Self | float | str | None
        :return: True or False
        :rtype: bool
        :raises OldapErrorValue: If the value is not comparable to a float.
        """
        if other is None:
            return True
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, (float, int)):
            return self._value != other
        elif isinstance(other, FloatingPoint):
            return self._value != other._value
        else:
            raise OldapErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __lt__(self, other: Self | float | int | str) -> bool:
        """
        Test for less-than
        :param other: The value to compare with
        :type other: Self | float | str | None
        :return: True or False
        :rtype: bool
        :raises OldapErrorValue: If the value is not comparable to a float.
        """
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, (float, int)):
            return self._value < other
        elif isinstance(other, FloatingPoint):
            return self._value < other._value
        else:
            raise OldapErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __le__(self, other: Self | float | int | str) -> bool:
        """
        Test for less or equal than
        :param other: The value to compare with
        :type other: Self | float | str
        :return: True or False
        :rtype: bool
        :raises OldapErrorValue: If the value is not comparable to a float.
        """
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, (float, int)):
            return self._value <= other
        elif isinstance(other, FloatingPoint):
            return self._value <= other._value
        else:
            raise OldapErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __gt__(self, other: Self | float | int | str) -> bool:
        """
        Test for greater than
        :param other: The value to compare with
        :type other: Self | float | str
        :return: True or False
        :rtype: bool
        :raises OldapErrorValue: If the value is not comparable to a float.
        """
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, (float, int)):
            return self._value > other
        elif isinstance(other, FloatingPoint):
            return self._value > other._value
        else:
            raise OldapErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __ge__(self, other: Self | float | int | str) -> bool:
        """
        Test for greater or equal than
        :param other: The value to compare with
        :type other: Self | float | str
        :return: True or False
        :rtype: bool
        :raises OldapErrorValue: If the value is not comparable to a float.
        """
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, (float, int)):
            return self._value >= other
        elif isinstance(other, FloatingPoint):
            return self._value >= other._value
        else:
            raise OldapErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __hash__(self) -> int:
        """
        Returns the hash value of the instance
        :return: Hash value of instance
        :rtype: int
        """
        return hash(self._value)

    @property
    def value(self) -> float:
        """
        Returns the value of the instance
        :return: Value of instance as float
        :rtype: float
        """
        return self._value

    def _toRdf(self, xsdtype: str = 'xsd:float') -> str:
        """
        Helper for converting instances to a RDF string
        :param xsdtype: XML Schema type to use
        :type xsdtype: XML Schema datatype to use (prefix: "xsd" to be used)
        :return: string representation of the instance as RDF
        :rtype: str
        """
        if math.isnan(self):
            return '"NaN"^^' + xsdtype
        elif math.isinf(self):
            if self < 0.0:
                return '"-INF"^^' + xsdtype
            else:
                return '"INF"^^' + xsdtype
        else:
            return f'"{self}"^^' + xsdtype

    @property
    def toRdf(self) -> str:
        """
        Converts the instance to a RDF string as xsd:float
        :return: RDF string representation of the instance as RDF
        :rtype: str
        """
        return self._toRdf('xsd:float')

    def _as_dict(self) -> dict:
        """
        Used internally for JSON serialization using @serialisation decorator
        :return: Representation of the instance as dict
        :rtype: dict
        """
        return {'value': self._value}

if __name__ == '__main__':
    f = FloatingPoint("1.0")






