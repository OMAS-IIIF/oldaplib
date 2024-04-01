import re
from typing import Self

from pystrict import strict

from omaslib.src.dtypes.string_literal import StringLiteral
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_name(Xsd):
    __value: str

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_name):
            self.__value = value.__value
        else:
            if not re.match("^[a-zA-Z_][\\w.\\-:_]*$", value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:name.')
            self.__value = value

    @classmethod
    def fromRdf(cls, value: str) -> Self:
        value = StringLiteral.unescaping(value)
        return cls(value)

    def __str__(self):
        return self.__value

    def __repr__(self):
        return f'Xsd_name("{self.__value}")'

    def __eq__(self, other: Self | str | None) -> bool:
        if other is None:
            return False
        if isinstance(other, Xsd_name):
            return self.__value == other.__value
        else:
            return self.__value == other

    def __hash__(self) -> int:
        return hash(self.__value)

    def _as_dict(self) -> dict[str, str]:
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        return f'"{StringLiteral.escaping(self.__value)}"^^xsd:name'

    @property
    def value(self) -> str:
        return self.__value
