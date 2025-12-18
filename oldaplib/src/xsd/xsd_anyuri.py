import re
from typing import Self, Any, Dict

from pystrict import strict
from validators import url

from oldaplib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd


#@strict
@serializer
class Xsd_anyURI(Xsd):
    """
    # AnyIRI

    Represents a generic IRI (corresponds to the XML datatype [AnyURI](https://www.w3.org/TR/xmlschema11-2/#anyURI).
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

    Validation uses regex patterns (always) and the XsdValidator library (optional)
    """
    _value: str
    _append_allowed: bool
    _uri_pattern = re.compile(
        r'^[a-zA-Z][a-zA-Z0-9+.-]*:'  # Scheme
        r'//'  # Authority separator
        r'([a-zA-Z0-9._~%!$&\'()*+,;=:@-]*@)?'  # Optional userinfo
        r'('
        r'(\[[0-9a-fA-F:.]+\])|'  # IPv6 address
        r'(([a-zA-Z0-9._~%!$&\'()*+,;=:-]+)|'  # Domain name
        r'([a-zA-Z0-9.-]+(\.[a-zA-Z]{2,})+))'  # Or domain name with TLD
        r')'
        r'(:\d{2,5})?'  # Optional port
        r'(/[a-zA-Z0-9._~%!$&\'()*+,;=:@-]*)*'  # Path
        r'(\?[a-zA-Z0-9._~%!$&\'()*+,;=:@/?-]*)?'  # Optional query
        r'(#[-a-zA-Z0-9._~%!$&\'()*+,;=:@/?]*)?')  # Optional fragment

    def __init__(self, value: Self | str, validate: bool = False):
        """
        Constructor for the AnyIRI class. It performs a consistency check if the given string is an IRI.
        If the validate parameter is true, the extensive XsdValidator library will be used.
        :param value: A string or another AnyIRI instance
        :type value: Xsd_anyURI | str
        :param validate: Whether to validate the IRI against the IRI XML schema
        :type validate: bool
        :raises OldapErrorValue: The given string is not an IRI
        """
        super().__init__(value)
        if isinstance(value, Xsd_anyURI):
            self._value = value._value
            self._append_allowed = value.append_allowed
        else:
            if isinstance(value, str):
                value = value.replace("<", "").replace(">", "")
            if value.startswith("urn:"):
                if not re.match(r'^urn:[a-z0-9][a-z0-9-]{0,31}:[^\s]+', str(value)):
                    raise OldapErrorValue(f'Invalid URN format for "{value}".')
            elif value.startswith("http"):
                if not re.match(self._uri_pattern, str(value)):
                    raise OldapErrorValue(f'Invalid string "{value}" for xsd:anyURI (regexp).')
                if validate:
                    if not XsdValidator.validate(XsdDatatypes.anyURI, str(value)):
                        raise OldapErrorValue(f'Invalid string "{value}" for xsd:anyURI (validator)')
                    else:
                        if not url(str(value)):
                            raise OldapErrorValue(f'Invalid string "{value}" for xsd:anyURI (url()).')
            else:
                raise OldapErrorValue(f'Invalid string "{value}" for anyURI (no urn:/http:)')
            self._value = str(value)
        self._append_allowed = self._value[-1] == '/' or self._value[-1] == '#'

    def __repr__(self) -> str:
        """
        Returns the Python representation of the AnyIRI
        :return: Python representation of the AnyIRI
        :rtype: str
        """
        return f'Xsd_anyURI("{self._value}")'

    def __str__(self) -> str:
        """
        Returns the string representation of the AnyIRI
        :return: String representation of the AnyIRI
        :rtype: str
        """
        return f'{self._value}'

    def __eq__(self, other: Any | None) -> bool:
        """
        Test for equality of two AnyIRIs
        :param other: A string/AnyIRI to be compared
        :type other: AnyIRI | None
        :return: True or False
        :rtype: bool
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
        :rtype: bool
        """
        if other is None:
            return True
        return self._value != str(other)

    def __hash__(self) -> int:
        """
        Returns the hash of the AnyIRI
        :return: Hash of the AnyIRI
        :rtype: int
        """
        return self._value.__hash__()

    def __len__(self):
        """
        Returns the number of characters in the AnyIRI
        :return: Number of characters in the AnyIRI
        :rtype: int
        """
        return len(self._value)

    def _as_dict(self) -> dict[str, str]:
        """
        Used internally for JSON serialization using @serialisation decorator
        :return: dict for JSON serializer
        :rtype: dict[str, str]
        """
        return {'value': self._value}

    @property
    def toRdf(self) -> str:
        """
        Returns the RDF representation of the AnyIRI
        :return: RDF string
        :rtype: str
        """
        return f'"{self._value}"^^xsd:anyURI'

    @property
    def append_allowed(self) -> bool:
        """
        Property which is "True" if the AnyURI is ending with "#" or "/"
        :return: True of False
        :rtype: bool
        """
        return self._append_allowed

    @property
    def value(self) -> str:
        """
        Property which returns the AnyIRI value
        :return: string
        :rtype: str
        """
        return self._value


if __name__ == '__main__':
    iri = Xsd_anyURI('urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b')