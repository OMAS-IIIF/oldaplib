"""
# InProject Class

The InProject class is a helper class that is used to record the per-project administrative permissions for
a particular user. It's not meant to be used without the context of a user, that is as a _property_ of a User.
"""
from copy import deepcopy
from typing import Dict, Callable, Set, Self, ItemsView, KeysView

from pystrict import strict

from omaslib.src.helpers.datatypes import QName, AnyIRI, NamespaceIRI
from omaslib.src.helpers.observable_set import ObservableSet
from omaslib.src.helpers.permissions import AdminPermission
from omaslib.src.helpers.query_processor import OmasStringLiteral
from omaslib.src.helpers.serializer import serializer
import json

@strict
@serializer
class InProjectClass:
    """
    Implements the administrative permission a user has for the projects the user is associated with.
    """
    __data: Dict[QName | AnyIRI, ObservableSet[AdminPermission]]
    __on_change: Callable[[QName | AnyIRI, ObservableSet[AdminPermission] | None], None]

    def __init__(self,
                 data: Dict[QName | AnyIRI, Set[AdminPermission] | ObservableSet[AdminPermission]] | None = None,
                 on_change: Callable[[QName | AnyIRI, ObservableSet[AdminPermission] | None], None] = None) -> None:
        """
        Constructor of the class. The class acts like a dictionary and allows the access to the permission
        set for a project using the QName of the project as the key: ```perms = t.in_project[QName('ex:proj')]```.
        It supports the getting, setting and deleting a permission set.
        In addition, the following methods are implemented:

        - _get()_: gets the permission set or returns `None`if it doesn't exist for the given project'
        - _copy()_: Creates a deep copy of the given instance
        - _==_: Check for equality of 2 instances
        - _!=_: Check for inequality of 2 instances

        :param data: A dictionary with the QName of the project as key and the set of permissions as value
        :type data: Dict[str | QName, Set[AdminPermission] | ObservableSet[AdminPermission]] | None
        :param on_change: A callable that is called whenever the instance has been changed
        :type on_change: Callable[[str, ObservableSet[AdminPermission] | None], None]
        """
        self.__data = {}
        if data is not None:
            for key, value in data.items():
                if isinstance(key, str):
                    if '§' in key:
                        t, k = key.split('§')
                        match (t):
                            case 'QName':
                                key = QName(k)
                            case 'AnyIRI':
                                key = AnyIRI(k)
                            case 'NamespaceIri':
                                key = NamespaceIRI(k)
                            case 'OmasStringLiteral':
                                key = OmasStringLiteral(k)
                self.__data[key] = ObservableSet(value, on_change=self.__on_set_changed, on_change_data=key)

            #self.__data = {key: ObservableSet(val, on_change=self.__on_set_changed, on_change_data=key) for key, val in data.items()}
        self.__on_change = on_change

    def __on_set_changed(self, oldset: ObservableSet[AdminPermission], key: QName | str):
        if self.__on_change is not None:
            self.__on_change(key, oldset) ## Action.MODIFY

    def __getitem__(self, key: QName | AnyIRI) -> ObservableSet[AdminPermission]:
        return self.__data[key]

    def __setitem__(self, key: QName | AnyIRI, value: ObservableSet[AdminPermission] | Set[AdminPermission]) -> None:
        if self.__data.get(key) is None:
            if self.__on_change is not None:
                self.__on_change(key, None) ## Action.CREATE: Create a new inProject connection to a new project and add permissions
        else:
            if self.__on_change is not None:
                self.__on_change(key, self.__data[key].copy())  ## Action.REPLACE Replace all the permission of the given connection to a project
        self.__data[key] = ObservableSet(value, on_change=self.__on_set_changed)

    def __delitem__(self, key: QName | AnyIRI) -> None:
        if self.__data.get(key) is not None:
            if self.__on_change is not None:
                self.__on_change(key, self.__data[key].copy())  ## Action.DELETE
            del self.__data[key]

    def __str__(self) -> str:
        s = '';
        for k, v in self.__data.items():
            s += f'{k} ({type(k)}): {v}\n'
        return s

    def copy(self) -> Self:
        data_copy = deepcopy(self.__data)
        on_change_copy = self.__on_change
        return InProjectClass(data_copy, on_change_copy)

    def __eq__(self, other: Self) -> bool:
        return self.__data == other.__data

    def __ne__(self, other: Self) -> bool:
        return self.__data != other.__data

    def get(self, key: AnyIRI | QName) -> ObservableSet[AdminPermission] | None:
        return self.__data.get(key)

    def items(self) -> ItemsView[AnyIRI | QName, ObservableSet[AdminPermission]]:
        return self.__data.items()

    def keys(self) -> KeysView:
        return self.__data.keys()

    def _as_dict(self) -> dict:
        tmp = {f'{key.__class__.__name__}§{str(key)}': value for key, value in self.__data.items()}
        #return {'data': self.__data}
        return {'data': tmp}


if __name__ == '__main__':
    in_proj = InProjectClass({QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                          AdminPermission.ADMIN_RESOURCES,
                                                          AdminPermission.ADMIN_CREATE}})
    jsonstr = json.dumps(in_proj, default=serializer.encoder_default)
    in_proj2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
    for k, v in in_proj2.items():
        print(f'{k} ({type(k)}) = {v}')