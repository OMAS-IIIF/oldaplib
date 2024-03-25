from typing import Any, Self, Dict

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_boolean(Xsd):
    __value: bool

    def __init__(self, value: Any):
        if isinstance(value, str):
            if value.lower() in ('yes', 'true', 't', 'y', '1'):
                self.__value = True
            elif value.lower() in ('no', 'false', 'f', 'n', '0'):
                self.__value = False
            else:
                raise OmasErrorValue('No valid string for boolean value.')
        else:
            self.__value = bool(value)

    def __str__(self) -> str:
        return str(self.__value).lower()

    def __repr__(self) -> str:
        return f'"{str(self.__value).lower()}"^^xsd:boolean'

    def __bool__(self) -> bool:
        return self.__value

    def __eq__(self, other: Any | None) -> bool:
        if other is None:
            return False
        if not isinstance(other, Xsd_boolean):
            other = Xsd_boolean(other)
        return self.__value == other.__value

    @property
    def toRdf(self) -> str:
        return f'"{str(self.__value).lower()}"^^xsd:boolean'

    def _as_dict(self) -> dict[str, str]:
        return {'value': str(self.__value)}

    @property
    def value(self) -> bool:
        return self.__value
