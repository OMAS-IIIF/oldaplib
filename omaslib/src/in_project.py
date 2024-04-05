"""
# InProject Class

The InProject class is a helper class that is used to record the per-project administrative permissions for
a particular user. It's not meant to be used without the context of a user, that is as a _property_ of a User.
"""
from typing import Dict, Callable, Set, Self, ItemsView, KeysView

from pystrict import strict

from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.helpers.observable_set import ObservableSet
from omaslib.src.enums.permissions import AdminPermission
from omaslib.src.helpers.omaserror import OmasErrorValue, OmasErrorKey
from omaslib.src.helpers.serializer import serializer
import json


@strict
@serializer
class InProjectClass:
    """
    Implements the administrative permission a user has for the projects the user is associated with.
    """
    __data: Dict[Iri, ObservableSet[AdminPermission]]
    __on_change: Callable[[Iri, ObservableSet[AdminPermission] | None], None] | None

    def __init__(self,
                 data: Self | Dict[Iri | str, set[AdminPermission | str] | ObservableSet[AdminPermission]] | None = None,
                 on_change: Callable[[Iri, ObservableSet[AdminPermission] | None], None] = None) -> None:
        """
        Constructor of the class. The class acts like a dictionary and allows the access to the permission
        set for a project using the QName of the project as the key: ```perms = t.in_project[QName('ex:proj')]```.
        It supports the getting, setting and deleting a permission set.
        In addition, the following methods are implemented:

        - _get()_: gets the permission set or returns `None`if it doesn't exist for the given project'
        - _copy()_: Creates a deep copy of the given instance
        - _==_: Check for equality of 2 instances
        - _!=_: Check for inequality of 2 instances

        :param data: A dictionary with the QName/anyURI of the project as key and the set of permissions as value
        :type data: Dict[str | Xsd_QName, Set[AdminPermission] | ObservableSet[AdminPermission]] | None
        :param on_change: A callable that is called whenever the instance has been changed
        :type on_change: Callable[[str, ObservableSet[AdminPermission] | None], None]
        """
        self.__data = {}
        self.__on_change = None
        if data is not None:
            if isinstance(data, InProjectClass):
                self.__data = data.__data
            else:
                for key, value in data.items():
                    key = Iri(key)
                    self.__data[key] = self.__perms(key, value)
        self.__on_change = on_change

    def __perms(self,
                key: Iri,
                value: set[AdminPermission | str] | ObservableSet[AdminPermission] | None) -> ObservableSet[AdminPermission]:
        perms = ObservableSet(on_change=self.__on_set_changed, on_change_data=key)
        if value is None:
            return perms
        for permission in value:
            if isinstance(permission, str):
                try:
                    if permission.find(':') >= 0:
                        perms.add(AdminPermission(permission))
                    else:
                        perms.add(AdminPermission('omas:' + permission))
                except ValueError as err:
                    raise OmasErrorValue(str(err))
            elif permission in AdminPermission:
                perms.add(permission)
            else:
                raise OmasErrorValue(f'{permission} is not a valid AdminPermission')
        return perms

    def __on_set_changed(self, oldset: ObservableSet[AdminPermission], key: Iri | str):
        if self.__on_change is not None:
            self.__on_change(key, oldset) ## Action.MODIFY

    def __getitem__(self, key: Iri | str) -> ObservableSet[AdminPermission]:
        if not isinstance(key, Iri):
            key = Iri(key)
        try:
            return self.__data[key]
        except (KeyError, AttributeError) as err:
            raise OmasErrorKey(str(err), key)

    def __setitem__(self, key: Iri | str, value: set[AdminPermission | str] | ObservableSet[AdminPermission]) -> None:
        if not isinstance(key, Iri):
            key = Iri(key)
        if self.__data.get(key) is None:
            if self.__on_change is not None:
                self.__on_change(key, None) ## Action.CREATE: Create a new inProject connection to a new project and add permissions
        else:
            if self.__on_change is not None:
                self.__on_change(key, self.__data[key].copy())  ## Action.REPLACE Replace all the permission of the given connection to a project
        self.__data[key] = self.__perms(key, value)

    def __delitem__(self, key: Iri | str) -> None:
        if not isinstance(key, Iri):
            key = Iri(key)
        if self.__data.get(key) is not None:
            if self.__on_change is not None:
                self.__on_change(key, self.__data[key].copy())  ## Action.DELETE
            del self.__data[key]
        else:
            raise OmasErrorKey(f'Can\'t delete key "{key}" – does not exist')

    def __str__(self) -> str:
        s = ''
        for k, v in self.__data.items():
            l = [x.value for x in v]
            l.sort()
            s += f'{k} : {l}\n'
        return s

    def __bool__(self) -> bool:
        return bool(self.__data)

    def copy(self) -> Self:
        data_copy: dict[Iri, set[AdminPermission | str] | ObservableSet[AdminPermission]] = {}
        tmp = self.__on_change
        self.__on_change = None
        for key, val in self.__data.items():
            data_copy[key] = val
        self.__on_change = tmp
        return InProjectClass(data_copy, self.__on_change)

    def __eq__(self, other: Self | None) -> bool:
        if other is None:
            return False
        if not isinstance(other, InProjectClass):
            raise OmasErrorValue(f'"Other must be an instance of InProjectClass, not {type(other)}"')
        return self.__data == other.__data

    def __ne__(self, other: Self | None) -> bool:
        if other is None:
            return True
        if not isinstance(other, InProjectClass):
            raise OmasErrorValue(f'"Other must be an instance of InProjectClass, not {type(other)}"')
        return self.__data != other.__data

    def get(self, key: Iri) -> ObservableSet[AdminPermission] | None:
        return self.__data.get(key)

    def items(self) -> ItemsView[Iri, ObservableSet[AdminPermission]]:
        return self.__data.items()

    def keys(self) -> KeysView:
        return self.__data.keys()

    def _as_dict(self) -> dict:
        tmp = {f'{str(key)}': value for key, value in self.__data.items()}
        return {'data': tmp}

    def add_admin_permission(self, project: Iri, permission: AdminPermission) -> None:
        pass


if __name__ == '__main__':
    in_proj = InProjectClass({Iri('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                              AdminPermission.ADMIN_RESOURCES,
                                                              AdminPermission.ADMIN_CREATE}})
    jsonstr = json.dumps(in_proj, default=serializer.encoder_default)
    in_proj2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
    for k, v in in_proj2.items():
        print(f'{k} ({type(k)}) = {v}')