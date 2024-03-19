from typing import Set, List, Dict

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class RdfSet:
    __data: Set[Xsd]

    def __init__(self, value: Set[Xsd] | List[Xsd]):
        self.__data: Set[Xsd] = set()
        for val in value:
            if not isinstance(val, Xsd):
                raise OmasErrorValue("Set elements must be of Subclasses of Xsd.")
            self.__data.add(val)

    def __str__(self) -> str:
        return '(' + ", ".join(map(str, self.__data)) + ')'

    def __repr__(self) -> str:
        return '(' + ", ".join(map(repr, self.__data)) + ')'

    def __contains__(self, val: Xsd) -> bool:
        return val in self.__data

    def _as_dict(self) -> Dict[str, List[T]]:
        return {'value': [x for x in self.__data]}
