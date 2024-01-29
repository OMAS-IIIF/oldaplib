from enum import Enum, unique

from omaslib.src.helpers.datatypes import QName
from omaslib.src.helpers.serializer import serializer


@unique
@serializer
class AdminPermission(Enum):
    ADMIN_OLDAP = 'omas:ADMIN_OLDAP'
    ADMIN_USERS = 'omas:ADMIN_USERS'
    ADMIN_RESOURCES = 'omas:ADMIN_RESOURCES'
    ADMIN_MODEL = 'omas:ADMIN_MODEL'
    ADMIN_CREATE = 'omas:ADMIN_CREATE'


@unique
@serializer
class DataPermission(Enum):
    DATA_RESTRICTED = 1
    DATA_VIEW = 2
    DATA_EXTEND = 3
    DATA_UPDATE = 4
    DATA_DELETE = 5
    DATA_PERMISSIONS = 6


