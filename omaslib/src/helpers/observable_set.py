from typing import List, Callable, Any, Iterable, Set, Self

from pystrict import strict

from omaslib.src.helpers.datatypes import Action


@strict
class ObservableSet(Set):

    def __init__(self, items: Iterable | None = None, onChange: Callable[[Action], None] = None):
        self.__onChange = onChange
        if items is None:
            super().__init__(set())
        else:
            super().__init__(items)

    def __repr__(self) -> str:
        l = [repr(x) for x in self]
        return ", ".join(l)

    def update(self, items: Iterable):
        super().update(items)
        self.__onChange(Action.MODIFY)

    def intersection_update(self, items: Iterable):
        super().intersection_update(items)
        self.__onChange(Action.MODIFY)

    def difference_update(self, items: Iterable):
        super().difference_update(items)
        self.__onChange(Action.MODIFY)

    def symmetric_difference_update(self, items: Iterable):
        super().symmetric_difference_update(items)
        self.__onChange(Action.MODIFY)

    def add(self, item: Any) -> None:
        super().add(item)
        self.__onChange(Action.MODIFY)

    def remove(self, item: Any) -> None:
        super().remove(item)
        self.__onChange(Action.MODIFY)

    def discard(self, item: Any):
        super().discard(item)
        self.__onChange(Action.DELETE)

    def pop(self):
        super().pop()
        self.__onChange(Action.DELETE)

    def clear(self) -> None:
        super().clear()
        self.__onChange(Action.DELETE)

    def copy(self) -> Self:
        return ObservableSet(super().copy())

    def _as_dict(self):
        return {'set': list(self)}


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
