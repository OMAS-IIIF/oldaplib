from typing import Self, Dict

from pystrict import strict

from omaslib.src.helpers.oldap_string_literal import OldapStringLiteral
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_string(Xsd):
    __value: str

    def __init__(self, value: Self | str):
        if isinstance(value, str):
            self.__value = value
        else:
            self.__value = str(value)

    def __str__(self) -> str:
        return self.__value

    def __repr__(self) -> str:
        return f'"{OldapStringLiteral.escaping(self.__value)}"^^xsd:string'

    def __hash__(self) -> int:
        return hash(self.__value)

    @classmethod
    def fromRdf(cls, value: str) -> Self:
        return cls(OldapStringLiteral.unescaping(value))

    @property
    def toRdf(self) -> str:
        return f'"{OldapStringLiteral.escaping(str.__str__(self))}"^^xsd:string'

    def _as_dict(self) -> Dict[str, str]:
        return {'value': self.__value}

    @property
    def value(self) -> str:
        return self.__value

