from typing import Self, Dict

from pystrict import strict

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI


@strict
@serializer
class NamespaceIRI(Xsd_anyURI):
    """
    # NamespaceIRI

    An IRI representing a namespace. A namespace is an IRI that ends with a fragment separates, that is a "#" or "/".
    It is a subclass of AnyIRI and checks in the constructor for the termination with a "#" or "/".
    """

    def __init__(self, value: Self | Xsd_anyURI | str):
        """
        Constructor for the NamespaceIRI
        :param value: A string or another NamespaceIRI
        """
        super().__init__(value)
        if not self._append_allowed:
            raise OmasErrorValue("NamespaceIRI must end with '/' or '#'!")

    def __repr__(self) -> str:
        return f'NamespaceIRI("{self.value}")'

    def __add__(self, other: str) -> Xsd_anyURI:
        return Xsd_anyURI(self._value + other)

