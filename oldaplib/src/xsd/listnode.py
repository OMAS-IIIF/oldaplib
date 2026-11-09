from dataclasses import dataclass
from typing import Self

from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.helpers.oldaperror import OldapErrorValue
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
        prefix = parts[0]
        if prefix.startswith('L-'):
            prefix = prefix[2:]
        return prefix

    @property
    def nodeId(self) -> str:
        parts = self._value.split(':')
        return parts[1]


@serializer
@dataclass(frozen=True)
class HListNodeRef:
    listId: Xsd_NCName
    nodeId: Xsd_NCName
    validate: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, 'listId', Xsd_NCName(self.listId, validate=self.validate))
        object.__setattr__(self, 'nodeId', Xsd_NCName(self.nodeId, validate=self.validate))

    def __str__(self) -> str:
        return f'{self.listId}:{self.nodeId}'

    def __repr__(self) -> str:
        return f'HListNodeRef("{self.listId}:{self.nodeId}")'

    @property
    def as_qname(self) -> HListNode:
        return HListNode(f'L-{self.listId}:{self.nodeId}', validate=False)

    @classmethod
    def from_value(cls, value: Self | HListNode | str, validate: bool = False) -> Self:
        if isinstance(value, cls):
            return value
        if isinstance(value, HListNode):
            return cls(value.listId, value.nodeId, validate=validate)
        if isinstance(value, str):
            try:
                node = HListNode(value, validate=validate)
            except OldapErrorValue as err:
                raise OldapErrorValue(f'Invalid hierarchical list node reference "{value}".') from err
            return cls(node.listId, node.nodeId, validate=validate)
        raise OldapErrorValue(f'Invalid hierarchical list node reference "{value}" (type: {type(value).__name__}).')
