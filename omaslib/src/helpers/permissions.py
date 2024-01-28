from enum import Enum, unique

from omaslib.src.helpers.datatypes import QName

@unique
class AdminPermission(Enum):
    ADMIN_OLDAP = QName('omas:ADMIN_OLDAP')
    ADMIN_USERS = QName('omas:ADMIN_USERS')
    ADMIN_RESOURCES = QName('omas:ADMIN_RESOURCES')
    ADMIN_MODEL = QName('omas:ADMIN_MODEL')
    ADMIN_CREATE = QName('omas:ADMIN_CREATE')


@unique
class DataPermission(Enum):
    DATA_RESTRICTED = 1
    DATA_VIEW = 2
    DATA_EXTEND = 3
    DATA_UPDATE = 4
    DATA_DELETE = 5
    DATA_PERMISSIONS = 6


