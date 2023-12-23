from typing import Dict

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NCName, QName
from omaslib.src.model import Model
from omaslib.src.propertyclass import PropertyClass
from omaslib.src.resourceclass import ResourceClass


class DataModel(Model):
    __graph: NCName
    __context: Context
    __propclasses: Dict[QName, PropertyClass]
    __resclasses: Dict[QName, ResourceClass]

    def __init__(self, con: Connection, graph: NCName):
        super().__init__(con)
        self.__graph = graph
        self.__context = Context(name=graph)

