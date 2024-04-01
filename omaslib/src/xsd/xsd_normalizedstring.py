import re
from typing import Self

from pystrict import strict

from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from omaslib.src.dtypes.string_literal import StringLiteral
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_normalizedString(Xsd):
    __value: str

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_normalizedString):
            self.__value = value.__value
        else:
            if not XsdValidator.validate(XsdDatatypes.normalizedString, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:normalizedString.')
            if re.match("^[^\r\n\t]*$", value) is None:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:normalizedString.')
            self.__value = value

    @classmethod
    def fromRdf(cls, value: str) -> Self:
        value = StringLiteral.unescaping(value)
        return cls(value)

    def __str__(self):
        return self.__value

    def __repr__(self):
        return f'{type(self).__name__}("{self.__value}")'

    def __eq__(self, other: Self | str | None) -> bool:
        if other is None:
            return False
        if not isinstance(other, Xsd_normalizedString):
            other = Xsd_normalizedString(other)
        return self.__value == other.__value

    def __hash__(self) -> int:
        return super().__hash__()

    @property
    def toRdf(self) -> str:
        return f'"{StringLiteral.escaping(str(self))}"^^xsd:normalizedString'

    def _as_dict(self) -> dict[str, str]:
        return {'value': self.__value}

    @property
    def value(self) -> str:
        return self.__value
