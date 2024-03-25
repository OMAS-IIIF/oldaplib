import re
from typing import Self

from pystrict import strict

from omaslib.src.enums.language import Language
from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_language(Xsd):
    __value: str

    def __init__(self, value: Self | Language | str):
        if isinstance(value, Xsd_language):
            self.__value = value.__value
        elif isinstance(value, Language):
            self.__value = value.name.lower()
        else:
            if not XsdValidator.validate(XsdDatatypes.language, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:language.')
            if not re.match('^[a-zA-Z]{2}(-[a-zA-Z]{2})?$', value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:language.')
            # if re.match(".*[\n\r\t].*", value) is not None:
            #     raise OmasErrorValue(f'Invalid string "{value}" for xsd:language.')
            self.__value = value

    def __str__(self):
        return self.__value

    def __repr__(self):
        return f'Xsd_language("{self.__value}")'

    def __eq__(self, other: Self | str | None) -> bool:
        if other is None:
            return False
        if not isinstance(other, Xsd_language):
            other = Xsd_language(other)
        return self.__value == other.__value

    def __hash__(self) -> int:
        return hash(self.__value)

    def _as_dict(self) -> dict[str, str]:
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        return f'"{self.__value}"^^xsd:language'

