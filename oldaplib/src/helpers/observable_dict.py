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
                 obsdict: dict | None = None,
                 validate: bool = False,
                 **kwargs):
        """
        Initializes a new instance of the class with optional data and settings for
        notifications and validation.

        :param obj: An optional iterable or mapping containing initial data for the
            instance. Defaults to None.
        :type obj: Iterable | Mapping | None
        :param on_change: A callable function that will be invoked when a change is made
            to the instance. The function is passed the instance itself as an argument.
            Defaults to None.
        :type on_change: Callable[[Self], None] | None
        :param obsdict: This is used in conjunction with the method _as_dict to serialize
            the instance's data to JSON and back. It preserves the dataclasses also of the keys.
            *NOTE": It should never be used directly – it's reserved for the @serializer decorator.
        :type obsdict: dict | None
        :param validate: A boolean flag indicating whether to enforce validation checks
            on the data. Defaults to False.
        :type validate: bool
        :param kwargs: Additional keyword arguments forwarded to the superclass
            initializer.
        """
        self.__on_change = on_change
        self._changeset = {}
        if obj:
            super().__init__(obj, **kwargs)
        else:
            super().__init__(**kwargs)
        if obsdict:
            for item in obsdict:
                self[item['key']] = item['val']

    def __setitem__(self, key, value) -> None:
        if key in self.data:
            self._changeset[key] = AttributeChange(self.data[key], Action.MODIFY)
        else:
            self._changeset[key] = AttributeChange(None, Action.CREATE)
        if self.__on_change:
            self.__on_change(self.copy())
        super().__setitem__(key, value)

    def __delitem__(self, key) -> None:
        self._changeset[key] = AttributeChange(self.data[key], Action.DELETE)
        if self.__on_change:
            self.__on_change(self.copy())
        super().__delitem__(key)

    def __bool__(self) -> bool:
        return len(self) > 0

    def copy(self) -> Self:
        return ObservableDict(self.data.copy())

    def set_on_change(self, on_change: Callable[[Self], None]) -> None:
        self.__on_change = on_change

    def _as_dict(self):
        return {'obsdict': [{'key': key, 'val': val} for key, val in self.data.items()]}

    def clear_changeset(self) -> None:
        for item in self.data.values():
            if hasattr(item, 'clear_changeset'):
                item.clear_changeset()
        self._changeset = {}

