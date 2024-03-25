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
    __value: str

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_NMTOKEN):
            self.__value = value.__value
        else:
            if not XsdValidator.validate(XsdDatatypes.NMTOKEN, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:NMTOKEN.')
            if not re.match("^[a-zA-Z_:.][a-zA-Z0-9_.:-]*$", value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:NMTOKEN.')
            self.__value = value

    def __str__(self):
        return self.__value

    def __repr__(self):
        return f'Xsd_NMTOKEN("{str(self)}")'

    def __eq__(self, other: Self | str | None) -> bool:
        if other is None:
            return False
        if not isinstance(other, Xsd_NMTOKEN):
            return self.__value != other
        else:
            return self.__value == other.__value

    def __hash__(self) -> int:
        return hash(self.__value)

    def _as_dict(self) -> dict[str, str]:
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        return f'"{str(self)}"^^xsd:NMTOKEN'

    @property
    def value(self) -> str:
        return self.__value
