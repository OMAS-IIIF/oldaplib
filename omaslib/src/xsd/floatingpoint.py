"""
# FloatingPoint

This module provides basic class to represent floating point numbers.
"""
import math
from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue, OmasErrorType
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class FloatingPoint(Xsd):
    """
    This is the superclass of floating point based XML Schema classes. It implements the basic
    functionality of floating point XML Schema classes.
    """
    _value: float

    def __init__(self, value: Self | float | str):
        """
        Constructor for Floating Point
        :param value: The initial value. May not be None
        :type value: A FloatingPoint value, a float value or a string that can be interpreted as float.
        """
        if isinstance(value, FloatingPoint):
            self._value = value._value
        elif isinstance(value, float):
            self._value = value
        else:
            try:
                self._value = float(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))
            except TypeError as err:
                raise OmasErrorType(str(err))

    def __float__(self) -> float:
        """
        Returns the value as a float.
        :return: float value of instance
        """
        return self._value

    def __str__(self) -> str:
        """
        Returns the value as a string. Special numbers are "NaN", "INF" and "-INF"
        :return: Value converted to string
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
        Returns the value as constructor statment
        :return: Constructor statment
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

    def __eq__(self, other: Self | float | str | None) -> bool:
        """
        test for equality
        :param other: The value to compare with
        :type other: Self | float | str | None
        :return: True or False
        """
        if other is None:
            return False
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, float):
            return self._value == other
        elif isinstance(other, FloatingPoint):
            return self._value == other._value
        else:
            raise OmasErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other)}')

    def __ne__(self, other: Self | float | str | None) -> bool:
        """
        test for inequality
        :param other: The value to compare with
        :type other: Self | float | str | None
        :return: True or False
        """
        if other is None:
            return True
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, float):
            return self._value != other
        elif isinstance(other, FloatingPoint):
            return self._value != other._value
        else:
            raise OmasErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __lt__(self, other: Self | float | str) -> bool:
        """
        test for less
        :param other: The value to compare with
        :type other: Self | float | str | None
        :return: True or False
        """
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, float):
            return self._value < other
        elif isinstance(other, FloatingPoint):
            return self._value < other._value
        else:
            raise OmasErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __le__(self, other: Self | float | str) -> bool:
        """
        test for less-equal
        :param other: The value to compare with
        :type other: Self | float | str
        :return: True or False
        """
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, float):
            return self._value <= other
        elif isinstance(other, FloatingPoint):
            return self._value <= other._value
        else:
            raise OmasErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __gt__(self, other: Self | float | str) -> bool:
        """
        test for greater than
        :param other: The value to compare with
        :type other: Self | float | str
        :return: True or False
        """
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, float):
            return self._value > other
        elif isinstance(other, FloatingPoint):
            return self._value > other._value
        else:
            raise OmasErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __ge__(self, other: Self | float | str) -> bool:
        """
        test for greater than-equal
        :param other: The value to compare with
        :type other: Self | float | str
        :return: True or False
        """
        if isinstance(other, str):
            other = FloatingPoint(other)
        if isinstance(other, float):
            return self._value >= other
        elif isinstance(other, FloatingPoint):
            return self._value >= other._value
        else:
            raise OmasErrorValue(f'Cannot compare FloatingPoint("{self._value}") to {type(other).__name__}')

    def __hash__(self) -> int:
        """
        Returns the hash value of the instance
        :return:
        """
        return hash(self._value)

    @property
    def value(self) -> float:
        """
        Returns the value of the instance
        :return:
        """
        return self._value

    def _toRdf(self, xsdtype: str = 'xsd:float') -> str:
        """
        Converts the instance to a RDF string
        :param xsdtype: XML Schema type to use
        :type xsdtype: XML Schema datatype to use (prefix: "xsd" to be used)
        :return: string representation of the instance as RDF
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
        """
        return self._toRdf('xsd:float')

    def _as_dict(self) -> dict:
        """
        Used by JSON serialization
        :return: Representation of the instance as dict
        """
        return {'value': self._value}

if __name__ == '__main__':
    f = FloatingPoint("1.0")






