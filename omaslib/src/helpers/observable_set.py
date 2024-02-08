"""
# Observalbe Set

This module implements a set which is observable. That means, that a callback function/method may
be given that is called whenever the set is changed (adding/removing of items)
"""
import json
from typing import List, Callable, Any, Iterable, Set, Self

from pystrict import strict

from omaslib.src.helpers.datatypes import Action
from omaslib.src.helpers.serializer import serializer


@strict
@serializer
class ObservableSet(Set):
    """
    The ObservableSet class is a subclass of `Set` which allows the notification if the set is changed, that
    is items are added or removed. For this purpose, a callback function can be added to the set which is
    called whenever the set changes.
    """
    __on_change: Callable[[Self, Any], None]
    __on_change_data: Any

    def __init__(self,
                 setitems: Iterable | None = None,
                 on_change: Callable[[Self, Any], None] = None,
                 on_change_data: Any = None) -> None:
        """
        Constructor of the ObservableSet class

        :param setitems: The items the ObservableSet will be initialized with
        :param on_change: Callback function to be called when an item is added/removed
        :param on_change_data: data supplied to the callback function
        """
        self.__on_change = on_change
        self.__on_change_data = on_change_data
        if setitems is None:
            super().__init__(set())
        else:
            super().__init__(setitems)

    def __repr__(self) -> str:
        l = [repr(x) for x in self]
        return ", ".join(l)

    def __str__(self) -> str:
        return super().__str__()

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
        if self.__on_change is not None:
            self.__on_change(self.copy(), self.__on_change_data)
        super().update(items)

    def intersection_update(self, items: Iterable):
        if self.__on_change is not None:
            self.__on_change(self.copy(), self.__on_change_data)
        super().intersection_update(items)

    def difference_update(self, items: Iterable):
        if self.__on_change is not None:
            self.__on_change(self.copy(), self.__on_change_data)
        super().difference_update(items)

    def symmetric_difference_update(self, items: Iterable):
        if self.__on_change is not None:
            self.__on_change(self.copy(), self.__on_change_data)
        super().symmetric_difference_update(items)

    def add(self, item: Any) -> None:
        if self.__on_change is not None:
            self.__on_change(self.copy(), self.__on_change_data)
        super().add(item)

    def remove(self, item: Any) -> None:
        if self.__on_change is not None:
            self.__on_change(self.copy(), self.__on_change_data)
        super().remove(item)

    def discard(self, item: Any):
        if self.__on_change is not None:
            self.__on_change(self.copy(), self.__on_change_data)
        super().discard(item)

    def pop(self):
        if self.__on_change is not None:
            self.__on_change(self.copy(), self.__on_change_data)
        super().pop()

    def clear(self) -> None:
        if self.__on_change is not None:
            self.__on_change(self.copy(), self.__on_change_data)
        super().clear()

    def copy(self) -> Self:
        return ObservableSet(super().copy(), on_change=self.__on_change)

    def _as_dict(self):
        return {'setitems': list(self)}

    def asSet(self):
        return super().copy()


if __name__ == '__main__':
    @serializer
    class Test:
        def __init__(self, data: ObservableSet[str] = None, on_change: Callable[[Self], None] = None):
            self.__data = ObservableSet(setitems=data, on_change=self.__changing)

        @property
        def data(self) -> Any:
            return self.__data

        def __changing(self, old: Self, data: Any = None) -> None:
            print("--->", old)

        def _as_dict(self):
            return {
                'data': self.__data
            }

    t = Test()
    t.data.add('x')
    t.data.add('a')
    t.data.add('b')
    print(t.data)
    jsonstr = json.dumps(t, default=serializer.encoder_default)
    print(jsonstr)
    t2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
    print(t2.data)
    gaga = t2.data.asSet()
    print(type(gaga))
