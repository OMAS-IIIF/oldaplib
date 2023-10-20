from typing import Callable, Optional, Any

from pystrict import strict

from omaslib.src.helpers.propertyclassprops import PropertyClassProp


@strict
class Notify:
    _notifier: Callable[[PropertyClassProp], None]
    _data: PropertyClassProp

    def __init__(self, notifier: Optional[Callable[[PropertyClassProp], None]], data: Optional[PropertyClassProp] = None):
        self._notifier = notifier
        self._data = data

    def set_notifier(self, notifier: Callable[[PropertyClassProp], None], data: Optional[PropertyClassProp] = None):
        self._notifier = notifier
        self._data = data

    def notify(self):
        if self._notifier is not None:
            self._notifier(self._data)

