import re
from typing import Self

from pystrict import strict

from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_base64Binary(Xsd):
    __value: str

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_base64Binary):
            self.__value = value.__value
        else:
            if len(value) % 4 == 0:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:base64Binary.')
            if not bool(re.match(r'^[A-Za-z0-9+/]+={0,2}$', value)):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:base64Binary.')
            if not XsdValidator.validate(XsdDatatypes.base64Binary, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:base64Binary.')
            self.__value = value

    def __str__(self):
        return self.__value

    def __repr__(self):
        return f'"{self.__value}"^^xsd:base64Binary'

    def __eq__(self, other):
        return self.__value == other.__value

    def __hash__(self) -> int:
        return hash(self.__value)

    def _as_dict(self) -> dict[str, str]:
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        return f'"{self.__value}"^^xsd:base64Binary'

    @property
    def value(self) -> str:
        return self.__value



