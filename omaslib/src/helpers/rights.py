from enum import Enum

from omaslib.src.helpers.datatypes import QName


class AdminRights(Enum):
    ADMIN_OLDAP = QName('omas:ADMIN_OLDAP')
    ADMIN_USERS = QName('omas:ADMIN_USERS')
    ADMIN_RESOURCES = QName('omas:ADMIN_RESOURCES')
    ADMIN_MODEL = QName('omas:ADMIN_MODEL')
    ADMIN_CREATE = QName('omas:ADMIN_CREATE')


class GroupRights(Enum):
    CHANGE_PERMISSIONS = 1
    DELETE = 2
    UPDATE = 3
    READ = 4


