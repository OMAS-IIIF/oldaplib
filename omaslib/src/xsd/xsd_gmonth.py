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
    __month: int
    __tz: Tuple[int, int] | None
    __zulu: bool

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_gMonth):
            self.__month = value.__month
            self.__tz = value.__tz
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
        if self.__month < 1 or self.__month > 12:
            raise OmasErrorValue(f'Invalid string "{value}" for xsd:gMonth.')

    def __str__(self):
        s = f'--{self.__month:02}'
        if self.__tz is not None:
            if self.__zulu:
                s += 'Z'
            else:
                s += f'{self.__tz[0]:0=+3}:{self.__tz[1]:02}'
        return s

    def __repr__(self):
        return f'Xsd_gMonth("{str(self)}")'

    def __eq__(self, other: Self | str | None) -> bool:
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
        return hash(str(self))

    def _as_dict(self) -> dict[str, str]:
        return {'value': str(self)}

    @property
    def toRdf(self) -> str:
        return f'"{str(self)}"^^xsd:gMonth'
