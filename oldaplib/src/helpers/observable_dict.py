import json
from collections import UserDict
from typing import Callable, Self, Any, Iterable, Mapping

from pystrict import strict

from oldaplib.src.helpers.serializer import serializer


#@strict
@serializer
class ObservableDict(UserDict):
    __on_change: Callable[[Self], None]

    def __init__(self,
                 obj: Iterable | Mapping | None = None, *,
                 on_change: Callable[[Self], None] | None = None,
                 **kwargs):
        self.__on_change = on_change
        if obj:
            super().__init__(obj, **kwargs)
        else:
            super().__init__(**kwargs)

    def __setitem__(self, key, value):
        if self.__on_change:
            self.__on_change(self.copy())
        super().__setitem__(key, value)

    def __delitem__(self, key):
        if self.__on_change:
            self.__on_change(self.copy())
        super().__delitem__(key)


    def copy(self) -> Self:
        return ObservableDict(self.data.copy())

    def set_on_change(self, on_change: Callable[[Self], None]) -> None:
        self.__on_change = on_change

    def _as_dict(self):
        return self.data

    def changeset_clear(self):
        pass

