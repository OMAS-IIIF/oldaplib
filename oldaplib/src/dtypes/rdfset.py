from typing import Set, List, Dict, Iterable, Iterator, Self, TypeVar, Generic

from pystrict import strict

from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorType, OldapErrorInconsistency
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd

T = TypeVar("T")


@serializer
class RdfSet(Generic[T], Notify):
    _data: Set[T]

    def __init__(self, *args: Self | set[T] | list[T] | tuple[T] | T,
                 value: Self | set[T] | list[T] | tuple[T] | T | None = None) -> None:
        self._data: Set[T] = set()
        Notify.__init__(self)
        if len(args) == 0:
            if value is None:
                return
            else:
                if isinstance(value, RdfSet):
                    self._data = value._data
                elif isinstance(value, (set | list | tuple)):
                    for val in value:
                        self._data.add(val)
                else:
                    self._data.add(value)
        elif len(args) == 1:
            if isinstance(args[0], RdfSet):
                self._data = args[0]._data
            elif isinstance(args[0], (set | list | tuple)):
                for val in args[0]:
                    self._data.add(val)
            else:
                self._data.add(args[0])
        else:
            for val in args:
                self._data.add(val)

    def __len__(self) -> int:
        return len(self._data)

    def __eq__(self, other: Self | set[T] | None) -> bool:
        if other is None:
            return False
        if isinstance(other, RdfSet):
            return self._data == other._data
        elif isinstance(other, set):
            return self._data == other
        else:
            raise OldapErrorValue(f"Comparison between RdfSet and {type(other)} not possible")

    def __gt__(self, other: Self | set[T]) -> bool:
        if isinstance(other, RdfSet):
            return self._data > other._data
        if isinstance(other, set):
            return self._data > other
        raise OldapErrorType(f'Cannot compare {type(self).__name__} to {type(other).__name__}')

    def __ge__(self, other: Self | set[T]) -> bool:
        if isinstance(other, RdfSet):
            return self._data >= other._data
        if isinstance(other, set):
            return self._data >= other
        raise OldapErrorType(f'Cannot compare {type(self).__name__} to {type(other).__name__}')

    def __lt__(self, other: Self | set[T]) -> bool:
        if isinstance(other, RdfSet):
            return self._data < other._data
        if isinstance(other, set):
            return self._data < other
        raise OldapErrorType(f'Cannot compare {type(self).__name__} to {type(other).__name__}')

    def __le__(self, other: Self | set[T]) -> bool:
        if isinstance(other, RdfSet):
            return self._data <= other._data
        if isinstance(other, set):
            return self._data <= other
        raise OldapErrorType(f'Cannot compare {type(self).__name__} to {type(other).__name__}')

    def __str__(self) -> str:
        return '(' + ", ".join(map(str, self._data)) + ')'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(' + ", ".join(map(repr, self._data)) + ')'

    def __contains__(self, val: T) -> bool:
        return val in self._data

    def __iter__(self) -> Iterator[T]:
        return iter(self._data)

    def add(self, val: T) -> None:
        self.notify()
        self._data.add(val)

    def discard(self, val: T) -> None:
        self.notify()
        self._data.discard(val)

    @property
    def value(self) -> set[T]:
        return self._data

    def _as_dict(self) -> Dict[str, List[T]]:
        return {'value': [x for x in self._data]}

    @property
    def toRdf(self) -> str:
        return f'({" ".join(map(lambda x: x.toRdf, self._data))})'

    @property
    def value(self) -> set[T]:
        return self._data

if __name__ == "__main__":
    g = RdfSet[str](['a', 'b', 'c'])
    print(repr(g))
