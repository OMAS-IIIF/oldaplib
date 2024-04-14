import re
from typing import Self

from pystrict import strict

from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_NMTOKEN(Xsd):
    """
    Implements the XML Schema [xsd:NMTOKEN](https://www.w3.org/TR/xmlschema11-2/#NMTOKEN) datatype
    """
    __value: str

    def __init__(self, value: Self | str):
        """
        Constructor of the Xsd_NMTOKEN class.
        :param value: Either a Xsd_NMTOKEN instance or a string conforming to the syntax of Xsd_NMTOKEN.
        :type value: Xsd_NMTOKEN | str
        :raises OmasErrorValue: If the value is not a valid Xsd_NMTOKEN string.
        """
        if isinstance(value, Xsd_NMTOKEN):
            self.__value = value.__value
        else:
            if not XsdValidator.validate(XsdDatatypes.NMTOKEN, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:NMTOKEN.')
            if not re.match("^[a-zA-Z_:.][a-zA-Z0-9_.:-]*$", value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:NMTOKEN.')
            self.__value = value

    def __str__(self):
        """
        String representation of the Xsd_NMTOKEN instance.
        :return: String representation of the Xsd_NMTOKEN instance.
        :rtype: str
        """
        return self.__value

    def __repr__(self):
        """
        Python constructor string representation of the Xsd_NMTOKEN instance.
        :return: Python constructor string representation of the Xsd_NMTOKEN instance.
        :rtype: str
        """
        return f'Xsd_NMTOKEN("{str(self)}")'

    def __eq__(self, other: Self | str | None) -> bool:
        """
        Equality check for Xsd_NMTOKEN instances.
        :param other: Xsd_NMTOKEN instance or string to compare to.
        :type other: Xsd_NMTOKEN | str | None
        :return: True or False
        :rtype: bool
        :raises OmasErrorValue: If the value is not a valid Xsd_NMTOKEN instance.
        """
        if other is None:
            return False
        if not isinstance(other, Xsd_NMTOKEN):
            other = Xsd_NMTOKEN(other)
        return self.__value == other.__value

    def __hash__(self) -> int:
        """
        Hash method for the Xsd_NMTOKEN instance.
        :return: Hash value of the Xsd_NMTOKEN instance.
        :rtype: int
        """
        return hash(self.__value)

    def _as_dict(self) -> dict[str, str]:
        """
        Internal method to convert the Xsd_NMTOKEN instance to a JSON dict (@serializer decorator)
        :return: dict
        """
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        """
        Converts the Xsd_NMTOKEN instance to a RDF string.
        :return: RDF string representation of the Xsd_NMTOKEN instance.
        :rtype: str
        """
        return f'"{str(self)}"^^xsd:NMTOKEN'

    @property
    def value(self) -> str:
        """
        Converts the Xsd_NMTOKEN instance to a string.
        :return: String representation of the Xsd_NMTOKEN instance.
        """
        return self.__value
