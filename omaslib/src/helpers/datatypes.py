"""
# Datatypes

This module implements common data classes that are used throughout the OMASLIB library

* _NCName_: An XML NCName
* _QName_: An XML QName
* _BNode_: A blank node a returned by the triple store
* _AnyIRI_: A generic IRI
* _NamespaceIRI_: A namespace IRI, that is an IRI that ends with either "#" or "/"
* _Action_: The action that can be performed on resources and properties

These classes perform consistency checks to guarantee that the data is consistent with the syntax rules
for the given XML datatypes. They should be used instead of simple string representations wherever possible
"""
import json
import re
from enum import Enum, unique
from typing import Any, Self, Optional, Dict, Tuple
from urllib.parse import urlparse

from pystrict import strict
from validators import url

from omaslib.src.helpers.oldap_string_literal import OldapStringLiteral
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.enums.xsd_datatypes import XsdValidator, XsdDatatypes


class Xsd:
    pass


@strict
@serializer
class Xsd_gYearMonth(Xsd):
    __year: int
    __month: int
    __tz: Tuple[int, int] | None
    __zulu: bool

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_gYearMonth):
            self.__year = value.__year
            self.__month = value.__month
            self.__tz = value.__tz
        else:
            if not XsdValidator.validate(XsdDatatypes.gYearMonth, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gYearMonth')
            # or: re.match("[+-]?[0-9]{4}-[0-9]{2}(([+-][0-9]{2}:[0-9]{2})|Z)?", string)
            res = re.split("([+-]?[0-9]{4})-([0-9]{2})((([+-][0-9]{2}):([0-9]{2}))|(Z))?", value)
            if len(res) != 9:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gYearMonth.')
            self.__year = int(res[1])
            self.__month = int(res[2])
            if res[3] == 'Z':
                self.__tz = (0, 0)
                self.__zulu = True
            elif res[3] is not None:
                self.__tz = (int(res[5]), int(res[6]))
                self.__zulu = False
            else:
                self.__tz = None
        if self.__month < 1 or self.__month > 12:
            raise OmasErrorValue(f'Invalid string "{value}" for xsd:gYearMonth.')

    def __str__(self):
        ff = '05' if self.__year < 0 else '04'
        s = f'{self.__year:{ff}}-{self.__month:02}'
        if self.__tz is not None:
            if self.__zulu:
                s += 'Z'
            else:
                s += f'{self.__tz[0]:0=+3}:{self.__tz[1]:02}'
        return s

    def __repr__(self):
        return f'"{str(self)}"^^gYearMonth'

    def __hash__(self):
        return hash(str(self))

    def _as_dict(self) -> Dict[str, str]:
        return {'value': str(self)}

    def __eq__(self, other: Self | str):
        if not isinstance(other, Xsd_gYearMonth):
            other = Xsd_gYearMonth(other)
        if self.__year != other.__year:
            return False
        if self.__month != other.__month:
            return False
        if self.__tz != other.__tz:
            return False
        return True


@strict
@serializer
class Xsd_gYear(Xsd):
    __year: int
    __tz: Tuple[int, int] | None
    __zulu: bool

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_gYear):
            self.__year = value.__year
            self.__tz = value.__tz
        else:
            if not XsdValidator.validate(XsdDatatypes.gYear, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gYear.')
            # or: re.match("[+-]?[0-9]{4}-[0-9]{2}(([+-][0-9]{2}:[0-9]{2})|Z)?", string)
            res = re.split("([+-]?[0-9]{4})((([+-][0-9]{2}):([0-9]{2}))|(Z))?", value)
            if len(res) != 8:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gYear.')
            self.__year = int(res[1])
            if res[2] == 'Z':
                self.__tz = (0, 0)
                self.__zulu = True
            elif res[2] is not None:
                self.__tz = (int(res[4]), int(res[5]))
                self.__zulu = False
            else:
                self.__tz = None

    def __str__(self):
        ff = '05' if self.__year < 0 else '04'
        s = f'{self.__year:{ff}}'
        if self.__tz is not None:
            if self.__zulu:
                s += 'Z'
            else:
                s += f'{self.__tz[0]:0=+3}:{self.__tz[1]:02}'
        return s

    def __repr__(self):
        return f'"{str(self)}"^^xsd:gYear'

    def __hash__(self):
        return hash(str(self))

    def _as_dict(self) -> Dict[str, str]:
        return {'value': str(self)}

    def __eq__(self, other: Self | str):
        if not isinstance(other, Xsd_gYear):
            other = Xsd_gYear(other)
        if self.__year != other.__year:
            return False
        if self.__tz != other.__tz:
            return False
        return True


@strict
@serializer
class Xsd_gMonthDay(Xsd):
    __month: int
    __day: int
    __tz: Tuple[int, int] | None
    __zulu: bool

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_gMonthDay):
            self.__month = value.__month
            self.__day = value.__day
            self.__tz = value.__tz
        else:
            if not XsdValidator.validate(XsdDatatypes.gMonthDay, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gMonthDay')
            res = re.split("--([0-9]{2})-([0-9]{2})((([+-][0-9]{2}):([0-9]{2}))|(Z))?", value)
            if len(res) != 9:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gMonthDay.')
            self.__month = int(res[1])
            self.__day = int(res[2])
            if res[3] == 'Z':
                self.__tz = (0, 0)
                self.__zulu = True
            elif res[3] is not None:
                self.__tz = (int(res[5]), int(res[6]))
                self.__zulu = False
            else:
                self.__tz = None
        if self.__month < 1 or self.__month > 12 or self.__day < 1 or self.__day > 31:
            raise OmasErrorValue(f'Invalid string "{value}" for xsd:gMonthDay.')

    def __str__(self):
        s = f'--{self.__month:02}-{self.__day:02}'
        if self.__tz is not None:
            if self.__zulu:
                s += 'Z'
            else:
                s += f'{self.__tz[0]:0=+3}:{self.__tz[1]:02}'
        return s

    def __repr__(self):
        return f'"{str(self)}"^^xsd:gMonthDay'

    def __hash__(self):
        return hash(str(self))

    def _as_dict(self) -> Dict[str, str]:
        return {'value': str(self)}

    def __eq__(self, other: Self | str):
        if not isinstance(other, Xsd_gMonthDay):
            other = Xsd_gMonthDay(other)
        if self.__month != other.__month:
            return False
        if self.__day != other.__day:
            return False
        if self.__tz != other.__tz:
            return False
        return True

@strict
@serializer
class Xsd_gDay(Xsd):
    __day: int
    __tz: Tuple[int, int] | None
    __zulu: bool

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_gDay):
            self.__day = value.__day
            self.__tz = value.__tz
        else:
            if not XsdValidator.validate(XsdDatatypes.gDay, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gDay')
            res = re.split("---([0-9]{2})((([+-][0-9]{2}):([0-9]{2}))|(Z))?", value)
            if len(res) != 8:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gDay.')
            self.__day = int(res[1])
            if res[2] == 'Z':
                self.__tz = (0, 0)
                self.__zulu = True
            elif res[2] is not None:
                self.__tz = (int(res[4]), int(res[5]))
                self.__zulu = False
            else:
                self.__tz = None
        if self.__day < 1 or self.__day > 31:
            raise OmasErrorValue(f'Invalid string "{value}" for xsd:gDay.')

    def __str__(self):
        s = f'---{self.__day:02}'
        if self.__tz is not None:
            if self.__zulu:
                s += 'Z'
            else:
                s += f'{self.__tz[0]:0=+3}:{self.__tz[1]:02}'
        return s

    def __repr__(self):
        return f'"{str(self)}"^^xsd:gDay'

    def __hash__(self):
        return hash(str(self))

    def _as_dict(self) -> Dict[str, str]:
        return {'value': str(self)}

    def __eq__(self, other: Self | str):
        if not isinstance(other, Xsd_gDay):
            other = Xsd_gDay(other)
        if self.__day != other.__day:
            return False
        if self.__tz != other.__tz:
            return False
        return True


@strict
@serializer
class Xsd_gMonth(Xsd):
    __month: int
    __tz: Tuple[int, int] | None
    __zulu: bool

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_gMonth):
            self.__month = value.__month
            self.__tz = value.__tz
        else:
            if not XsdValidator.validate(XsdDatatypes.gMonth, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gMonth.')
            res = re.split("--([0-9]{2})((([+-][0-9]{2}):([0-9]{2}))|(Z))?", value)
            if len(res) != 8:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:gMonth.')
            self.__month = int(res[1])
            if res[2] == 'Z':
                self.__tz = (0, 0)
                self.__zulu = True
            elif res[2] is not None:
                self.__tz = (int(res[4]), int(res[5]))
                self.__zulu = False
            else:
                self.__tz = None
        if self.__month < 1 or self.__month > 12:
            raise OmasErrorValue(f'Invalid string "{value}" for xsd:gMonth.')

    def __str__(self):
        s = f'--{self.__month:02}'
        if self.__tz is not None:
            if self.__zulu:
                s += 'Z'
            else:
                s += f'{self.__tz[0]:0=+3}:{self.__tz[1]:02}'
        return s

    def __repr__(self):
        return f'"{str(self)}"^^xsd:gMonth'

    def __hash__(self):
        return hash(str(self))

    def _as_dict(self) -> Dict[str, str]:
        return {'value': str(self)}

    def __eq__(self, other: Self | str):
        if not isinstance(other, Xsd_gMonth):
            other = Xsd_gMonth(other)
        if self.__month != other.__month:
            return False
        if self.__tz != other.__tz:
            return False
        return True


@strict
@serializer
class Xsd_hexBinary(Xsd):
    __value: str

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_hexBinary):
            self.__value = value.__value
        else:
            if not XsdValidator.validate(XsdDatatypes.hexBinary, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:hexBinary.')
            self.__value = value

    def __str__(self):
        return self.__value

    def __repr__(self):
        return f'"{str(self)}"^^xsd:hexBinary'

    def __hash__(self):
        return hash(self.__value)

    def _as_dict(self) -> Dict[str, str]:
        return {'value': self.__value}

    def __eq__(self, other):
        return self.__value == other.__value


@strict
@serializer
class Xsd_base64Binary(Xsd):
    __value: str

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_base64Binary):
            self.__value = value.__value
        else:
            if not XsdValidator.validate(XsdDatatypes.base64Binary, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:base64Binary.')
            self.__value = value

    def __str__(self):
        return self.__value

    def __repr__(self):
        return f'"{str(self)}"^^xsd:base64Binary'

    def __hash__(self):
        return hash(self.__value)

    def _as_dict(self) -> Dict[str, str]:
        return {'value': self.__value}

    def __eq__(self, other):
        return self.__value == other.__value

@strict
@serializer
class Xsd_anyURI(Xsd):
    __value: str

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_anyURI):
            self.__value = value.__value
        else:
            if not XsdValidator.validate(XsdDatatypes.anyURI, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:anyURI.')

            if not url(value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:anyURI.')
            self.__value = value

    def __str__(self):
        return self.__value

    def __repr__(self):
        return f'"{str(self)}"^^xsd:anyURI'

    def __hash__(self):
        return hash(self.__value)

    def _as_dict(self) -> Dict[str, str]:
        return {'value': self.__value}

    def __eq__(self, other):
        return self.__value == other.__value


@strict
@serializer
class Xsd_normalizedString(Xsd):
    __value: str

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_normalizedString):
            self.__value = value.__value
        else:
            if not XsdValidator.validate(XsdDatatypes.normalizedString, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:normalizedString.')
            if re.match("^[^\r\n\t]*$", value) is None:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:normalizedString.')
            self.__value = value

    @classmethod
    def fromRdf(cls, value: str) -> Self:
        value = OldapStringLiteral.unescaping(value)
        return cls(value)

    def __str__(self):
        return self.__value

    def __repr__(self):
        return f'"{OldapStringLiteral.escaping(str(self))}"^^xsd:normalizedString'

    def __hash__(self):
        return hash(self.__value)

    def _as_dict(self) -> Dict[str, str]:
        return {'value': self.__value}

    def __eq__(self, other: Self | str):
        if not isinstance(other, Xsd_normalizedString):
            other = Xsd_normalizedString(other)
        return self.__value == other.__value


@strict
@serializer
class Xsd_token(Xsd):
    __value: str

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_token):
            self.__value = value.__value
        else:
            if not XsdValidator.validate(XsdDatatypes.token, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:token.')
            if not re.match("^[^\s]+(\s[^\s]+)*$", value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:token.')
            if re.match(".*[\n\r\t].*", value) is not None:
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:token.')
            self.__value = value

    @classmethod
    def fromRdf(cls, value: str) -> Self:
        value = OldapStringLiteral.unescaping(value)
        return cls(value)

    def __str__(self):
        return self.__value

    def __repr__(self):
        return f'"{OldapStringLiteral.escaping(str(self))}"^^xsd:token'

    def __hash__(self):
        return hash(self.__value)

    def _as_dict(self) -> Dict[str, str]:
        return {'value': self.__value}

    def __eq__(self, other: Self | str):
        if not isinstance(other, Xsd_token):
            other = Xsd_token(other)
        return self.__value == other.__value


@strict
@serializer
class Xsd_language(Xsd):
    __value: str

    def __init__(self, value: Self | str):
        if isinstance(value, Xsd_token):
            self.__value = value.__value
        else:
            if not XsdValidator.validate(XsdDatatypes.language, value):
                raise OmasErrorValue(f'Invalid string "{value}" for xsd:language.')
            # if not re.match("^[^\s]+(\s[^\s]+)*$", value):
            #     raise OmasErrorValue(f'Invalid string "{value}" for xsd:language.')
            # if re.match(".*[\n\r\t].*", value) is not None:
            #     raise OmasErrorValue(f'Invalid string "{value}" for xsd:language.')
            self.__value = value

    @classmethod
    def fromRdf(cls, value: str) -> Self:
        return cls(value)

    def __str__(self):
        return self.__value

    def __repr__(self):
        return f'"{str(self)}"^^xsd:language'

    def __hash__(self):
        return hash(self.__value)

    def _as_dict(self) -> Dict[str, str]:
        return {'value': self.__value}

    def __eq__(self, other: Self | str):
        if not isinstance(other, Xsd_language):
            other = Xsd_language(other)
        return self.__value == other.__value


@strict
@serializer
class NCName:
    """
    # NCName

    Implements a NCName according to the XML datatyping.

    NCName is according to the XML datatype an "unqualified name". See the
    [W3C documentation](https://www.w3.org/TR/xmlschema-2/#NCName).
    This class implements the following operations/methods:

    - *Constructor*: NCName(string), NCName(NCName)
    - *+*: NCName + string
    - *+=*: NCName += string
    - *repr()*: Get the representation of the NCName
    - *str()*: Get the string representation of the NCName
    - *==*: Compare a NCName to another NCName or string for equality
    - *!=*: Compare a NCName to another NCName or string for inequality
    - *hash()*: Get the hash of the NCName
    - *prefix()*: Get the prefix of the NCName
    - *fragment()*: Get the suffix of the NCName

    """
    _value: str

    def __init__(self, value: Self | str):
        """
        Initialize the NCName
        :param value: Either a string conforming to the QName syntax or a NCName
        :type value: NCName | str
        """
        if isinstance(value, NCName):
            self._value = str(value)
        else:
            if not XsdValidator.validate(XsdDatatypes.NCName, value):
                raise OmasErrorValue(f'Invalid string "{value}" for NCName')
            self._value = value

    def __add__(self, other: Self | str) -> Self:
        """
        Append a string (which must conform to the NCName restriction) to the NCName
        :param other: string or NCName to append
        :type other: NCName | str
        :return: A *new* NCName with string appended
        """
        if isinstance(other, str):
            other = NCName(
                other)  # convert to NCName. Will raise OmasValueError if string does not conform to NCName form
        if isinstance(other, NCName):
            return NCName(self._value + str(other))
        else:
            raise OmasErrorValue("Can only add a string or a NCName to a NCName")

    def __iadd__(self, other: Self | str) -> Self:
        """
        Append a string to the NCName
        :param other: string to append to the NCName
        :return: Self        """
        if isinstance(other, str):
            other = NCName(
                other)  # convert to NCName. Will raise OmasValueError if string does not conform to NCName form
        if isinstance(other, NCName):
            self._value += str(other)
            return self
        else:
            raise OmasErrorValue("Can only add a string to NCName")

    def __repr__(self) -> str:
        """
        Return the representation string
        :return: Python representation of the instance
        """
        return f'"{self._value}"^^xsd:NCName'

    def __str__(self) -> str:
        """
        Return the value as string
        :return: Value as string
        """
        return self._value

    def __eq__(self, other: Any) -> bool:
        """
        Test two NCNames for equality
        :param other: The other NCName/str to compare
        :return: True of False
        """
        if isinstance(other, str):
            return self._value == other
        return isinstance(other, NCName) and self._value == other._value

    def __ne__(self, other: Any) -> bool:
        """
        Test for non-equality
        :param other: The other NCName/str to compare
        :return: True of False
        """
        if not isinstance(other, NCName):
            return False
        return self._value != other._value

    def __hash__(self) -> int:
        """
        Return the hash of the NCName
        :return: hash of the NCName
        """
        return self._value.__hash__()

    def _as_dict(self) -> Dict[str, str]:
        return {
            'value': self._value
        }


@strict
@serializer
class QName:
    """
    # QName

    Implements a XSD qualified name (xs:QName) See [W3C documentation](https://www.w3.org/TR/xmlschema-2/#QName).

    A QName consists of a prefix (itelf a NCName) and a fragment (also itself a NCName) seperatet
    by a colon (":").
    The following methods are implemented:

    - *Constructor*: Construct a QName from a QName, string (with a ":") or a prefix/fragment pair
    - *len()*: Return the length of the QName, that is the number of characters of the string representation
    - *repr()*: Return the Python representation of the QName
    - *str()*: Return the string representation of the QName
    - *==*: Test for equality
    - *!=*: Test for inequality
    - *hash()*: Return the hash of the QName
    - *prefix*: Property for the prefix of the QName
    - *fragment*: Property for the fragment of the QName

    """
    _value: str

    def __init__(self, value: Self | str | NCName, fragment: Optional[str | NCName] = None) -> None:
        """
        Construct a QName from a QName, string (with a ":") or a prefix/fragment pair
        :param value: A Qname, string (with a ":") or a prefix as NCName or string
        :param fragment: A NCName or string (conforming to NCName the convention) for the fragment part
        """
        if fragment is None:
            if isinstance(value, QName):
                self._value = str(value)
            elif isinstance(value, str):
                try:
                    prefix, fragment = value.split(':')
                except ValueError as err:
                    raise OmasErrorValue(f'Invalid string "{value}" for QName')
                try:
                    prefix = NCName(prefix)
                    fragment = NCName(fragment)
                except OmasErrorValue as err:
                    raise OmasErrorValue(f'Invalid string "{value}" for QName. Error: {err}')
                self._value = f'{prefix}:{fragment}'
            else:
                raise OmasErrorValue(f'Invalid value for QName "{value}"')
        else:
            prefix = NCName(value)
            fragment = NCName(fragment)
            self._value = f'{prefix}:{fragment}'

    def __len__(self) -> int:
        """
        Return the number of characters in the QName
        :return: Length of the QName
        """
        return len(self._value)

    def __add__(self, other: Any) -> 'QName':
        return QName(self._value + str(other))

    def __iadd__(self, other):
        return QName(self._value + str(other))

    def __repr__(self):
        """
        Return the Python representation of the QName
        :return: Python representation of the QName
        """
        return str(self._value)

    def __str__(self):
        """
        Return the string representation of the QName
        :return: String representation of the QName
        """
        return self._value

    def __eq__(self, other: Any):
        """
        Test for equality of two QNames
        :param other: Another QName/str to compare with
        :return: True of False
        """
        if isinstance(other, str):
            return self._value == other
        return isinstance(other, QName) and self._value == other._value

    def __ne__(self, other: Any):
        """
        Test for inequality of two QNames
        :param other: Another QName/str to compare with
        :return: True of False
        """
        if not isinstance(other, QName):
            return False
        return self._value != other._value

    def __hash__(self):
        """
        Return the hast value of the QName
        :return: Hash of the QName
        """
        return self._value.__hash__()

    def _as_dict(self):
        return {
            'value': self._value
        }

    def as_rdf(self) -> str:
        return self._value

    @property
    def prefix(self) -> str:
        """
        Access the prefix of the QName as property
        :return: Prefix as string
        """
        parts = self._value.split(':')
        return parts[0]

    @property
    def fragment(self) -> str:
        """
        Access the fragment as fragment of the QName as property
        :return: Fragment as string
        """
        parts = self._value.split(':')
        return parts[1]


@strict
@serializer
class BNode:
    """
    # BNode

    Represents a blank node in the triple store. The class has the following methods:

    - *Constructor*: Initialize a blank node
    - *str()*: Return the name of the blank node
    - *repr()*: Return the Python representation of the blank node
    - *==*: Test for equality of 2 blank nodes
    - *!=*: Test for inequality of 2 blank nodes
    - *hash()*: Return the hash of the blank node
    - *value()*: Return the value of the blank node (same as str())
    """
    __value: str

    def __init__(self, value: str) -> None:
        """
        Construct a blank node from its name
        :param value: Name/id of the blank node
        :type value: str
        """
        self.__value = value

    def __str__(self) -> str:
        """
        Return the string representation of the BNode
        :return: string representation of the BNode
        """
        return self.__value

    def __repr__(self) -> str:
        """
        Return the Python representation of the BNode
        :return: Python representation of the BNode
        """
        return self.__value

    def __eq__(self, other: Any) -> bool:
        """
        Test for equality of two BNodes
        :param other: Another BNode to compare with
        :return: True of False
        """
        return isinstance(other, BNode) and self.__value == other.__value

    def __ne__(self, other: Any) -> bool:
        """
        Test for inequality of two BNodes
        :param other: Any BNode to compare with
        :type other: BNode
        :return: True or False
        """
        return self.__value != str(other)

    def __hash__(self):
        """
        Return the hash of the BNode
        :return: Hash of the BNode
        """
        return hash(self.__value)

    def _as_dict(self):
        """used for json serialization using serializer"""
        return {
            'value': self.__value
        }

    @property
    def value(self) -> str:
        """
        Return the BNode's value (equivalent to str())
        :return: String representation of the BNode
        :rtype: string
        """
        return self.__value


@strict
@serializer
class AnyIRI:
    """
    # AnyIRI

    Represents a generic IRI (corresonds to the XML datatype [AnyURI](https://www.w3.org/TR/xmlschema-2/#QName).
    This class is used to represent a generic IRI. This class has the following methods:

    - *Constructor()*: Constructor which initializes a AnyIRI instance
    - *+*: Append a string or NCName to an AnyIRI instance
    - *+=*: Append a string or NCName to an AnyIRI instance
    - *repr()*: Returns the Python representation of the AnyIRI instance
    - *str()*: Returns the string representation of the AnyIRI instance
    - *==*: Tests for equality of 2 AnyIRI instances
    - *!=*: Tests for inequality of 2 AnyIRI instances
    - *hash()*: Returns the hash of the AnyIRI instance
    - *len()*: Returns the number of characters in the string representation of the AnyIRI
    - *append_allowed()*: Returns True if the AnyIRI instance allows appending a fragment, that is if it terminates
      with a "#" or "/" character
    """
    _value: str
    _append_allowed: bool

    def __init__(self, value: Self | str):
        """
        Constructor for the AnyIRI class. It performs a consistency check if the given string is an IRI
        :param value: A string or another AnyIRI instance
        :type value: AnyIRI | str
        """
        if isinstance(value, AnyIRI):
            self._value = str(value)
        else:
            if isinstance(value, str):
                value = value.replace("<", "").replace(">", "")
            if not XsdValidator.validate(XsdDatatypes.anyURI, value):
                raise OmasErrorValue(f'Invalid string "{value}" for anyIRI')
            self._value = value
        self._append_allowed = self._value[-1] == '/' or self._value[-1] == '#'

    def __add__(self, other: str | NCName) -> Self:
        """
        Add a string/NCName to a AnyIRI
        :param other: A string/NCName to be appended to the AnyIRI
        :type other: NCName | str
        :return: A new AnyIRI
        :rtype: AnyIRI
        """
        if isinstance(other, str):
            other = NCName(other)
            return AnyIRI(self._value + str(other))
        if isinstance(other, NCName):
            return AnyIRI(self._value + str(other))
        else:
            return OmasErrorValue(f'Cannot add "{other}" to AnyIRI')

    def __iadd__(self, other: str | NCName) -> Self:
        """
        Add a string/NCName to an AnyIRI
        :param other: A string/NCName to be appended to the AnyIRI
        :return: self
        """
        if isinstance(other, str):
            other = NCName(other)
        if isinstance(other, NCName):
            self._value += str(other)
        else:
            raise OmasErrorValue(f'Cannot add "{other}" to AnyIRI')
        return self

    def __repr__(self) -> str:
        """
        Returns the Python representation of the AnyIRI
        :return: Python representation of the AnyIRI
        """
        return f'<{self._value}>'

    def __str__(self) -> str:
        """
        Returns the string representation of the AnyIRI
        :return: String representation of the AnyIRI
        """
        return f'{self._value}'

    def __eq__(self, other: Any) -> bool:
        """
        Test for equality of two AnyIRIs
        :param other: A string/AnyIRI to be compared
        :return: True or False
        """
        if isinstance(other, str):
            return self._value == other
        return isinstance(other, AnyIRI) and self._value == other._value

    def __ne__(self, other: Any) -> bool:
        """
        Test for inequality of two
        :param other: A string/AnyIRI to be compared
        :return: True or False
        """
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

    def _as_dict(self) -> Dict[str, str]:
        return {
            'value': self._value
        }

    def as_rdf(self) -> str:
        return f'<{self._value}>'

    @property
    def append_allowed(self) -> bool:
        """
        Property which is "True" if the AnyURI is ending with "#" or "/"
        :return: True of False
        """
        return self._append_allowed


@serializer
class NamespaceIRI(AnyIRI):
    """
    # NamespaceIRI

    An IRI representing a namespace. A namespace is an IRI that ends with a fragment separates, that is a "#" or "/".
    It is a subclass of AnyIRI and checks in the constructor for the termination with a "#" or "/".
    """

    def __init__(self, value: Self | str):
        """
        Constructor for the NamespaceIRI
        :param value: A string or another NamespaceIRI
        """
        super().__init__(value)
        if not self._append_allowed:
            raise OmasErrorValue("NamespaceIRI must end with '/' or '#'!")

    def _as_dict(self) -> Dict[str, str]:
        return {
            'value': self._value
        }


@unique
@serializer
class Action(Enum):
    """
    # Action

    An Enumeration of the Actions that are supported on PropertyClass and ResourceClass attributes/restrictions

    - `Action.CREATE` = 'create'
    - `Action.MODIFY` = 'modify'
    - `Action.REPLACE` = 'replace'
    - `Action.DELETE` = 'delete'
    """
    CREATE = 'create'  # a new value has been added
    MODIFY = 'modify'  # a complex value (LangString, PropertyRestriction) has been modified
    REPLACE = 'replace'  # an existing value has been replaced by a new value
    DELETE = 'delete'  # an existing value has been deleted

    def _as_dict(self) -> Dict[str, str]:
        return {__class__: self.__class__.__name__, 'value': self.value}


if __name__ == "__main__":
    # print(NCName("orcid") + "0000-0003-1681-4036")

    g1 = Xsd_gYearMonth("2022-05")
    g2 = Xsd_gYearMonth("-2022-05+03:00")

    AnyIRI('urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b')

    gaga = Action.REPLACE
    json_repr = json.dumps(gaga, default=serializer.encoder_default)
    print(json_repr)
    gugus = json.loads(json_repr, object_hook=serializer.decoder_hook)
    print(gugus)
