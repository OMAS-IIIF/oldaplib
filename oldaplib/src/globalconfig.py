from oldaplib.src.helpers.singletonmeta import SingletonMeta
from oldaplib.src.iconnection import IConnection
from oldaplib.src.project import Project


class GlobalConfig(metaclass=SingletonMeta):
    """
    Manages global configuration and provides access to specific project instances.

    The `GlobalConfig` class is designed to hold and manage references to key
    project instances, specifically the system project and shared project, which
    are read and initialized during the creation of the class instance. This is
    achieved using the SingletonMeta metaclass to ensure a single shared instance
    globally.

    :ivar sysproject: The system project instance used for system-related
        configurations and operations.
    :type sysproject: Project
    :ivar sharedproject: The shared project instance used for shared configurations
        and operations.
    :type sharedproject: Project
    """
    __sysproject: Project
    __sharedproject: Project

    def __init__(self, con: IConnection):
        self.__sysproject = Project.read(con, "oldap")
        self.__sharedproject = Project.read(con, "shared")

    @property
    def sysproject(self) -> Project:
        return self.__sysproject

    @property
    def sharedproject(self) -> Project:
        return self.__sharedproject