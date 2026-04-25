from typing import Self

from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


@serializer
class HListNode(Xsd_QName):

    def __init__(self, value: Self | str | Xsd_NCName, fragment: str | Xsd_NCName | None = None, validate: bool = False) -> None:
        super().__init__(value, fragment, validate=validate)

    def __repr__(self):
        return f'HListNode("{self.value}")'

    @property
    def listId(self) -> str:
        parts = self._value.split(':')
        return parts[0]

    @property
    def nodeId(self) -> str:
        parts = self._value.split(':')
        return parts[1]