from abc import ABC, abstractmethod
from typing import Self, Dict


class Xsd(ABC):
    """
    Abstract base class for XSD classes.
    """

    @abstractmethod
    def __init__(self, value: Self | str):
        pass

    @abstractmethod
    def __str__(self) -> str:
        pass

    @abstractmethod
    def __repr__(self) -> str:
        pass

    @classmethod
    def fromRdf(cls, value: str) -> Self:
        return cls(value)

    @property
    @abstractmethod
    def toRdf(self) -> str:
        pass

    @abstractmethod
    def _as_dict(self) -> dict[str, str]:
        pass
