"""
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
from enum import Enum, unique
from typing import Any, Self, Optional
from pystrict import strict

from omaslib.src.helpers.omaserror import OmasValueError
from omaslib.src.helpers.xsd_datatypes import XsdValidator, XsdDatatypes


#from .xsd_datatypes import XsdDatatypes, XsdValidator
#from .omaserror import OmasValueError


@strict
class NCName:
    """
    Implements a NCName according to the XML datatyping).

    NCName is according to the XML datatype a "unqualified name". This class implements the
    following operations/methods:
    * *Constructor*: NCName(<string>), NCName(<NCName>)
    * " *+*: <NCName> + <string>
    * " *+=*: <NCName> += <string>
    * *repr()*: Get the representation of the NCName
    * *str()*: Get the string representation of the NCName
    * *==*: Compare a NCName to another NCName or string for equality
    * *!=*: Compare a NCName to another NCName or string for inequality
    * *hash()*: Get the hash of the NCName
    * *prefix()*: Get the prefix of the NCName
    * *fragment()*: Get the suffix of the NCName
    """
    _value: str

    def __init__(self, value: Self | str):
        """
        Initialize the NCName
        :param value: Either a string conforming to the QName syntax or a NCName
        """
        if isinstance(value, NCName):
            self._value = str(value)
        else:
            if not XsdValidator.validate(XsdDatatypes.NCName, value):
                raise OmasValueError(f'Invalid string "{value}" for NCName')
            self._value = value

    def __add__(self, other: Self | str) -> Self:
        """
        Append a string (which must conform to the NCName restriction) to the NCName
        :param other: string or NCName to append
        :return: A *new* NCName with string appended
        """
        if isinstance(other, str):
            other = NCName(other)  # convert to NCName. Will raise OmasValueError if string does not conform to NCName form
        if isinstance(other, NCName):
            return NCName(self._value + str(other))
        else:
            raise OmasValueError("Can only add a string or a NCName to a NCName")

    def __iadd__(self, other: Self | str) -> Self:
        """
        Append a string to the NCName
        :param other: string to append to the NCName
        :return:
        """
        if isinstance(other, str):
            other = NCName(other)  # convert to NCName. Will raise OmasValueError if string does not conform to NCName form
        if isinstance(other, NCName):
            self._value += str(other)
            return self
        else:
            raise OmasValueError("Can only add a string to NCName")

    def __repr__(self) -> str:
        """
        Return the representation string
        :return: Python representation of the instance
        """
        return f"NCName({self._value})"

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
        return self._value == str(other)

    def __ne__(self, other: Any) -> bool:
        """
        Test for non-equality
        :param other: The other NCName/str to compare
        :return: True of False
        """
        return self._value != str(other)

    def __hash__(self) -> int:
        """
        Return the hash of the NCName
        :return: hash of the NCName
        """
        return self._value.__hash__()


@strict
class QName:
    """
    Implements a XSD qualified name (xs:QName)

    A QName consists of a prefix (itelf a NCName) and a fragment (also itself a NCName) seperatet
    by a colon (":").
    The following methods are implemented:
    * *Constructor*: Construct a QName from a QName, string (with a ":") or a prefix/fragment pair
    * *len()*: Return the length of the QName, that is the number of characters of the string representation
    * *repr()*: Return the Python representation of the QName
    * *str()*: Return the string representation of the QName
    * *==*: Test for equality
    * *!=*: Test for inequality
    * *hash()*: Return the hash of the QName
    * *prefix*: Property for the prefix of the QName
    * *fragment*: Property for the fragment of the QName
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
                    raise OmasValueError(f'Invalid string "{value}" for QName')
                try:
                    prefix = NCName(prefix)
                    fragment = NCName(fragment)
                except OmasValueError as err:
                    raise OmasValueError(f'Invalid string "{value}" for QName. Error: {err}')
                self._value = f'{prefix}:{fragment}'
            else:
                raise OmasValueError(f'Invalid value for QName "{value}"')
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
        return f'QName("{self._value}")'

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
        return self._value == str(other)

    def __ne__(self, other: Any):
        """
        Test for inequality of two QNames
        :param other: Another QName/str to compare with
        :return: True of False
        """
        return self._value != str(other)

    def __hash__(self):
        """
        Return the hast value of the QName
        :return: Hash of the QName
        """
        return self._value.__hash__()

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
class BNode:
    """
    Represents a blank node in the triple store. The class has the following methods:
    * *Constructor*: Initialize a blank node
    * *str()*: Return the name of the blank node
    * *repr()*: Return the Python representation of the blank node
    * *==*: Test for equality of 2 blank nodes
    * *!=*: Test for inequality of 2 blank nodes
    * *hash()*: Return the hash of the blank node
    * *value()*: Return the value of the blank node (same as str())
    """
    __value: str

    def __init__(self, value: str) -> None:
        """
        Construct a blank node from its name
        :param value:
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
        return f'BNode("{self.__value}")'

    def __eq__(self, other: Any) -> bool:
        """
        Test for equality of two BNodes
        :param other: Another BNode to compare with
        :return: True of False
        """
        return self.__value == str(other)

    def __ne__(self, other: Any) -> bool:
        """
        Test for inequality of two BNodes
        :param other: Any BNode to compare with
        :return: True or False
        """
        return self.__value != str(other)

    def __hash__(self):
        """
        Return the hash of the BNode
        :return: Hash of the BNode
        """
        return hash(self.__value)

    @property
    def value(self) -> str:
        """
        Return the BNode's value (equivalent to str())
        :return: String representation of the BNode
        """
        return self.__value


@strict
class AnyIRI:
    """
    Represents a generic IRI

    This class is used to represent a generic IRI. This class has the following methods:
    * *Constructor()*: Constructor which initializes a AnyIRI instance
    * *+*: Append a string or NCName to an AnyIRI instance
    * *+=*: Append a string or NCName to an AnyIRI instance
    * *repr()*: Returns the Python representation of the AnyIRI instance
    * *str()*: Returns the string representation of the AnyIRI instance
    * *==*: Tests for equality of 2 AnyIRI instances
    * *!=*: Tests for inequality of 2 AnyIRI instances
    * *hash()*: Returns the hash of the AnyIRI instance
    * *len()*: Returns the number of characters in the string representation of the AnyIRI
    * *append_allowed()*: Returns True if the AnyIRI instance allows appending a fragment, that is if it terminates
      with a "#" or "/" character
    """
    _value: str
    _append_allowed: bool

    def __init__(self, value: Self | str):
        """
        Constructor for the AnyIRI class. It performs a consistency check if the given string is an IRI
        :param value: A string or another AnyIRI instance
        """
        if isinstance(value, AnyIRI):
            self._value = str(value)
        else:
            if not XsdValidator.validate(XsdDatatypes.anyURI, value):
                raise OmasValueError(f'Invalid string "{value}" for anyIRI')
            self._value = value
        self._append_allowed = self._value[-1] == '/' or self._value[-1] == '#'

    def __add__(self, other: str | NCName) -> Self:
        """
        Add a string/NCName to a AnyIRI
        :param other: A string/NCName to be appended to the AnyIRI
        :return: A new AnyIRI
        """
        if isinstance(other, str):
            other = NCName(other)
            return AnyIRI(self._value + str(other))
        if isinstance(other, NCName):
            return AnyIRI(self._value + str(other))
        else:
            return OmasValueError(f'Cannot add "{other}" to AnyIRI')

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
            raise OmasValueError(f'Cannot add "{other}" to AnyIRI')
        return self

    def __repr__(self) -> str:
        """
        Returns the Python representation of the AnyIRI
        :return: Python representation of the AnyIRI
        """
        return f"AnyURI({self._value})"

    def __str__(self) -> str:
        """
        Returns the string representation of the AnyIRI
        :return: String representation of the AnyIRI
        """
        return self._value

    def __eq__(self, other: Any) -> bool:
        """
        Test for equality of two AnyIRIs
        :param other: A string/AnyIRI to be compared
        :return: True or False
        """
        return self._value == str(other)

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

    @property
    def append_allowed(self) -> bool:
        """
        Property which is "True" if the AnyURI is ending with "#" or "/"
        :return: True of False
        """
        return self._append_allowed


class NamespaceIRI(AnyIRI):
    """
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
            raise OmasValueError("NamespaceIRI must end with '/' or '#'!")


@unique
class Action(Enum):
    """
    An Enumeration of the Actions that are supported on PropertyClass and ResourceClass attributes/restrictions
    """
    CREATE = 'create'  # a new value has been added
    MODIFY = 'modify'  # a complex value (LangString, PropertyRestriction) has been modified
    REPLACE = 'replace'  # an existing value has been replaced by a new value
    DELETE = 'delete'  # an existing value has been deleted

if __name__ == "__main__":
    print(NCName("orcid") + "0000-0003-1681-4036")
