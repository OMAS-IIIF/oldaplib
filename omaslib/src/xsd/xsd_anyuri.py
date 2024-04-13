import re
from typing import Self, Any, Dict

from pystrict import strict
from validators import url

from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd


@strict
@serializer
class Xsd_anyURI(Xsd):
    """
    # AnyIRI

    Represents a generic IRI (corresonds to the XML datatype [AnyURI](https://www.w3.org/TR/xmlschema11-2/#anyURI).
    This class is used to represent a generic IRI. This class has the following methods:

    - Constructor method `__init__`
    - Accessor methods `XXX.value`
    - Comparison methods `==`, `!=`
    - Operators for LangString manipulation:
        - Append a string or NCName to an AnyIRI instance: `+`, `+=`
    - Serializer methods `str(XXX)`, `repr(XXX)`,
    - RDF property `toRdf`
    - Hashing methods `hash(XXX)`
    - information `len(XXX)`, `XXX.append_allowed`
    """
    _value: str
    _append_allowed: bool

    def __init__(self, value: Self | str):
        """
        Constructor for the AnyIRI class. It performs a consistency check if the given string is an IRI
        :param value: A string or another AnyIRI instance
        :type value: Xsd_anyURI | str
        :raises OmasErrorValue: The given string is not an IRI
        """
        super().__init__(value)
        if isinstance(value, Xsd_anyURI):
            self._value = str(value)
        else:
            if isinstance(value, str):
                value = value.replace("<", "").replace(">", "")
            if not XsdValidator.validate(XsdDatatypes.anyURI, value):
                raise OmasErrorValue(f'Invalid string "{value}" for anyURI')
            if value.startswith("urn:"):
                if not re.match(r'^urn:[a-z0-9][a-z0-9-]{0,31}:[^\s]+', value):
                    raise OmasErrorValue(f'Invalid URN format for "{value}".')
            else:
                if not url(value):
                    raise OmasErrorValue(f'Invalid string "{value}" for xsd:anyURI.')
            self._value = value
        self._append_allowed = self._value[-1] == '/' or self._value[-1] == '#'

    def __repr__(self) -> str:
        """
        Returns the Python representation of the AnyIRI
        :return: Python representation of the AnyIRI
        """
        return f'Xsd_anyURI("{self._value}")'

    def __str__(self) -> str:
        """
        Returns the string representation of the AnyIRI
        :return: String representation of the AnyIRI
        """
        return f'{self._value}'

    def __eq__(self, other: Any | None) -> bool:
        """
        Test for equality of two AnyIRIs
        :param other: A string/AnyIRI to be compared
        :type other: AnyIRI | None
        :return: True or False
        """
        if other is None:
            return False
        if isinstance(other, str):
            return self._value == other
        return isinstance(other, Xsd_anyURI) and self._value == other._value

    def __ne__(self, other: Any) -> bool:
        """
        Test for inequality of two
        :param other: A string/AnyIRI to be compared
        :type other: AnyIRI | None
        :return: True or False
        """
        if other is None:
            return True
        return self._value != str(other)

    def __hash__(self) -> int:
        """
        Returns the hash of the AnyIRI
        :return: Hash of the AnyIRI
        """
        return self._value.__hash__()

    def __len__(self):
        """
        Returns the number of characters in the AnyIRI
        :return: Number of characters in the AnyIRI
        """
        return len(self._value)

    def _as_dict(self) -> dict[str, str]:
        return {'value': self._value}

    @property
    def toRdf(self) -> str:
        """
        Returns the RDF representation of the AnyIRI
        :return: RDF string
        """
        return f'"{self._value}"^^xsd:anyURI'

    @property
    def append_allowed(self) -> bool:
        """
        Property which is "True" if the AnyURI is ending with "#" or "/"
        :return: True of False
        """
        return self._append_allowed

    @property
    def value(self) -> str:
        """
        Property which returns the AnyIRI value
        :return: string
        """
        return self._value
