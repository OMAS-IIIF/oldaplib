"""
# InProject Class

The InProject class is a helper class that is used to record the per-project administrative permissions for
a particular user. It's not meant to be used without the context of a user, that is as a _property_ of a User.
"""
from dataclasses import dataclass
from enum import unique
from typing import Dict, Callable, Set, Self, ItemsView, KeysView, Iterator, Any

from pystrict import strict

from oldaplib.src.enums.action import Action
from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorKey
from oldaplib.src.helpers.serializer import serializer
import json


#@strict
@serializer
class InProjectClass(Notify):
    """
    Defines a class that implements administrative permission management for users
    associated with projects.

    This class provides a dictionary-like interface to manage permissions for various
    projects, identified by their QName or IRI. It supports operations like
    retrieving, setting, deleting, and copying permission sets. It also facilitates
    tracking changes and notifying through observers when modifications occur. The
    permissions for each project are stored in an observable set.

    :ivar changeset: A dictionary that keeps track of changes to the permissions for
        the associated projects.
    :type changeset: dict[Iri, AttributeChange]
    """
    __setdata: dict[Iri, ObservableSet]
    _changeset: dict[Iri, AttributeChange]

    def __init__(self,
                 setdata: Self | Dict[Iri | str, set[AdminPermission | str] | ObservableSet] | None = None,
                 notifier: Callable[[Iri], None] | None = None,
                 notify_data: Iri | None = None,
                 validate: bool = False) -> None:
        """
        Constructor of the class. The class behaves like a dictionary that allows access to the permission set for
        a project, using the QName of the project as the key. It supports retrieving, setting, and deleting
        permission sets. Methods for copying the instance and comparing equality or inequality with another
        instance are implemented.

        :param setdata: Optional initial set of data represented as a dictionary. Keys are project QName or anyURI,
            and values are sets of permissions.
        :type setdata: Dict[Iri | str, Set[AdminPermission | str] | ObservableSet] | None
        :param notifier: A callable function to be invoked for notifications related to project permissions.
        :type notifier: Callable[[Iri], None] | None
        :param notify_data: Relevant data to be passed to the notifier callable, typically an Iri instance.
        :type notify_data: Iri | None
        :param validate: A boolean value indicating whether the data should be validated during initialization.
        :type validate: bool

        :raises OldapErrorValue: If the input data is not valid.
        :raises OldapErrorNotFound: If a project is not found.
        :raises OldapError: If an error occurs during initialization.
        """
        super().__init__(notifier=notifier, data=notify_data)
        self.__setdata = {}
        self._changeset = {}
        if setdata is not None:
            if isinstance(setdata, InProjectClass):
                self.__setdata = setdata.__setdata
            else:
                for key, value in setdata.items():
                    key = Iri(key)
                    self.__setdata[key] = self.__perms(key, value)
        self.clear_changeset()

    def __perms(self,
                key: Iri,
                value: set[AdminPermission | str] | ObservableSet | None) -> ObservableSet:
        perms = ObservableSet(notifier=self.__on_set_changed, notify_data=key)
        if value is None:
            return perms
        for permission in value:
            if isinstance(permission, str):
                try:
                    perms.add(AdminPermission.from_string(permission))
                except ValueError as err:
                    raise OldapErrorValue(str(err))
            elif permission in AdminPermission:
                perms.add(permission)
            else:
                raise OldapErrorValue(f'{permission} is not a valid AdminPermission')
        return perms

    def __bool__(self) -> bool:
        return bool(self.__setdata)

    def __len__(self) -> int:
        return len(self.__setdata)

    def __on_set_changed(self, key: Iri):
        if self._changeset.get(key) is None:
            self._changeset[key] = AttributeChange(self.__setdata.get(key), Action.MODIFY)
        self.notify()

    def __getitem__(self, key: Iri | str) -> ObservableSet:
        if not isinstance(key, Iri):
            key = Iri(key)
        try:
            return self.__setdata[key]
        except (KeyError, AttributeError) as err:
            raise OldapErrorKey(str(err), key)

    def __setitem__(self, key: Iri | str, value: set[AdminPermission | str] | ObservableSet | None) -> None:
        if not isinstance(key, Iri):
            key = Iri(key, validate=True)
        if self.__setdata.get(key) is None:
            if self._changeset.get(key) is None:
                self._changeset[key] = AttributeChange(self.__setdata.get(key), Action.CREATE)
        else:
            if self._changeset.get(key) is None:
                self._changeset[key] = AttributeChange(self.__setdata[key], Action.REPLACE)
        if value is None:
            if self._changeset.get(key) is None:
                self._changeset[key] = AttributeChange(self.__setdata.get(key), Action.DELETE)
            del self.__setdata[key]
        else:
            self.__setdata[key] = self.__perms(key, value)
        self.notify()

    def __delitem__(self, key: Iri | str) -> None:
        if not isinstance(key, Iri):
            key = Iri(key, validate=True)
        if self.__setdata.get(key) is not None:
            if self._changeset.get(key) is None:
                self._changeset[key] = AttributeChange(self.__setdata[key], Action.DELETE)
            del self.__setdata[key]
            self.notify()
        else:
            raise OldapErrorKey(f'Can\'t delete key "{key}" – does not exist')

    def __eq__(self, other: Self) -> bool:
        if len(self) != len(other):
            return False
        for iri, perms in self.__setdata.items():
            if other.get(iri) is None:
                return False
            if self[iri] != other[iri]:
                return False
        return True

    def __ne__(self, other: Self) -> bool:
        return not self.__eq__(other)

    def __iter__(self) -> Iterator[Iri]:
        return iter(self.__setdata.items())

    def __contains__(self, key: Iri | str) -> bool:
        if not isinstance(key, Iri):
            key = Iri(key, validate=True)
        return key in self.__setdata


    def __str__(self) -> str:
        s = ''
        for k, v in self.__setdata.items():
            l = [x.value for x in v]
            l.sort()
            s += f'{k} : {l}\n'
        return s

    @property
    def changeset(self) -> dict[Iri, AttributeChange]:
        return self._changeset

    def clear_changeset(self) -> None:
        """
        Clear the changeset. This method is only for internal use or debugging...
        :return: None
        """
        for key in self.__setdata.keys():
            self.__setdata[key].clear_changeset()
        self._changeset = {}

    def copy(self) -> Self:
        data_copy: dict[Iri, set[AdminPermission | str] | ObservableSet] = {}
        for key, val in self.__setdata.items():
            data_copy[key] = val
        return InProjectClass(data_copy, notifier=self._notifier, notify_data=self._notify_data)

    def __eq__(self, other: Self | None) -> bool:
        if other is None:
            return False
        if not isinstance(other, InProjectClass):
            raise OldapErrorValue(f'"Other must be an instance of InProjectClass, not {type(other)}"')
        return self.__setdata == other.__setdata

    def __ne__(self, other: Self | None) -> bool:
        if other is None:
            return True
        if not isinstance(other, InProjectClass):
            raise OldapErrorValue(f'"Other must be an instance of InProjectClass, not {type(other)}"')
        return self.__setdata != other.__setdata

    def get(self, key: Iri) -> ObservableSet | None:
        """
        Retrieves the value associated with the specified key from the internal
        data structure. If the key exists, the corresponding value will be
        returned; otherwise, None will be returned.

        :param key: The key to search within the data structure.
        :type key: Iri
        :return: The value associated with the provided key if it exists,
            otherwise None.
        :rtype: ObservableSet | None
        """
        return self.__setdata.get(key)

    def items(self) -> ItemsView[Iri, ObservableSet]:
        """
        Returns a view of the dictionary's items.

        This method provides access to the items of the internal dictionary-like
        structure. It returns an ItemsView object containing key-value pairs where
        keys are of type `Iri` and values are of type `ObservableSet`.

        :return: An ItemsView containing all key-value pairs from the internal
            dictionary-like structure. The keys are of type `Iri` and the values are
            of type `ObservableSet`.
        :rtype: ItemsView[Iri, ObservableSet]
        """
        return self.__setdata.items()

    def keys(self) -> KeysView:
        """
        Returns a view of the keys in the internal data structure.

        This method provides access to the keys stored in the internal
        data representation. It is particularly useful for iterating
        over all keys or checking the existence of a key within the
        data structure.

        :returns: A view object displaying a dynamic view of the
                  dictionary's keys.
        :rtype: KeysView
        """
        return self.__setdata.keys()

    def _as_dict(self) -> dict:
        tmp = {f'{str(key)}': value for key, value in self.__setdata.items()}
        return {'setdata': tmp}

    def add_admin_permission(self, project: Iri, permission: AdminPermission) -> None:
        pass

