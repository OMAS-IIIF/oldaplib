import re
from typing import Tuple, Self

from pystrict import strict

from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_gMonth(Xsd):
    """
    Implements the XML Schema [xsd:gMonth](https://www.w3.org/TR/xmlschema11-2/#gMonth) datatype
    """
    __month: int
    __tz: Tuple[int, int] | None
    __zulu: bool | None

    def __init__(self, value: Self | str):
        """
        Constructor of Xsd_gMonth class
        :param value: An Xsd_gMonth instance or a valid string conforming to the
        :type value: Xsd | str
        :raises OmasErrorValue: If a Xsd_gMonth instance or string is not valid
        """
        if isinstance(value, Xsd_gMonth):
            self.__month = value.__month
            self.__tz = value.__tz
            self.__zulu = value.__zulu
        else:
            if not XsdValidator.validate(XsdDatatypes.gMonth, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gMonth.')
            res = re.split("--([0-9]{2})((([+-][0-9]{2}):([0-9]{2}))|(Z))?", value)
            if len(res) != 8:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gMonth.')
            self.__month = int(res[1])
            if res[2] == 'Z':
                self.__tz = (0, 0)
                self.__zulu = True
            elif res[2] is not None:
                self.__tz = (int(res[4]), int(res[5]))
                self.__zulu = False
            else:
                self.__tz = None
                self.__zulu = None
        if self.__month < 1 or self.__month > 12:
            raise OmasErrorValue(f'Invalid string "{value}" for xsd:gMonth.')

    def __str__(self):
        """
        String representation of Xsd_gMonth instance
        :return:
        """
        s = f'--{self.__month:02}'
        if self.__tz is not None:
            if self.__zulu:
                s += 'Z'
            else:
                s += f'{self.__tz[0]:0=+3}:{self.__tz[1]:02}'
        return s

    def __repr__(self):
        """
        Constructor string representation of Xsd_gMonth instance
        :return: Constructor string
        """
        return f'Xsd_gMonth("{str(self)}")'

    def __eq__(self, other: Self | str | None) -> bool:
        """
        Equality check for Xsd_gMonth instance
        :param other: Other Xsd_gMonth instance or valid gMonth string
        :type other: Xsd_gMonth | str | None
        :return: True or False
        :raises OmasErrorValue: If Xsd_gMonth instance or string is not valid
        """
        if other is None:
            return False
        if not isinstance(other, Xsd_gMonth):
            other = Xsd_gMonth(other)
        if self.__month != other.__month:
            return False
        if self.__tz != other.__tz:
            return False
        return True

    def __hash__(self) -> int:
        """
        Hashing function for Xsd_gMonth instance
        :return: Hash value
        """
        return hash(str(self))

    def _as_dict(self) -> dict[str, str]:
        """
        Internal method for serializing Xsd_gMonth instance to JSON (@serilaizer decorator)
        :return: dict
        """
        return {'value': str(self)}

    @property
    def toRdf(self) -> str:
        """
        Converts Xsd_gMonth instance to RDF string
        :return: RDF string
        """
        return f'"{str(self)}"^^xsd:gMonth'

