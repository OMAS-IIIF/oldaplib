from typing import Callable, Optional

from pystrict import strict

from omaslib.src.helpers.propertyclassprops import PropertyClassAttribute


@strict
class Notify:
    """
    This class can be used as super-class for a classes used as real (sh:name, sh:description) or
    virtual (Restrictions) props of a PropertyClass. It allows these non-primitive values such
    as of type LangString or PropertyRestriction to notify PropertyClass that something has changed,
    e.g. the change of value
    """
    _notifier: Callable[[PropertyClassAttribute], None]
    _data: PropertyClassAttribute

    def __init__(self, notifier: Optional[Callable[[PropertyClassAttribute], None]], data: Optional[PropertyClassAttribute] = None):
        self._notifier = notifier
        self._data = data

    def set_notifier(self, notifier: Callable[[PropertyClassAttribute], None], data: Optional[PropertyClassAttribute] = None):
        self._notifier = notifier
        self._data = data

    def notify(self):
        if self._notifier is not None:
            self._notifier(self._data)

