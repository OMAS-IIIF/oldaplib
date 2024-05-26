import re
import sys
import traceback
from typing import Self, Any

from pystrict import strict

from oldaplib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd


#@strict
@serializer
class Xsd_NCName(Xsd):
    """
    Implements the XML Schema [xsd:NCName](https://www.w3.org/TR/xmlschema11-2/#NCName) datatype.

    NCName is according to the XML datatype an "unqualified name". See the
    [W3C documentation](https://www.w3.org/TR/xmlschema-2/#NCName).
    This class implements the following operations/methods:

    - *Constructor*: NCName(string), NCName(NCName)
    - *repr()*: Get the representation of the NCName
    - *str()*: Get the string representation of the NCName
    - *==*: Compare a NCName to another NCName or string for equality
    - *!=*: Compare a NCName to another NCName or string for inequality
    - *hash()*: Get the hash of the NCName

    """
    __value: str

    def __init__(self, value: Self | str | None, validate: bool = True):
        """
        Initialize the NCName
        :param value: Either a string conforming to the QName syntax or a NCName
        :type value: Xsd_NCName | str
        :raises OldapErrorValue: If the value is not a valid NCName
        """
        if value is None:
            self.__value = ""
        elif isinstance(value, Xsd_NCName):
            self.__value = value.__value
        else:
            if not bool(re.match(r'^[A-Za-z_][A-Za-z0-9_.-]*$', value)):
                raise OldapErrorValue(f'Invalid string "{value}" for NCName')
            if validate:
                if not XsdValidator.validate(XsdDatatypes.NCName, value):
                    raise OldapErrorValue(f'Invalid string "{value}" for NCName')
            self.__value = value

    def __bool__(self):
        return bool(self.__value)

    def __repr__(self) -> str:
        """
        Return the representation string
        :return: Python representation of the instance
        :rtype: str
        """
        return f'Xsd_NCName("{self.__value}")'

    def __str__(self) -> str:
        """
        Return the value as string
        :return: Value as string
        :rtype: str
        """
        return self.__value

    def __eq__(self, other: Self | str | None) -> bool:
        """
        Test two NCNames for equality
        :param other: The other NCName/str to compare
        :return: True of False
        :rtype: bool
        """
        if other is None:
            return False
        if isinstance(other, Xsd_NCName):
            return self.__value == other.__value
        elif isinstance(other, str):
            return self.__value == other
        else:
            raise OldapErrorValue(f'Cannot compare to {type(other)}')

    def __ne__(self, other: Self | str) -> bool:
        """
        Test for non-equality
        :param other: The other NCName/str to compare
        :return: True of False
        :rtype: bool
        """
        if isinstance(other, Xsd_NCName):
            return self.__value != other.__value
        elif isinstance(other, str):
            return self.__value != other
        else:
            raise OldapErrorValue(f'Cannot compare to {type(other)}')

    def __add__(self, other: Self | str) -> Self:
        """
        Add two NCNames or an NCName and a string
        :param other: NCName or string to add
        :return: Concatenated NCName
        :rtype: Xsd_NCName
        :raises OldapErrorValue: If the other value is not a valid NCName
        """
        if not isinstance(other, Xsd_NCName):
            other = Xsd_NCName(other)
        return Xsd_NCName(self.__value + other.__value)

    def __iadd__(self, other: Self | str) -> Self:
        """
        Add two NCNames, or an NCName and a string
        :param other: A NCName or string to add
        :return: Self
        :rtype: Xsd_NCName
        :raises OldapErrorValue: If the other value is not a valid NCName
        """
        if not isinstance(other, Xsd_NCName):
            other = Xsd_NCName(other)
        self.__value += other.__value
        return self

    def __hash__(self) -> int:
        """
        Get the hash of the NCName
        :return: Hash value of the NCName
        :rtype: int
        """
        return hash(self.__value)

    def _as_dict(self) -> dict[str, str]:
        """
        Internal method used to convert the NCName to a JSON dictionary (@serializer decorator)
        :return: dict
        """
        return {'value': self.__value}

    @property
    def toRdf(self) -> str:
        """
        Get the RDF representation of the NCName
        :return: RDF representation of the NCName
        :rtype: str
        """
        return f'"{self.__value}"^^xsd:NCName'

    @property
    def value(self) -> str:
        """
        Get the value of the NCName
        :return: String representation of the NCName
        :rtype: str
        """
        return self.__value

