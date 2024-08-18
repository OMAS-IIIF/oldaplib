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
    Implements the administrative permission a user has for the projects the user is associated with.
    """
    __setdata: dict[Iri, ObservableSet]
    _changeset: dict[Iri, AttributeChange]

    def __init__(self,
                 setdata: Self | Dict[Iri | str, set[AdminPermission | str] | ObservableSet] | None = None,
                 notifier: Callable[[Iri], None] | None = None,
                 notify_data: Iri | None = None) -> None:
        """
        Constructor of the class. The class acts like a dictionary and allows the access to the permission
        set for a project using the QName of the project as the key: ```perms = t.in_project[QName('ex:proj')]```.
        It supports the getting, setting and deleting a permission set.
        In addition, the following methods are implemented:

        - _get()_: gets the permission set or returns `None`if it doesn't exist for the given project'
        - _copy()_: Creates a deep copy of the given instance
        - _==_: Check for equality of 2 instances
        - _!=_: Check for inequality of 2 instances

        :param setdata: A dictionary with the QName/anyURI of the project as key and the set of permissions as value
        :type setdata: Dict[str | Xsd_QName, Set[AdminPermission] | ObservableSet[AdminPermission]] | None
        :param on_change: A callable that is called whenever the instance has been changed
        :type on_change: Callable[[str, ObservableSet[AdminPermission] | None], None]
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
                    if permission.find(':') >= 0:
                        perms.add(AdminPermission(permission))
                    else:
                        perms.add(AdminPermission('oldap:' + permission))
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
            key = Iri(key)
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
            key = Iri(key)
        if self.__setdata.get(key) is not None:
            if self._changeset.get(key) is None:
                self._changeset[key] = AttributeChange(self.__setdata[key], Action.DELETE)
            del self.__setdata[key]
            self.notify()
        else:
            raise OldapErrorKey(f'Can\'t delete key "{key}" – does not exist')

    def __iter__(self) -> Iterator[Iri]:
        return iter(self.__setdata.items())

    def __contains__(self, key: Iri | str) -> bool:
        if not isinstance(key, Iri):
            key = Iri(key)
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
        return self.__setdata.get(key)

    def items(self) -> ItemsView[Iri, ObservableSet]:
        return self.__setdata.items()

    def keys(self) -> KeysView:
        return self.__setdata.keys()

    def _as_dict(self) -> dict:
        tmp = {f'{str(key)}': value for key, value in self.__setdata.items()}
        return {'setdata': tmp}

    def add_admin_permission(self, project: Iri, permission: AdminPermission) -> None:
        pass


if __name__ == '__main__':
    in_proj = InProjectClass({Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                              AdminPermission.ADMIN_RESOURCES,
                                                              AdminPermission.ADMIN_CREATE}})
    for key, val in in_proj:
        print(key, val)
    jsonstr = json.dumps(in_proj, default=serializer.encoder_default)
    in_proj2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
    for k, v in in_proj2.items():
        print(f'{k} ({type(k)}) = {v}')