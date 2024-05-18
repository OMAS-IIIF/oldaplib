from oldaplib.src.iconnection import IConnection
from oldaplib.src.project import Project


class SingletonMeta(type):
    """
    This is a thread-safe implementation of Singleton.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

class GlobalConfig(metaclass=SingletonMeta):
    __sysproject: Project

    def __init__(self, con: IConnection):
        self.__sysproject = Project.read(con, "oldap")

    @property
    def sysproject(self) -> Project:
        return self.__sysproject