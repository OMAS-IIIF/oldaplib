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
    __value: str

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_hexBinary):
            self.__value = value.__value
        else:
            if not bool(re.match(r'^[0-9A-Fa-f]*$', value)) or len(value) % 2 != 0:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:hexBinary.')
            if not XsdValidator.validate(XsdDatatypes.hexBinary, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:hexBinary.')
            self.__value = value

    def __str__(self):
        return self.__value

    def __repr__(self):
        return f'Xsd_hexBinary("{str(self)}")'

    def __eq__(self, other: Self | str | None) -> bool:
        if other is None:
            return False
        if isinstance(other, Xsd_hexBinary):
            return self.__value == other.__value
        else:
            return self.__value == other

    def __hash__(self) -> int:
        return hash(self.__value)

    def _as_dict(self) -> dict[str, str]:
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        return f'"{str(self)}"^^xsd:hexBinary'

    @property
    def value(self) -> str:
        return self.__value
