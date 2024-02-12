"""
# InProject Class

The InProject class is a helper class that is used to record the per-project administrative permissions for
a particular user. It's not meant to be used without the context of a user, that is as a _property_ of a User.
"""
from copy import deepcopy
from typing import Dict, Callable, Set, Self, ItemsView, KeysView

from pystrict import strict

from omaslib.src.helpers.datatypes import QName
from omaslib.src.helpers.observable_set import ObservableSet
from omaslib.src.helpers.permissions import AdminPermission
from omaslib.src.helpers.serializer import serializer
import json

@strict
@serializer
class InProjectType:
    """
    Implements the administrative permission a user has for the projects the user is associated with.
    """
    __data: Dict[str, ObservableSet[AdminPermission]]
    __on_change: Callable[[str, ObservableSet[AdminPermission] | None], None]

    def __init__(self,
                 data: Dict[str | QName, Set[AdminPermission] | ObservableSet[AdminPermission]] | None = None,
                 on_change: Callable[[str, ObservableSet[AdminPermission] | None], None] = None) -> None:
        """
        Constructor of the class. The class acts like a dictionary and allows the access to the permission
        set for a project using the QName of the project as the key: ```perms = t.in_project[QName('ex:proj')]```.
        It supports the getting, setting and deleting a permission set.
        In addition the following methods are implemented:

        - _get()_: gets the permission set or returns `None`if it doesn't exist for the given project'
        - _copy()_: Creates a deep copy of the given instance
        - _==_: Check for equality of 2 instances
        - _!=_: Check for inequality of 2 instances

        :param data: A dictionary with the QName of the project as key and the set of permissions as value
        :type data: Dict[str | QName, Set[AdminPermission] | ObservableSet[AdminPermission]] | None
        :param on_change: A callable that is called whenever the instance has been changed
        :type on_change: Callable[[str, ObservableSet[AdminPermission] | None], None]
        """
        if data is not None:
            self.__data = {str(key): ObservableSet(val, on_change=self.__on_set_changed, on_change_data=str(key)) for key, val in data.items()}
        else:
            self.__data = {}
        self.__on_change = on_change

    def __on_set_changed(self, oldset: ObservableSet[AdminPermission], key: QName | str):
        if self.__on_change is not None:
            self.__on_change(str(key), oldset) ## Action.MODIFY

    def __getitem__(self, key: QName | str) -> ObservableSet[AdminPermission]:
        return self.__data[str(key)]

    def __setitem__(self, key: QName | str, value: ObservableSet[AdminPermission] | Set[AdminPermission]) -> None:
        if self.__data.get(str(key)) is None:
            if self.__on_change is not None:
                self.__on_change(str(key), None) ## Action.CREATE: Create a new inProject connection to a new project and add permissions
        else:
            if self.__on_change is not None:
                self.__on_change(str(key), self.__data[str(key)].copy())  ## Action.REPLACE Replace all the permission of the given connection to a project
        self.__data[key] = ObservableSet(value, on_change=self.__on_set_changed)

    def __delitem__(self, key: QName | str) -> None:
        if self.__data.get(str(key)) is not None:
            if self.__on_change is not None:
                self.__on_change(str(key), self.__data[str(key)].copy())  ## Action.DELETE
            del self.__data[key]

    def __str__(self) -> str:
        s = '';
        for k, v in self.__data.items():
            s += f'{k}: {v}\n'
        return s

    def copy(self) -> Self:
        data_copy = deepcopy(self.__data)
        on_change_copy = self.__on_change
        return InProjectType(data_copy, on_change_copy)

    def __eq__(self, other: Self) -> bool:
        return self.__data == other.__data

    def __ne__(self, other: Self) -> bool:
        return self.__data != other.__data

    def get(self, key: str | QName) -> ObservableSet[AdminPermission] | None:
        return self.__data.get(str(key))

    def items(self) -> ItemsView[str, ObservableSet[AdminPermission]]:
        return self.__data.items()

    def keys(self) -> KeysView:
        return self.__data.keys()

    def _as_dict(self) -> dict:
        return {'data': self.__data}


if __name__ == '__main__':
    in_proj = InProjectType({QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE}})
    jsonstr = json.dumps(in_proj, default=serializer.encoder_default)
    in_proj2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)