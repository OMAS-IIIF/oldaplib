from typing import Self, Dict

from pystrict import strict

from omaslib.src.dtypes.string_literal import StringLiteral
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

    def __getitem__(self, key: int | slice) -> str:
        return self.__value[key]

    def __eq__(self, other: Self | str | None) -> bool:
        if other is None:
            return False
        if isinstance(other, self.__class__):
            return self.__value == other.__value
        else:
            return self.__value == str(other)

    def __ne__(self, other: Self | str | None) -> bool:
        if other is None:
            return True
        if isinstance(other, self.__class__):
            return self.__value != other.__value
        else:
            return self.__value != str(other)


    def __repr__(self) -> str:
        return f'Xsd_string("{self.__value}")'

    def __hash__(self) -> int:
        return hash(self.__value)

    @classmethod
    def fromRdf(cls, value: str) -> Self:
        return cls(StringLiteral.unescaping(value))

    @property
    def toRdf(self) -> str:
        return f'"{StringLiteral.escaping(str.__str__(self.__value))}"^^xsd:string'

    def _as_dict(self) -> Dict[str, str]:
        return {'value': self.__value}

    @property
    def value(self) -> str:
        return self.__value

if __name__ == '__main__':
    s = Xsd_string("abcdefghijklmnop")
    print(s[-2:].upper())