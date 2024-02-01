from typing import List, Callable, Any, Iterable, Set, Self

from pystrict import strict

from omaslib.src.helpers.datatypes import Action



@strict
class ObservableSet(Set):
    __on_change: Callable[[], None]

    def __init__(self, setitems: Iterable | None = None, on_change: Callable[[Self], None] = None):
        self.__on_change = on_change
        if setitems is None:
            super().__init__(set())
        else:
            super().__init__(setitems)

    def __repr__(self) -> str:
        l = [repr(x) for x in self]
        return ", ".join(l)

    def __or__(self, other: Self) -> Self:
        if isinstance(other, ObservableSet):
            return ObservableSet(super().__or__(other))
        return NotImplemented

    def __ror__(self, other: Self) -> Self:
        return self.__or__(other)

    def __rsub__(self, other: Self) -> Self:
        return self.__sub__(other)

    def __sub__(self, other: Self) -> Self:
        if isinstance(other, ObservableSet):
            return ObservableSet(super().__sub__(other))
        return NotImplemented

    def update(self, items: Iterable):
        self.__on_change(self.copy())
        super().update(items)

    def intersection_update(self, items: Iterable):
        self.__on_change(self.copy())
        super().intersection_update(items)

    def difference_update(self, items: Iterable):
        self.__on_change(self.copy())
        super().difference_update(items)

    def symmetric_difference_update(self, items: Iterable):
        self.__on_change(self.copy())
        super().symmetric_difference_update(items)

    def add(self, item: Any) -> None:
        self.__on_change(self.copy())
        super().add(item)

    def remove(self, item: Any) -> None:
        self.__on_change(self.copy())
        super().remove(item)

    def discard(self, item: Any):
        self.__on_change(self.copy())
        super().discard(item)

    def pop(self):
        self.__on_change(self.copy())
        super().pop()

    def clear(self) -> None:
        self.__on_change(self.copy())
        super().clear()

    def copy(self) -> Self:
        return ObservableSet(super().copy())

    def _as_dict(self):
        return {'setitems': list(self)}


if __name__ == '__main__':
    class Test:
        def __init__(self):
            self.__data = ObservableSet(onChange=self.__changing)

        @property
        def data(self) -> Any:
            return self.__data

        def __changing(self, action: Action) -> None:
            print("--->", Action)

    t = Test()
    t.data.add('x')
    t.data.add('a')
    t.data.add('b')
    print(t.data)
    tt = t.data.copy()
    tt.add('w')
    print(set(tt) - set(t.data))
    print(set(t.data) - set(tt))
    gaga = ObservableSet(['a', 'b', 'c'])
    print(gaga)
