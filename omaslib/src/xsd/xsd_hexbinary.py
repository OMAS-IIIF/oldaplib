import re
from typing import Self

from pystrict import strict

from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_hexBinary(Xsd):
    """
    Implementation of the XML Schema [xsd:HexBinary](https://www.w3.org/TR/xmlschema11-2/#hexBinary) datatype
    """
    __value: str

    def __init__(self, value: Self | str):
        """
        Constructor of the Xsd_hexBinary class
        :param value: Xsd_hexBinary instance or a valid string
        :type value: Xsd_hexBinary | str
        :raises OmasErrorValue: If the value is not a valid Xsd_hexBinary instance
        """
        if isinstance(value, Xsd_hexBinary):
            self.__value = value.__value
        else:
            if not bool(re.match(r'^[0-9A-Fa-f]*$', value)) or len(value) % 2 != 0:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:hexBinary.')
            if not XsdValidator.validate(XsdDatatypes.hexBinary, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:hexBinary.')
            self.__value = value

    def __str__(self):
        """
        String representation of the Xsd_hexBinary instance
        :return: String representation of the Xsd_hexBinary instance
        """
        return self.__value

    def __repr__(self):
        """
        Constructor string representation of the Xsd_hexBinary instance
        :return: Constructor string
        """
        return f'Xsd_hexBinary("{str(self)}")'

    def __eq__(self, other: Self | str | None) -> bool:
        """
        Equality test for Xsd_hexBinary instance
        :param other: Xsd_hexBinary instance or a valid string
        :return: True or False
        :raises OmasErrorValue: If the value is not a valid Xsd_hexBinary instance
        """
        if other is None:
            return False
        if isinstance(other, Xsd_hexBinary):
            return self.__value == other.__value
        else:
            return self.__value == Xsd_hexBinary(str(other))

    def __hash__(self) -> int:
        """
        Hash value of the Xsd_hexBinary instance
        :return: Hash value
        """
        return hash(self.__value)

    def _as_dict(self) -> dict[str, str]:
        """
        Internal method for JSON serialization (@serializer decorator)
        :return: dict
        """
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        """
        RDF representation of the Xsd_hexBinary instance
        :return: RDF representation of the Xsd_hexBinary instance
        """
        return f'"{str(self)}"^^xsd:hexBinary'

    @property
    def value(self) -> str:
        """
        String representation of the Xsd_hexBinary instance
        :return: String representation of the Xsd_hexBinary instance
        """
        return self.__value
