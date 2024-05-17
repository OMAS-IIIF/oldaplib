"""
This module implements the enumerations for the permissions.
"""
from enum import Enum, unique
from typing import Self

from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.helpers.serializer import serializer


@unique
@serializer
class AdminPermission(Enum):
    """
    Administrative permissions. The following permissions are supported:

    - _AdminPermission.ADMIN_OLDAP_: Quasi root permission. This useer can do everything (**dangerous!**)
    - _AdminPermission.ADMIN_USERS_: Allows to add/modify/delete users for the project this permission is given for
    - _AdminPermission.ADMIN_RESOURCES_: Override resources permission for the resources in the given project
    - _AdminPermission.ADMIN_MODEL: Change the data model
    - _AdminPermission.ADMIN_CREATE: Create new resources in the given project
    """
    ADMIN_OLDAP = 'oldap:ADMIN_OLDAP'
    ADMIN_USERS = 'oldap:ADMIN_USERS'
    ADMIN_PERMISSION_SETS = 'oldap:ADMIN_PERMISSION_SETS'
    ADMIN_RESOURCES = 'oldap:ADMIN_RESOURCES'
    ADMIN_MODEL = 'oldap:ADMIN_MODEL'
    ADMIN_CREATE = 'oldap:ADMIN_CREATE'
    ADMIN_LISTS = 'oldap:ADMIN_LISTS'

    @property
    def toRdf(self):
        return self.value


@unique
@serializer
class DataPermission(Enum):
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
    DATA_RESTRICTED = 'oldap:DATA_RESTRICTED'
    DATA_VIEW = 'oldap:DATA_VIEW'
    DATA_EXTEND = 'oldap:DATA_EXTEND'
    DATA_UPDATE = 'oldap:DATA_UPDATE'
    DATA_DELETE = 'oldap:DATA_DELETE'
    DATA_PERMISSIONS = 'oldap:DATA_PERMISSIONS'

    @property
    def toRdf(self):
        return self.value

    @classmethod
    def from_string(cls, permission_string: str) -> Self:
        for member in cls:
            if f'oldap:{member.name}' == permission_string:
                return member
        raise ValueError(f'{permission_string} is not in DataPermission enum.')

