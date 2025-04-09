"""
This module implements the enumerations for the permissions.
"""
from enum import Enum, unique

#from oldaplib.src.connection import Connection
from oldaplib.src.helpers.serializer import serializer


@unique
@serializer
class AdminPermission(Enum):
    """
    Administrative permissions. The following permissions are supported:

    - _AdminPermission.ADMIN_OLDAP_: Quasi root permission. This user can do everything (**dangerous!**)
    - _AdminPermission.ADMIN_USERS_: Allows to add/modify/delete users for the project this permission is given for
    - _AdminPermission.ADMIN_RESOURCES_: Override resources permission for the resources in the given project
    - _AdminPermission.ADMIN_MODEL_: Change the data model
    - _AdminPermission.ADMIN_CREATE_: Create new resources in the given project
    """
    ADMIN_OLDAP = 'oldap:ADMIN_OLDAP'  # Quasi root permission. This user can do everything (**dangerous!**)
    ADMIN_USERS = 'oldap:ADMIN_USERS'  # Allows to add/modify/delete users for the project this permission is given for
    ADMIN_PERMISSION_SETS = 'oldap:ADMIN_PERMISSION_SETS'  # Allows to add/modify/delete PermissionSets
    ADMIN_RESOURCES = 'oldap:ADMIN_RESOURCES'  # Override resources permission for the resources in the given project
    ADMIN_MODEL = 'oldap:ADMIN_MODEL'  # Change the data model
    ADMIN_CREATE = 'oldap:ADMIN_CREATE'  # Create new resources in the given project
    ADMIN_LISTS = 'oldap:ADMIN_LISTS'  # Allows to add/modify/delete lists

    def __new__(cls, value):
        # Allow plain names like 'ADMIN_OLDAP'
        if not value.startswith('oldap:'):
            value = f'oldap:{value}'
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    @classmethod
    def from_string(cls, key):
        # Accept either 'ADMIN_OLDAP' or 'oldap:ADMIN_OLDAP'
        if not key.startswith('oldap:'):
            key = f'oldap:{key}'
        return cls(key)

    @property
    def toRdf(self):
        return self.value


