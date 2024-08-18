import threading
from enum import EnumMeta, Enum, unique
from typing import Self

import requests

from oldaplib.src.connection import Connection
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_qname import Xsd_QName


class PermissionWithValue(Enum):
    def __new__(cls, value: Xsd_QName | str, numeric: Xsd_integer | int):
        member = object.__new__(cls)
        member._value = Xsd_QName(value, validate=False)
        member._name = member._value.fragment  # Extract fragment for example
        member._numeric = Xsd_integer(numeric, validate=False)
        return member

    def __str__(self) -> str:
        return str(self.value)

    @property
    def value(self) -> Xsd_QName:
        return self._value

    @property
    def numeric(self) -> Xsd_integer:
        return self._numeric

@unique
@serializer
class DataPermission(PermissionWithValue):
    """
    Data permissions are given to permission sets. These permissions determine what a user is allowed to do
    with resources. Each resource as well as each user is connected to zero, one or several permission sets.
    See [Permission concept](permission_concept).

    - _DATA_RESTRICTED_: Restricted view rights
    - _DATA_VIEW_: Full view rights
    - _DATA_EXTEND_: User may extend data, but is not allowed to modify/delete existing data
    -_DATA_UPDATE_: User may update data, but is not allowed to delete date
    -_DATA_DELETE_: User may delete data
    -_DATA_PERMISSIONS_: User may change the permission of data
    """
    DATA_RESTRICTED = ('oldap:DATA_RESTRICTED', 1)
    DATA_VIEW = ('oldap:DATA_VIEW', 2)
    DATA_EXTEND = ('oldap:DATA_EXTEND', 3)
    DATA_UPDATE = ('oldap:DATA_UPDATE', 4)
    DATA_DELETE = ('oldap:DATA_DELETE', 5)
    DATA_PERMISSIONS = ('oldap:DATA_PERMISSIONS', 6)

    @property
    def toRdf(self):
        return self.value

    @classmethod
    def from_string(cls, permission_string: str) -> Self:
        for member in cls:
            if f'oldap:{member.name}' == permission_string:
                return member
        raise ValueError(f'{permission_string} is not in DataPermission enum.')


