from typing import Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_integer(Xsd):
    """
    Base class for XSD Schema integer classes, implements directly the XSD Schema
    [xsd:integer](https://www.w3.org/TR/xmlschema11-2/#integer) datatype
    """
    _value: int

    def __init__(self, value: Xsd | int | str):
        """
        Constructor for Xsd_integer
        :param value: Value to convert to Xsd_integer
        :type value: Xsd | int | str
        :raises OmasErrorValue: Value cannot be converted to Xsd_integer
        """
        if isinstance(value, Xsd_integer):
            self._value = value._value
        elif isinstance(value, int):
            self._value = value
        else:
            try:
                self._value = int(value)
            except ValueError as err:
                raise OmasErrorValue(str(err))

    def __str__(self) -> str:
        """
        String representation of Xsd_integer
        :return: string
        """
        return str(self._value)

    def __repr__(self) -> str:
        """
        Constrctor string representation of Xsd_integer in constructor form
        :return: string
        """
        return f'{type(self).__name__}({str(self._value)})'

    def __hash__(self) -> int:
        """
        Hash value of Xsd_integer
        :return: Hash value
        """
        return hash(self._value)

    def __int__(self) -> int:
        """
        Converts Xsd_integer to integer
        :return: integer value
        """
        return self._value

    def __eq__(self, other: Self | int | None) -> bool:
        """
        Equality check for Xsd_integer
        :param other: Value to compare instance with
        :type other: Xsd | int | None
        :return: True or False
        :raises OmasErrorValue: Value cannot be converted to Xsd_integer
        """
        if other is None:
            return False
        if isinstance(other, Xsd_integer):
            return self._value == other._value
        elif isinstance(other, int):
            return self._value == other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __ne__(self, other: Self | int) -> bool:
        """
        Inequality check for Xsd_integer
        :param other: Value to compare with
        :type other: Xsd | int | None
        :return: True of False
        :raises OmasErrorValue: Value cannot be converted to Xsd_integer
        """
        if other is None:
            return True
        if isinstance(other, Xsd_integer):
            return self._value != other._value
        elif isinstance(other, int):
            return self._value != other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __gt__(self, other: Self | int) -> bool:
        """
        Compare for greater than value
        :param other: Value to compare with
        :return: True or False
        :raises OmasErrorValue: Value cannot be converted to Xsd_integer
        """
        if isinstance(other, Xsd_integer):
            return self._value > other._value
        elif isinstance(other, int):
            return self._value > other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __ge__(self, other: Self | int) -> bool:
        """
        Compare for greater or equal than value
        :param other: Value to compare with
        :return: True or False
        :raises OmasErrorValue: Value cannot be converted to Xsd_integer
        """
        if isinstance(other, Xsd_integer):
            return self._value >= other._value
        elif isinstance(other, int):
            return self._value >= other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __lt__(self, other: Self | int) -> bool:
        """
        Compare for less than value
        :param other: Value to compare with
        :return: True or False
        :raises OmasErrorValue: Value cannot be converted to Xsd_integer
        """
        if isinstance(other, Xsd_integer):
            return self._value < other._value
        elif isinstance(other, int):
            return self._value < other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def __le__(self, other: Self | int) -> bool:
        """
        Compare for less or equal than value
        :param other: Value to compare with
        :return: True or False
        :raises OmasErrorValue: Value cannot be converted to Xsd_integer
        """
        if isinstance(other, Xsd_integer):
            return self._value <= other._value
        elif isinstance(other, int):
            return self._value <= other
        else:
            raise OmasErrorValue(f'Comparison of with {type(other)} not possible')

    def _as_dict(self) -> dict[str, int]:
        """
        Internal method for JSON serialization based on @serializer decorator
        :return: dict
        """
        return {'value': self._value}

    @property
    def toRdf(self) -> str:
        """
        Converts Xsd_integer to RDF string
        :return: RDF string representation of Xsd_integer
        """
        xsddummy, name = type(self).__name__.split('_')
        return f'"{str(self._value)}"^^xsd:{name}'

    @property
    def value(self) -> int:
        """
        Converts Xsd_integer to integer
        :return: integer
        """
        return self._value

