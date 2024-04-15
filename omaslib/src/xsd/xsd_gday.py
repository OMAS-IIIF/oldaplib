import re
from typing import Tuple, Self

from pystrict import strict

from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_gDay(Xsd):
    """
    Implements the XML Schema [xsd:gDay](https://www.w3.org/TR/xmlschema11-2/#gDay) datatpye
    """
    __day: int
    __tz: Tuple[int, int] | None
    __zulu: bool | None

    def __init__(self, value: Self | str):
        """
        Constructor for the Xsd_gDay class
        :param value: A Xsd_gDay object or a string valid for xsd:gDay
        :type value: Xsd_gDay | str
        :raises OmasErrorValue: If the value is not a valid xsd:gDay
        """
        if isinstance(value, Xsd_gDay):
            self.__day = value.__day
            self.__tz = value.__tz
            self.__zulu = value.__zulu
        else:
            if not XsdValidator.validate(XsdDatatypes.gDay, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gDay')
            res = re.split("---([0-9]{2})((([+-][0-9]{2}):([0-9]{2}))|(Z))?", value)
            if len(res) != 8:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gDay.')
            self.__day = int(res[1])
            if res[2] == 'Z':
                self.__tz = (0, 0)
                self.__zulu = True
            elif res[2] is not None:
                self.__tz = (int(res[4]), int(res[5]))
                self.__zulu = False
            else:
                self.__tz = None
                self.__zulu = None
        if self.__day < 1 or self.__day > 31:
            raise OmasErrorValue(f'Invalid string "{value}" for xsd:gDay.')

    def __str__(self):
        """
        String representation of the Xsd_gDay object
        :return:
        """
        s = f'---{self.__day:02}'
        if self.__tz is not None:
            if self.__zulu:
                s += 'Z'
            else:
                s += f'{self.__tz[0]:0=+3}:{self.__tz[1]:02}'
        return s

    def __repr__(self):
        """
        Constructor string representation of the Xsd_gDay object
        :return: Constructor string
        """
        return f'Xsd_gDay("{str(self)}")'

    def __eq__(self, other: Self | str | None) -> bool:
        """
        Equality check for Xsd_gDay object
        :param other: Another Xsd_gDay object
        :type other: Xsd_gDay | str | None
        :return: True or False
        :raise OmasErrorValue: If the value is not a valid xsd:gDay
        """
        if other is None:
            return False
        if not isinstance(other, Xsd_gDay):
            other = Xsd_gDay(other)
        if self.__day != other.__day:
            return False
        if self.__tz != other.__tz:
            return False
        return True

    def __hash__(self) -> int:
        """
        Hash representation of the Xsd_gDay object
        :return: Hash value
        """
        return super().__hash__()

    def _as_dict(self) -> dict[str, str]:
        """
        Internal method for JSON serialization (@serializer decorator)
        :return: dict
        """
        return {'value': str(self)}

    @property
    def toRdf(self) -> str:
        """
        Converts the Xsd_gDay object to RDF string
        :return: RDF string
        """
        return f'"{str(self)}"^^xsd:gDay'

