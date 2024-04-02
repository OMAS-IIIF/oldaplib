from typing import Set, List, Dict, Iterable, Iterator, Self

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class RdfSet:
    __data: Set[Xsd]

    def __init__(self, *args: Iterable[Xsd] | Xsd) -> None:
        self.__data: Set[Xsd] = set()
        if len(args) == 0:  # empty constructor: s = RdfSet()
            return
        elif len(args) == 1:  # Either one element or an iterable: s = RdfSet(Xsd_string('a')
            # or s = RdfSet({Xsd_string('a'), Xsd_string('b')})
            if isinstance(args[0], Iterable):
                values: Iterable[Xsd] = args[0]
                for val in values:
                    if not isinstance(val, Xsd):
                        raise OmasErrorValue("Set elements must be of Subclasses of Xsd.")
                    self.__data.add(val)
            elif isinstance(args[0], Xsd):
                self.__data.add(args[0])
            else:
                raise OmasErrorValue("Set elements must be of Subclasses of Xsd.")
        else:  # Several arguments: s = RdfSet(Xsd_string('a'), Xsd_string('b'))
            for arg in args:
                if not isinstance(arg, Xsd):
                    raise OmasErrorValue("Set elements must be of Subclasses of Xsd.")
                self.__data.add(arg)

    def __eq__(self, other: Self | set[Xsd] | None) -> bool:
        if other is None:
            return False
        if isinstance(other, RdfSet):
            return self.__data == other.__data
        elif isinstance(other, set):
            return self.__data == other
        else:
            raise OmasErrorValue(f"Comparison between RdfSet and {type(other)} not possible")

    def __str__(self) -> str:
        return '(' + ", ".join(map(str, self.__data)) + ')'

    def __repr__(self) -> str:
        return '(' + ", ".join(map(repr, self.__data)) + ')'

    def __contains__(self, val: Xsd) -> bool:
        return val in self.__data

    def __iter__(self) -> Iterator[Xsd]:
        return iter(self.__data)

    def add(self, val: Xsd) -> None:
        if not isinstance(val, Xsd):
            raise OmasErrorValue(f'Cannot add type {type(val)} to RdfSet')
        self.__data.add(val)

    def discard(self, val: Xsd) -> None:
        if not isinstance(val, Xsd):
            raise OmasErrorValue(f'Cannot discard type {type(val)} to RdfSet')
        self.__data.discard(val)

    @property
    def value(self) -> Set[Xsd]:
        return self.__data

    def _as_dict(self) -> Dict[str, List[Xsd]]:
        return {'value': [x for x in self.__data]}

    @property
    def toRdf(self) -> str:
        return f'({" ".join(map(lambda x: x.toRdf, self.__data))})'
