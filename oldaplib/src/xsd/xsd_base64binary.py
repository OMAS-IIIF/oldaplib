import re
from typing import Self, Type

from pystrict import strict

from oldaplib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd


#@strict
@serializer
class Xsd_base64Binary(Xsd):
    """
    Class that encodes and decodes binary data using the XML Scheme [xsd:base64Binary](https://www.w3.org/TR/xmlschema11-2/#base64Binary) datatype
    """

    __value: bytes

    def __init__(self, value: Self | bytes, validate: bool = False):
        """
        Constructor that encodes and decodes binary data using the XML Scheme xsd:base64Binary datatype.
        Validation uses regexp patterns and the XsdValidator library.
        :param value: Either another instance of Xsd_base64Binary or a bytes object
        :type value: Xsd_base64Binary | bytes
        :param validate: Whether to validate the binary data
        :type validate: bool
        :raises OldapErrorValue: If the value is not an instance of Xsd_base64Binary or a valid bytes object
        """
        if isinstance(value, Xsd_base64Binary):
            self.__value = value.__value
        elif isinstance(value, bytes):
            self.__value = value
            if validate:
                if len(value) % 4 != 0:
                    raise OldapErrorValue(f'Invalid string "{value}" for xsd:base64Binary.')
                if not bool(re.match(r'^[A-Za-z0-9+/]+={0,2}$', value.decode('utf-8'))):
                    raise OldapErrorValue(f'Invalid string "{value}" for xsd:base64Binary.')
                if not XsdValidator.validate(XsdDatatypes.base64Binary, value.decode('utf-8')):
                    raise OldapErrorValue(f'Invalid string "{value}" for xsd:base64Binary.')
        else:
            OldapErrorValue("Xsd_base64Binary requires bytes parameter")

    def __str__(self):
        """
        String representation based on utf-8 encoding
        :return: string
        :rtype: str
        """
        return self.__value.decode('utf-8')

    def __repr__(self):
        """
        String representation based on utf-8 encoding as used for constructor
        :return: string
        :rtype: str
        """
        return f'Xsd_base64Binary(b"{self.__value.decode('utf-8')}")'

    def __eq__(self, other: Self | None) -> bool:
        """
        Compare for equality
        :param other: Another Xsd_base64Binary instance
        :type other: Xsd_base64Binary | None
        :return: True or False
        :rtype: bool
        """
        if other is None:
            return False
        return self.__value == other.__value

    def __hash__(self) -> int:
        """
        Return the hash value for the object
        :return: Hash value
        :rtype: int
        """
        return hash(self.__value)

    def _as_dict(self) -> dict[str, bytes]:
        """
        Used internally for JSON serialization using @serialisation decorator
        :return: dict for JSON serialization
        """
        return {'value': self.__value}

    @classmethod
    def fromRdf(cls: Type['XsdBase64Binary'], value: str) -> Type['XsdBase64Binary']:
        """
        Converts an Xsd_base64Binary RDF string into an Xsd_base64Binary object
        :param value: RDF string
        :return: Instance of Xsd_base64Binary
        :rtype: Xsd_base64Binary
        """
        return cls(value.encode('utf-8'), validate=False)

    @property
    def toRdf(self) -> str:
        """
        Converts an Xsd_base64Binary object to an RDF string
        :return: RDF string
        :rtype: str
        """
        return f'"{self.__value.decode('utf-8')}"^^xsd:base64Binary'

    @property
    def value(self) -> bytes:
        """
        Converts an Xsd_base64Binary object to a bytes object
        :return: bytes
        :rtype: bytes
        """
        return self.__value

