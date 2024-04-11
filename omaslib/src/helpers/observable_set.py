"""
# Observalbe Set

This module implements a set which is observable. That means, that a callback function/method may
be given that is called whenever the set is changed (adding/removing of items)
"""
import json
from typing import List, Callable, Any, Iterable, Set, Self

from pystrict import strict

from omaslib.src.enums.action import Action
from omaslib.src.helpers.omaserror import OmasErrorKey
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
        pass

    def __ior__(self, other: Self) -> Self:
        tmp_copy = self.copy()
        super().__ior__(other)
        if self.__on_change is not None:
            self.__on_change(tmp_copy, self.__on_change_data)
        return self

    def __and__(self, other: Self) -> Self:
        return ObservableSet(super().__and__(other))

    def __iand__(self, other: Self) -> Self:
        tmp_copy = self.copy()
        super().__iand__(other)
        if self.__on_change is not None:
            self.__on_change(tmp_copy, self.__on_change_data)
        return self

    def __rsub__(self, other: Self) -> Self:
        pass

    def __sub__(self, other: Self) -> Self:
        return ObservableSet(super().__sub__(other))

    def __isub__(self, other: Self) -> Self:
        tmp_copy = self.copy()
        super().__isub__(other)
        if self.__on_change is not None:
            self.__on_change(tmp_copy, self.__on_change_data)
        return self


    def __eq__(self, other: Self) -> Self:
        return set(self) == set(other)

    def update(self, items: Iterable):
        tmp_copy = self.copy()
        super().update(items)
        if self.__on_change is not None:
            self.__on_change(tmp_copy, self.__on_change_data)


    def intersection_update(self, items: Iterable):
        tmp_copy = self.copy()
        super().intersection_update(items)
        if self.__on_change is not None:
            self.__on_change(tmp_copy, self.__on_change_data)

    def difference_update(self, items: Iterable):
        tmp_copy = self.copy()
        super().difference_update(items)
        if self.__on_change is not None:
            self.__on_change(tmp_copy, self.__on_change_data)

    def symmetric_difference_update(self, items: Iterable):
        tmp_copy = self.copy()
        super().symmetric_difference_update(items)
        if self.__on_change is not None:
            self.__on_change(tmp_copy, self.__on_change_data)

    def add(self, item: Any) -> None:
        tmp_copy = self.copy()
        super().add(item)
        if self.__on_change is not None:
            self.__on_change(tmp_copy, self.__on_change_data)

    def remove(self, item: Any) -> None:
        tmp_copy = self.copy()
        super().remove(item)
        if self.__on_change is not None:
            self.__on_change(tmp_copy, self.__on_change_data)

    def discard(self, item: Any):
        tmp_copy = self.copy()
        super().discard(item)
        if self.__on_change is not None:
            self.__on_change(tmp_copy, self.__on_change_data)
        return self

    def pop(self):
        tmp_copy = self.copy()
        len1 = len(self)
        super().pop()
        len2 = len(self)
        if len1 == len2:
            return
        if self.__on_change is not None:
            self.__on_change(tmp_copy, self.__on_change_data)

    def clear(self) -> None:
        tmp_copy = self.copy()
        super().clear()
        if self.__on_change is not None:
            self.__on_change(tmp_copy, self.__on_change_data)

    def copy(self) -> Self:
        return ObservableSet(super().copy(), on_change=self.__on_change)

    @property
    def toRdf(self) -> str:
        l = [x.toRdf if getattr(x, "toRdf", None) else x for x in self]
        return ", ".join(l)


    def _as_dict(self):
        return {'setitems': list(self)}

    def asSet(self):
        return super().copy()

    def on_change(self, func: Callable[[Self, Any], None], data: Any) -> None:
        self.__on_change = func
        self.__on_change_data = data

