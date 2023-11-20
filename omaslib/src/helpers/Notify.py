from typing import Callable, Optional, Union

from pystrict import strict

from omaslib.src.helpers.datatypes import QName
from omaslib.src.helpers.propertyclassattr import PropertyClassAttribute
from omaslib.src.helpers.resourceclassattr import ResourceClassAttribute


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

    def __init__(self,
                 notifier: Optional[Callable[[Union[PropertyClassAttribute, ResourceClassAttribute, QName]], None]],
                 data: Union[PropertyClassAttribute, ResourceClassAttribute, QName, None] = None):
        self._notifier = notifier
        self._data = data

    def set_notifier(self,
                     notifier: Callable[[Union[PropertyClassAttribute, ResourceClassAttribute, QName]], None],
                     data: Union[PropertyClassAttribute, ResourceClassAttribute, QName, None] = None) -> None:
        self._notifier = notifier
        self._data = data

    def notify(self) -> None:
        if self._notifier is not None:
            self._notifier(self._data)

