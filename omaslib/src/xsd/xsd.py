from abc import ABC, abstractmethod
from typing import Self, Dict


class Xsd(ABC):
    """
    Abstract base class for XSD classes.
    """

    @abstractmethod
    def __init__(self, value: Self | str):
        """
        Initialize the XSD class. Must not be called by subclasses
        :param value:
        """
        pass

    @abstractmethod
    def __str__(self) -> str:
        """
        Return the string representation of the XSD class.
        :return: string representation of the XSD class.
        """
        pass

    @abstractmethod
    def __repr__(self) -> str:
        """
        Return the string representation of the XSD class as it would be for constructing the XSD class.
        :return: string representation of the XSD class.
        """
        pass

    @classmethod
    def fromRdf(cls, value: str) -> Self:
        """
        Create an XSD instance from a RDF value string.
        :param value: String with RDF value string.
        :return: Instance of the XSD class.
        """
        return cls(value)

    @property
    @abstractmethod
    def toRdf(self) -> str:
        """
        Property returning the RDF representation of the XSD class.
        :return: String for the RDF representation of the XSD class.
        """
        pass

    @abstractmethod
    def _as_dict(self) -> dict[str, str]:
        """
        Used for the JSON serialization of the XSD class.
        :return:
        """
        pass
