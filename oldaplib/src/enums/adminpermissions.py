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

    @property
    def toRdf(self):
        return self.value


