import re
from typing import Self

from pystrict import strict

from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from omaslib.src.helpers.oldap_string_literal import OldapStringLiteral
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_token(Xsd):
    __value: str

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_token):
            self.__value = value.__value
        else:
            if not XsdValidator.validate(XsdDatatypes.token, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:token.')
            if not re.match("^[^\\s]+(\\s[^\\s]+)*$", value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:token.')
            if re.match(".*[\n\r\t].*", value) is not None:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:token.')
            self.__value = value

    @classmethod
    def fromRdf(cls, value: str) -> Self:
        value = OldapStringLiteral.unescaping(value)
        return cls(value)

    def __str__(self):
        return self.__value

    def __repr__(self):
        return f'"{OldapStringLiteral.escaping(str(self))}"^^xsd:token'

    def __eq__(self, other: Self | str):
        if not isinstance(other, Xsd_token):
            other = Xsd_token(other)
        return self.__value == other.__value

    def __hash__(self) -> int:
        return super().__hash__()

    def _as_dict(self) -> dict[str, str]:
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        return f'"{OldapStringLiteral.escaping(str(self))}"^^xsd:token'

    @property
    def value(self) -> str:
        return self.__value
