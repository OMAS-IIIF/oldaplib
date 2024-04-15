import re
from typing import Self

from pystrict import strict

from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_string import Xsd_string


@strict
@serializer
class Xsd_token(Xsd):
    """
    Implements the XML Schema [xsd:token](https://www.w3.org/TR/xmlschema11-2/#token) datatype
    """
    __value: str

    def __init__(self, value: Self | str):
        """
        Constructor for the Xsd_token class.
        :param value: A Xml_token instance or a valid token string
        :type value: Xsd_token | str
        :raises OmasErrorValue: If the token is invalid
        """
        if isinstance(value, Xsd_token):
            self.__value = value.__value
        else:
            if not XsdValidator.validate(XsdDatatypes.token, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:token.')
            if not re.match("^[^\\s]+(\\s[^\\s]+)*$", value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:token.')
            if re.match(".*[\n\r\t].*", value) is not None:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:token.')
            self.__value = value

    def __str__(self):
        """
        String representation of the Xsd_token instance.
        :return: String representation of the Xsd_token instance.
        :rtype: str
        """
        return self.__value

    def __repr__(self):
        """
        Python constructor string representation of the Xsd_token instance.
        :return: Python constructor string representation of the Xsd_token instance.
        :rtype: str
        """
        return f'Xsd_token("{Xsd_string.escaping(str(self))}")'

    def __eq__(self, other: Self | str | None) -> bool:
        """
        Compares two Xsd_token instances for equality.
        :param other: an other Xsd_token instance or a string
        :return: True or False
        """
        if other is None:
            return False
        if isinstance(other, Xsd_token):
            return self.__value == other.__value
        else:
            return self.__value == str(other)


    def __hash__(self) -> int:
        """
        Hash value of the Xsd_token instance.
        :return: Hash value
        :rtype: int
        """
        return super().__hash__()

    @classmethod
    def fromRdf(cls, value: str) -> Self:
        """
        Create a Xsd_token instance from an xs:token RDF Value (string must be without '^^xsd:token' data indicator)
        :param value:
        :return:
        """
        return cls(Xsd_string.unescaping(value))


    def _as_dict(self) -> dict[str, str]:
        """
        Internal method used to serialize to JSON (@serializer decorator)
        :return: dict
        """
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        """
        RDF representation of the Xsd_token instance.
        :return: RDF representation of the Xsd_token instance.
        :rtype: str
        """
        return f'"{Xsd_string.escaping(str(self))}"^^xsd:token'

    @property
    def value(self) -> str:
        """
        String representation of the Xsd_token instance.
        :return: String representation of the Xsd_token instance.
        """
        return self.__value
