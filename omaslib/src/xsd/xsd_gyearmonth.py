import re
from typing import Tuple, Self

from pystrict import strict

from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_gYearMonth(Xsd):
    """
    Implementation of the XML Schema [xsd:gYearMonth](https://www.w3.org/TR/xmlschema11-2/#gYearMonth) datatype
    """
    __year: int
    __month: int
    __tz: Tuple[int, int] | None
    __zulu: bool

    def __init__(self, value: Self | str):
        """
        Constructor of the Xsd_gYearMonth class
        :param value: Xsd_gYearMonth instance or a valid string representing a Xsd_gYearMonth instance
        :type value: Xsd_gYearMonth | str
        :raises OmasErrorValue: if the value is not a valid Xsd_gYearMonth instance
        """
        if isinstance(value, Xsd_gYearMonth):
            self.__year = value.__year
            self.__month = value.__month
            self.__tz = value.__tz
        else:
            if not XsdValidator.validate(XsdDatatypes.gYearMonth, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gYearMonth')
            # or: re.match("[+-]?[0-9]{4}-[0-9]{2}(([+-][0-9]{2}:[0-9]{2})|Z)?", string)
            if not re.match("([+-]?[0-9]{4})-([0-9]{2})((([+-][0-9]{2}):([0-9]{2}))|(Z))?", value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gYearMonth.')
            res = re.split("([+-]?[0-9]{4})-([0-9]{2})((([+-][0-9]{2}):([0-9]{2}))|(Z))?", value)
            if len(res) != 9:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gYearMonth.')
            self.__year = int(res[1])
            self.__month = int(res[2])
            if res[3] == 'Z':
                self.__tz = (0, 0)
                self.__zulu = True
            elif res[3] is not None:
                self.__tz = (int(res[5]), int(res[6]))
                self.__zulu = False
            else:
                self.__tz = None
        if self.__month < 1 or self.__month > 12:
            raise OmasErrorValue(f'Invalid string "{value}" for xsd:gYearMonth.')

    def __str__(self):
        """
        String representation of the Xsd_gYearMonth instance
        :return: String representation of the Xsd_gYearMonth instance
        """
        ff = '05' if self.__year < 0 else '04'
        s = f'{self.__year:{ff}}-{self.__month:02}'
        if self.__tz is not None:
            if self.__zulu:
                s += 'Z'
            else:
                s += f'{self.__tz[0]:0=+3}:{self.__tz[1]:02}'
        return s

    def __repr__(self):
        """
        Constructor string representation of the Xsd_gYearMonth instance
        :return: Constructor string
        """
        return f'Xsd_gYearMonth("{str(self)}")'

    def __eq__(self, other: Self | str | None) -> bool:
        """
        Equality test for Xsd_gYearMonth instance
        :param other: Xsd_gYearMonth instance or a valid string representing a Xsd_gYearMonth instance
        :type other: Xsd_gYearMonth | str | None
        :return: True or False
        :raise OmasErrorValue: if the value is not a valid Xsd_gYearMonth instance
        """
        if other is None:
            return False
        if not isinstance(other, Xsd_gYearMonth):
            other = Xsd_gYearMonth(other)
        if self.__year != other.__year:
            return False
        if self.__month != other.__month:
            return False
        if self.__tz != other.__tz:
            return False
        return True

    def __hash__(self) -> int:
        """
        Hash representation of the Xsd_gYearMonth instance
        :return: Hash value
        """
        return hash(str(self))

    def _as_dict(self) -> dict[str, str]:
        """
        Internal method for JSON serialization (@serializer decorator)
        :return: dict
        """
        return {'value': str(self)}

    @property
    def toRdf(self) -> str:
        """
        RDF representation of the Xsd_gYearMonth instance
        :return: RDF string
        """
        return f'"{str(self)}"^^xsd:gYearMonth'

