"""
# Observalbe Set

This module implements a set which is observable. That means, that a callback function/method may
be given that is called whenever the set is changed (adding/removing of items)
"""
import json
from copy import deepcopy
from enum import Enum
from typing import List, Callable, Any, Iterable, Set, Self

from pystrict import strict

from oldaplib.src.enums.action import Action
from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.helpers.oldaperror import OldapErrorKey, OldapErrorNotImplemented
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


#@strict
@serializer
class ObservableSet(Notify):
    """
    The ObservableSet class is a subclass of `Set` which allows the notification if the set is changed, that
    is items are added or removed. For this purpose, a callback function can be added to the set which is
    called whenever the set changes.
    """
    _setdata: Set[Any]
    _old_value: Self | None

    def __init__(self,
                 setitems: Self | Iterable | None = None,
                 notifier: Callable[[Enum | Iri], None] | None = None,
                 notify_data: Iri | None = None,
                 old_value: Self | None = None,
                 validate: bool = False) -> None:
        """
        Constructor of the ObservableSet class

        :param setitems: The items the ObservableSet will be initialized with
        :param on_change: Callback function to be called when an item is added/removed
        :param on_change_data: data supplied to the callback function
        """
        self._old_value = old_value
        super().__init__(notifier=notifier, data=notify_data)
        if isinstance(setitems, ObservableSet):
            self._setdata = setitems._setdata
        else:
            self._setdata = set(setitems if setitems else [])

    def __deepcopy__(self, memo: dict[Any, Any]) -> Self:
        new_copy = self.__class__.__new__(self.__class__)
        memo[id(self)] = new_copy
        #new_copy.__data = deepcopy(self.__data, memo)
        new_copy._setdata = set(self._setdata)
        #new_copy._notifier = deepcopy(self._notifier, memo)
        new_copy._notifier = self._notifier
        new_copy._notify_data = deepcopy(self._notify_data, memo)
        return new_copy

    def __iter__(self):
        return iter(self._setdata)

    def __len__(self) -> int:
        return len(self._setdata)

    def __contains__(self, item: Any) -> bool:
        return item in self._setdata

    def __repr__(self) -> str:
        l = [repr(x) for x in self._setdata]
        return ", ".join(l)

    def __str__(self) -> str:
        return str(self._setdata)

    def __eq__(self, other: Iterable[Any]) -> bool:
        if isinstance(other, ObservableSet):
            return self._setdata == other._setdata
        elif isinstance(other, set):
            return self._setdata == other
        elif isinstance(other, Iterable):
            return self._setdata == set(other)
        else:
            raise OldapErrorNotImplemented(f'Set.__eq__() not implemented for {type(other).__name__}')

    def __or__(self, other: Iterable[Any]) -> Self:
        if isinstance(other, ObservableSet):
            return ObservableSet(self._setdata.__or__(other._setdata), self._notifier, self._notify_data)
        elif isinstance(other, set):
            return ObservableSet(self._setdata.__or__(other), self._notifier, self._notify_data)
        elif isinstance(other, Iterable):
            return ObservableSet(self._setdata.__or__(set(other)), self._notifier, self._notify_data)
        else:
            raise OldapErrorNotImplemented(f'Set.__or__() not implemented for {type(other).__name__}')

    def __ror__(self, other: Iterable[Any]) -> Self:
        return ObservableSet(set(other).__or__(self._setdata), self._notifier, self._notify_data)

    def __rsub__(self, other: Iterable[Any]) -> Self:
        return ObservableSet(set(other).__sub__(self._setdata), self._notifier, self._notify_data)

    def __ior__(self, other: Iterable[Any]) -> Self:
        tmp_copy = deepcopy(self)
        if isinstance(other, ObservableSet):
            self._setdata.__ior__(other._setdata)
        else:
            self._setdata.__ior__(set(other))
        if not self._old_value:
            self._old_value = tmp_copy
        self.notify()
        return self

    def __and__(self, other: Iterable[Any]) -> Self:
        if isinstance(other, ObservableSet):
            return ObservableSet(self._setdata.__and__(other._setdata), self._notifier, self._notify_data)
        elif isinstance(other, set):
            return ObservableSet(self._setdata.__and__(other), self._notifier, self._notify_data)
        elif isinstance(other, Iterable):
            return ObservableSet(self._setdata.__and__(set(other)), self._notifier, self._notify_data)
        else:
            raise OldapErrorNotImplemented(f'Set.__and__() not implemented for {type(other).__name__}')

    def __iand__(self, other: Iterable[Any]) -> Self:
        tmp_copy = deepcopy(self)
        if isinstance(other, ObservableSet):
            self._setdata.__iand__(other._setdata)
        elif isinstance(other, set):
            self._setdata.__iand__(other)
        elif isinstance(other, Iterable):
            self._setdata.__iand__(set(other))
        else:
            raise OldapErrorNotImplemented(f'Set.__iand__() not implemented for {type(other).__name__}')
        if not self._old_value:
            self._old_value = tmp_copy
        self.notify()
        return self

    def __rsub__(self, other: Self) -> Self:
        pass

    def __sub__(self, other: Iterable[Any]) -> Self:
        if isinstance(other, ObservableSet):
            return ObservableSet(self._setdata.__sub__(other._setdata), self.notify, self._notify_data)
        elif isinstance(other, set):
            return ObservableSet(self._setdata.__sub__(other), self.notify, self._notify_data)
        elif isinstance(other, Iterable):
            return ObservableSet(self._setdata.__sub__(set(other)), self.notify, self._notify_data)
        else:
            raise OldapErrorNotImplemented(f'Set.__sub__() not implemented for {type(other).__name__}')

    def __isub__(self, other: Iterable[Any]) -> Self:
        tmp_copy = deepcopy(self)
        if isinstance(other, ObservableSet):
            self._setdata.__isub__(other._setdata)
        elif isinstance(other, set):
            self._setdata.__isub__(other)
        elif isinstance(other, Iterable):
            self._setdata.__isub__(set(other))
        else:
            raise OldapErrorNotImplemented(f'Set.__isub__() not implemented for {type(other).__name__}')
        if not self._old_value:
            self._old_value = tmp_copy
        self.notify()
        return self

    @classmethod
    def coerce(cls, value: Iterable[Any], *, notifier=None, notify_data=None) -> "ObservableSet":
        return value if isinstance(value, cls) else cls(value, notifier=notifier, notify_data=notify_data)

    def update(self, items: Iterable[Any]):
        tmp_copy = deepcopy(self)
        self._setdata.update(items)
        if not self._old_value:
            self._old_value = tmp_copy
        self.notify()

    def intersection_update(self, items: Iterable[Any]):
        tmp_copy = deepcopy(self)
        self._setdata.intersection_update(items)
        if not self._old_value:
            self._old_value = tmp_copy
        self.notify()

    def difference_update(self, items: Iterable[Any]):
        tmp_copy = deepcopy(self)
        self._setdata.difference_update(items)
        if not self._old_value:
            self._old_value = tmp_copy
        self.notify()

    def symmetric_difference_update(self, items: Iterable[Any]):
        tmp_copy = deepcopy(self)
        self._setdata.symmetric_difference_update(items)
        if not self._old_value:
            self._old_value = tmp_copy
        self.notify()

    def replace(self, items: Iterable[Any]) -> None:
        tmp_copy = deepcopy(self)
        self._setdata = set(items)
        if not self._old_value:
            self._old_value = tmp_copy
        self.notify()

    def add(self, item: Any) -> None:
        tmp_copy = deepcopy(self)
        self._setdata.add(item)
        if not self._old_value:
            self._old_value = tmp_copy
        self.notify()

    def remove(self, item: Any) -> None:
        tmp_copy = deepcopy(self)
        self._setdata.remove(item)
        if not self._old_value:
            self._old_value = tmp_copy
        self.notify()

    def discard(self, item: Any):
        tmp_copy = deepcopy(self)
        self._setdata.discard(item)
        if not self._old_value:
            self._old_value = tmp_copy
        self.notify()

    def pop(self):
        tmp_copy = deepcopy(self)
        item = self._setdata.pop()
        if not self._old_value:
            self._old_value = tmp_copy
        self.notify()
        return item

    def clear(self) -> None:
        tmp_copy = deepcopy(self)
        self._setdata.clear()
        if not self._old_value:
            self._old_value = tmp_copy
        self.notify()

    @property
    def old_value(self) -> Self | None:
        return self._old_value

    def clear_old_value(self) -> None:
        """
        Clear the changeset. This method is only for internal use or debugging...
        :return: None
        """
        self._old_value = None

    def copy(self) -> Self:
        return ObservableSet(self._setdata.copy(), notifier=self._notifier, notify_data=self._notify_data)

    @property
    def toRdf(self) -> str:
        l = [x.toRdf if getattr(x, "toRdf", None) else x for x in self._setdata]
        return ", ".join(l)

    def _as_dict(self):
        return {'setitems': list(self._setdata)}

    def asSet(self) -> set:
        return self._setdata.copy()

    def to_set(self) -> set:
        return self._setdata

    def undo(self) -> None:
        if self._old_value:
            self._setdata = self._old_value.to_set()
        self._old_value = None

    def clear_changeset(self) -> None:
        for item in self._setdata:
            if hasattr(item, 'clear_changeset'):
                item.clear_changeset()
        self._old_value = None

    def update_sparql(self, *,
                      graph: Iri | Xsd_QName,
                      subject: Iri,
                      field: Iri,
                      ignoreitems: Set[Any] | None = None,
                      indent: int = 0, indent_inc: int = 4) -> list[str]:
        items_to_add = self._setdata - self._old_value.to_set() if self._old_value else self._setdata
        if ignoreitems:
            items_to_add = items_to_add - ignoreitems
        items_to_delete = self._old_value.to_set() - self._setdata if self._old_value else set()
        if ignoreitems:
            items_to_delete = items_to_delete - ignoreitems
        blank = ''
        sparql_list = []

        if items_to_add:
            sparql = f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {graph} {{\n'
            for item in items_to_add:
                sparql += f'{blank:{(indent + 2) * indent_inc}}{subject.toRdf} {field.toRdf} {item.toRdf} .'
            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql_list.append(sparql)

        if items_to_delete:
            sparql = f'{blank:{indent * indent_inc}}DELETE DATA {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {graph} {{\n'
            for item in items_to_delete:
                sparql += f'{blank:{(indent + 2) * indent_inc}}{subject.toRdf} {field.toRdf} {item.toRdf} .'
            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql_list.append(sparql)

        return sparql_list

    def update_shacl(self, *,
                     graph: Xsd_NCName,
                     owlclass_iri: Iri | None = None,
                     prop_iri: Iri,
                     attr: AttributeClass,
                     modified: Xsd_dateTime,
                     indent: int = 0, indent_inc: int = 4) -> list[str]:
        items_to_add = self._setdata - self._old_value
        items_to_delete = self._old_value - self._setdata

        blank = ''
        sparql_list = []
        sparql = f'# ObservableSet: Update SHACL\n'
        sparql += f'{blank:{indent * indent_inc}}WITH {graph}:shacl\n'

        if items_to_add:
            sparql = f'{blank:{indent * indent_inc}}INSERT {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {graph} {{\n'
            for item in items_to_add:
                sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {attr.value.toRdf} {item.toRdf} .'
            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

        if items_to_delete:
            sparql = f'{blank:{indent * indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {graph} {{\n'
            for item in items_to_delete:
                sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {attr.value.toRdf} {item.toRdf} .'
            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql_list.append(sparql)

            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            if owlclass_iri:
                sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:path {prop_iri.toRdf} .\n'
            else:
                sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({prop_iri}Shape as ?prop) .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {modified.toRdf})\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        return sparql