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


#@strict
@serializer
class ObservableSet(Notify):
    """
    The ObservableSet class is a subclass of `Set` which allows the notification if the set is changed, that
    is items are added or removed. For this purpose, a callback function can be added to the set which is
    called whenever the set changes.
    """
    __setdata: Set[Any]
    __old_value: Self | None

    def __init__(self,
                 setitems: Self | Iterable | None = None,
                 notifier: Callable[[Enum | Iri], None] | None = None,
                 notify_data: Iri | None = None,
                 old_value: Self | None = None) -> None:
        """
        Constructor of the ObservableSet class

        :param setitems: The items the ObservableSet will be initialized with
        :param on_change: Callback function to be called when an item is added/removed
        :param on_change_data: data supplied to the callback function
        """
        self.__old_value = old_value
        super().__init__(notifier=notifier, data=notify_data)
        if isinstance(setitems, ObservableSet):
            self.__setdata = setitems.__setdata
        else:
            self.__setdata = set(setitems if setitems else [])

    def __deepcopy__(self, memo: dict[Any, Any]) -> Self:
        new_copy = self.__class__.__new__(self.__class__)
        memo[id(self)] = new_copy
        #new_copy.__data = deepcopy(self.__data, memo)
        new_copy.__setdata = set(self.__setdata)
        #new_copy._notifier = deepcopy(self._notifier, memo)
        new_copy._notifier = self._notifier
        new_copy._notify_data = deepcopy(self._notify_data, memo)
        return new_copy

    def __iter__(self):
        return iter(self.__setdata)

    def __len__(self) -> int:
        return len(self.__setdata)

    def __contains__(self, item: Any) -> bool:
        return item in self.__setdata

    def __repr__(self) -> str:
        l = [repr(x) for x in self.__setdata]
        return ", ".join(l)

    def __str__(self) -> str:
        return str(self.__setdata)

    def __eq__(self, other: Iterable) -> bool:
        if isinstance(other, ObservableSet):
            return self.__setdata == other.__setdata
        elif isinstance(other, set):
            return self.__setdata == other
        elif isinstance(other, Iterable):
            return self.__setdata == set(other)
        else:
            raise OldapErrorNotImplemented(f'Set.__eq__() not implemented for {type(other).__name__}')

    def __or__(self, other: Iterable) -> Self:
        if isinstance(other, ObservableSet):
            return ObservableSet(self.__setdata.__or__(other.__setdata), self._notifier, self._notify_data)
        elif isinstance(other, set):
            return ObservableSet(self.__setdata.__or__(other), self._notifier, self._notify_data)
        elif isinstance(other, Iterable):
            return ObservableSet(self.__setdata.__or__(set(other)), self._notifier, self._notify_data)
        else:
            raise OldapErrorNotImplemented(f'Set.__or__() not implemented for {type(other).__name__}')

    def __ror__(self, other: Self) -> Self:
        pass

    def __ior__(self, other: Iterable) -> Self:
        tmp_copy = deepcopy(self)
        if isinstance(other, ObservableSet):
            self.__setdata.__ior__(other.__setdata)
        elif isinstance(other, set):
            self.__setdata.__ior__(other)
        elif isinstance(other, Iterable):
            return ObservableSet(self.__setdata.__ior__(set(other)), self._notifier, self._notify_data)
        else:
            raise OldapErrorNotImplemented(f'Set.i__or__() not implemented for {type(other).__name__}')
        if not self.__old_value:
            self.__old_value = tmp_copy
        self.notify()
        return self

    def __and__(self, other: Iterable) -> Self:
        if isinstance(other, ObservableSet):
            return ObservableSet(self.__setdata.__and__(other.__setdata), self._notifier, self._notify_data)
        elif isinstance(other, set):
            return ObservableSet(self.__setdata.__and__(other), self._notifier, self._notify_data)
        elif isinstance(other, Iterable):
            return ObservableSet(self.__setdata.__and__(set(other)), self._notifier, self._notify_data)
        else:
            raise OldapErrorNotImplemented(f'Set.__and__() not implemented for {type(other).__name__}')

    def __iand__(self, other: Iterable) -> Self:
        tmp_copy = deepcopy(self)
        if isinstance(other, ObservableSet):
            self.__setdata.__iand__(other.__setdata)
        elif isinstance(other, set):
            self.__setdata.__iand__(other)
        elif isinstance(other, Iterable):
            self.__setdata.__iand__(set(other))
        else:
            raise OldapErrorNotImplemented(f'Set.__iand__() not implemented for {type(other).__name__}')
        if not self.__old_value:
            self.__old_value = tmp_copy
        self.notify()
        return self

    def __rsub__(self, other: Self) -> Self:
        pass

    def __sub__(self, other: Iterable) -> Self:
        if isinstance(other, ObservableSet):
            return ObservableSet(self.__setdata.__sub__(other.__setdata), self.notify, self._notify_data)
        elif isinstance(other, set):
            return ObservableSet(self.__setdata.__sub__(other), self.notify, self._notify_data)
        elif isinstance(other, Iterable):
            return ObservableSet(self.__setdata.__sub__(set(other)), self.notify, self._notify_data)
        else:
            raise OldapErrorNotImplemented(f'Set.__sub__() not implemented for {type(other).__name__}')

    def __isub__(self, other: Iterable) -> Self:
        tmp_copy = deepcopy(self)
        if isinstance(other, ObservableSet):
            self.__setdata.__isub__(other.__setdata)
        elif isinstance(other, set):
            self.__setdata.__isub__(other)
        elif isinstance(other, Iterable):
            self.__setdata.__isub__(set(other))
        else:
            raise OldapErrorNotImplemented(f'Set.__isub__() not implemented for {type(other).__name__}')
        if not self.__old_value:
            self.__old_value = tmp_copy
        self.notify()
        return self

    def update(self, items: Iterable):
        tmp_copy = deepcopy(self)
        self.__setdata.update(items)
        if not self.__old_value:
            self.__old_value = tmp_copy
        self.notify()

    def intersection_update(self, items: Iterable):
        tmp_copy = deepcopy(self)
        self.__setdata.intersection_update(items)
        if not self.__old_value:
            self.__old_value = tmp_copy
        self.notify()

    def difference_update(self, items: Iterable):
        tmp_copy = deepcopy(self)
        self.__setdata.difference_update(items)
        if not self.__old_value:
            self.__old_value = tmp_copy
        self.notify()

    def symmetric_difference_update(self, items: Iterable):
        tmp_copy = deepcopy(self)
        self.__setdata.symmetric_difference_update(items)
        if not self.__old_value:
            self.__old_value = tmp_copy
        self.notify()

    def add(self, item: Any) -> None:
        tmp_copy = deepcopy(self)
        self.__setdata.add(item)
        if not self.__old_value:
            self.__old_value = tmp_copy
        self.notify()

    def remove(self, item: Any) -> None:
        tmp_copy = deepcopy(self)
        self.__setdata.remove(item)
        if not self.__old_value:
            self.__old_value = tmp_copy
        self.notify()

    def discard(self, item: Any):
        tmp_copy = deepcopy(self)
        self.__setdata.discard(item)
        if not self.__old_value:
            self.__old_value = tmp_copy
        self.notify()

    def pop(self):
        tmp_copy = deepcopy(self)
        item = self.__setdata.pop()
        if not self.__old_value:
            self.__old_value = tmp_copy
        self.notify()
        return item

    def clear(self) -> None:
        tmp_copy = deepcopy(self)
        self.__setdata.clear()
        if not self.__old_value:
            self.__old_value = tmp_copy
        self.notify()

    @property
    def old_value(self) -> Self | None:
        return self.__old_value

    def clear_old_value(self) -> None:
        """
        Clear the changeset. This method is only for internal use or debugging...
        :return: None
        """
        self.__old_value = None

    def copy(self) -> Self:
        return ObservableSet(self.__setdata.copy(), notifier=self._notifier, notify_data=self._notify_data)

    @property
    def toRdf(self) -> str:
        l = [x.toRdf if getattr(x, "toRdf", None) else x for x in self.__setdata]
        return ", ".join(l)

    def _as_dict(self):
        return {'setitems': list(self.__setdata)}

    def asSet(self) -> set:
        return self.__setdata.copy()

    def to_set(self) -> set:
        return self.__setdata

    def undo(self) -> None:
        if self.__old_value:
            self.__setdata = self.__old_value.to_set()
        self.__old_value = None

    def clear_changeset(self):
        self.__old_value = None

    def update_sparql(self, *,
                      graph: Iri,
                      subject: Iri,
                      field: Iri,
                      indent: int = 0, indent_inc: int = 4) -> list[str]:
        items_to_add = self.__setdata - self.__old_value.__setdata
        items_to_delete = self.__old_value.__setdata - self.__setdata
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
