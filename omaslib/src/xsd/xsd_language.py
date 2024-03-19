import re
from typing import Self

from pystrict import strict

from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_language(Xsd):
    __value: str

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_language):
            self.__value = value.__value
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
        return f'"{str(self)}"^^xsd:language'

    def __eq__(self, other: Self | str):
        if not isinstance(other, Xsd_language):
            other = Xsd_language(other)
        return self.__value == other.__value

    def __hash__(self) -> int:
        return hash(self.__value)

    def _as_dict(self) -> dict[str, str]:
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        return f'"{str(self)}"^^xsd:language'

