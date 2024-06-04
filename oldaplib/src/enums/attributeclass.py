from enum import Enum
from typing import Type, Self

from oldaplib.src.xsd.xsd_qname import Xsd_QName


class AttributeClass(Enum):
    def __new__(cls, value: Xsd_QName | str, mandatory: bool, immutable: bool, datatype: Type):
        member = object.__new__(cls)
        member._value = Xsd_QName(value, validate=False)
        member._name = member._value.fragment  # Extract fragment for example
        member._mandatory = mandatory
        member._immutable = immutable
        member._datatype = datatype
        return member

    def __str__(self) -> str:
        return str(self.value)

    @property
    def value(self) -> Xsd_QName:
        return self._value

    @property
    def datatype(self) -> Type:
        return self._datatype

    @property
    def mandatory(self) -> bool:
        return self._mandatory

    @property
    def immutable(self) -> bool:
        return self._immutable

    @classmethod
    def from_value(cls, value: Xsd_QName | str) -> Self:
        value = Xsd_QName(value)
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"No member with value {value} ({type(value).__name__})found")

    @classmethod
    def from_name(cls, name: str) -> Self:
        for member in cls:
            if member._name == name:
                return member
        raise ValueError(f"No member with name {name} found")

    @property
    def to_rdf(self) -> str:
        return self._value.toRdf
