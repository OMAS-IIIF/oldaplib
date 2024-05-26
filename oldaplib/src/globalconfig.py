from oldaplib.src.helpers.singletonmeta import SingletonMeta
from oldaplib.src.iconnection import IConnection
from oldaplib.src.project import Project


class GlobalConfig(metaclass=SingletonMeta):
    __sysproject: Project

    def __init__(self, con: IConnection):
        self.__sysproject = Project.read(con, "oldap")

    @property
    def sysproject(self) -> Project:
        return self.__sysproject