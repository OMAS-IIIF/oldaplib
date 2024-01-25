from enum import Enum


class AdminRights(Enum):
    ADMIN_PROJECT = 1
    ADMIN_USERS = 2
    ADMIN_RESOURCES = 3
    ADMIN_NONE = 4


class GroupRights(Enum):
    CHANGE_PERMISSIONS = 1
    DELETE = 2
    UPDATE = 3
    READ = 4


