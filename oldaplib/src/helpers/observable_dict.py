import json
from collections import UserDict
from collections.abc import Hashable
from typing import Callable, Self, Iterable, Mapping

from oldaplib.src.enums.action import Action
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.helpers.serializer import serializer


@serializer
class ObservableDict(UserDict):
    __on_change: Callable[[Self], None]
    _changeset: dict[Hashable, AttributeChange]

    def __init__(self,
                 obj: Iterable | Mapping | None = None, *,
                 on_change: Callable[[Self], None] | None = None,
                 validate: bool = False,
                 **kwargs):
        self.__on_change = on_change
        self._changeset = {}
        if obj:
            super().__init__(obj, **kwargs)
        else:
            super().__init__(**kwargs)

    def __setitem__(self, key, value):
        if key in self.data:
            self._changeset[key] = AttributeChange(self.data[key], Action.MODIFY)
        else:
            self._changeset[key] = AttributeChange(None, Action.CREATE)
        if self.__on_change:
            self.__on_change(self.copy())
        super().__setitem__(key, value)

    def __delitem__(self, key):
        self._changeset[key] = AttributeChange(self.data[key], Action.DELETE)
        if self.__on_change:
            self.__on_change(self.copy())
        super().__delitem__(key)


    def copy(self) -> Self:
        return ObservableDict(self.data.copy())

    def set_on_change(self, on_change: Callable[[Self], None]) -> None:
        self.__on_change = on_change

    def _as_dict(self):
        #return self.data
        return {str(key): val for key, val in self.data.items()}

    def clear_changeset(self):
        self._changeset = {}

