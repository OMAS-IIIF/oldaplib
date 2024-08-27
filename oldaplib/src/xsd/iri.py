import uuid
from enum import unique, Enum
from typing import Self

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


@unique
class IriRep(Enum):
    """
    Enum to indicate form of Iri
    """
    FULL = 'full'
    QNAME = 'qname'


@serializer
class Iri(Xsd):
    """
    Implements the Iri class. In the context of OLDAP, an Iri may have two representations:

    - _IriRep.FULL_: It's a fully qualified Iri, such as ```http://example.org/data/myobj```
    - _IriRep.QNAME: The Iri is composed of a prefix and a fragment, e.g. ```myproj:myobj```

    If an Iri instance is created with a None value or without Iri, a unique URN is being
    created and used as full qualified Iri.
    The validation is relevant and may take considerable amounts of CPU cycles.

    The following methods are implemented:

    - Constructor method `__init__`
    - Constructor method `fromPrefixFragment(...)`
    - Comparison methods `==`, `!=`
    - hash function `__hash__`
    - test properties `is_qname` and `is_fulliri`
    - Conversion to Xsd_QName: `as_qname`
    - Access to prefix and fragment: properties `prefix` and `fragment`
    - Serializer methods `str(XXX)`, `repr(XXX)`,
    - RDF property `toRdf`
    - JSON serialization helper `toDict()`
    """

    __value: str
    __rep: IriRep

    def __init__(self, value: Self | Xsd_QName | Xsd_anyURI | str | None = None, validate: bool = True):
        """
        Constructor for the Iri class. If no parameter is supplied, the Iri class is initialized with
        a generated random Iri from the urn-namespace.
        :param value: an Iri value. If this parameter is omitted or None, a URN is being generated
        :type value: IriRep | Xsd_anyURI | str | None
        :param validate: whether to validate the Iri value. The validation may use considerable amounts of CPU cycles.
        :type validate: bool
        :raises OldapErrorValue: Invalid IRI string
        """
        if value is None:
            self.__value = uuid.uuid4().urn
            self.__rep = IriRep.FULL
            return
        if isinstance(value, Iri):
            self.__value = value.__value
            self.__rep = value.__rep
            return
        if isinstance(value, Xsd_QName):
            self.__value = str(value)
            self.__rep = IriRep.QNAME
            return
        if isinstance(value, Xsd_anyURI):
            self.__value = str(value)
            self.__rep = IriRep.FULL
            return
        if isinstance(value, str):
            try:
                tmp = Xsd_QName(value, validate=validate)
                self.__value = str(value)
                self.__rep = IriRep.QNAME
                return
            except:
                pass
            try:
                tmp = Xsd_anyURI(value, validate=validate)
                self.__value = str(value)
                self.__rep = IriRep.FULL
                return
            except:
                pass
            raise OldapErrorValue(f'Invalid string for IRI: "{value}"')
        else:
            raise OldapErrorValue(f'Invalid value for IRI: "{value}"')

    @classmethod
    def fromPrefixFragment(cls, prefix: Xsd_NCName | str, fragment: Xsd_NCName | str, validate: bool = True) -> Self:
        """
        Create an Iri instance from a prefix and a fragment.
        :param prefix: A NCName or NCName conforming string
        :type prefix: Xsd_NCName | str
        :param fragment: A NCName or NCName conforming string
        :type fragment: Xsd_NCName | str
        :param validate: weather to validate the prefix and fragment and the resulting Iri instance
        :type validate: bool
        :return: Iri instance
        :rtype: Iri
        :raises OldapErrorValue: Invalid IRI string
        """
        prefix = Xsd_NCName(prefix, validate=validate)
        fragment = Xsd_NCName(fragment, validate=validate)
        value = Xsd_QName(prefix, fragment, validate)
        return cls(value)

    def __str__(self) -> str:
        """
        String representation of the Iri
        :return: Iri string
        """
        return self.__value

    def __repr__(self) -> str:
        """
        String representation of the Iri as constructor string
        :return:
        """
        return f'Iri("{self.__value}")'

    def __eq__(self, other: Self | Xsd_QName | Xsd_anyURI | str) -> bool:
        """
        Compare for equality
        :param other: Other value to compare with
        :type other: Self | Xsd_QName | Xsd_anyURI | str
        :return: True if equal otherwise False
        :rtype: bool
        """
        if isinstance(other, Iri):
            return self.__value == other.__value
        elif isinstance(other, Xsd_QName):
            return self.__value == str(other)
        elif isinstance(other, Xsd_anyURI):
            return self.__value == str(other)
        else:
            return self.__value == str(other)

    def __ne__(self, other: Self | Xsd_QName | Xsd_anyURI | str) -> bool:
        """
        Compare for equality
        :param other: Other value to compare with
        :type other: Self | Xsd_QName | Xsd_anyURI | str
        :return: True if equal otherwise False
        :rtype: bool
        """
        if isinstance(other, Iri):
            return self.__value != other.__value
        elif isinstance(other, Xsd_QName):
            return self.__value != str(other)
        elif isinstance(other, Xsd_anyURI):
            return self.__value != str(other)
        else:
            return self.__value != str(other)


    def __hash__(self) -> int:
        """
        Return the hash of the Iri
        :return: Return the hash of the Iri
        :rtype: int
        """
        return hash(self.__value)

    @property
    def toRdf(self) -> str:
        """
        Return the Iri as a RDF string
        :return: The Iri as a RDF string
        :rtype: str
        """
        if self.__rep == IriRep.FULL:
            return f'<{self.__value}>'
        else:
            return self.__value

    def _as_dict(self) -> dict[str, str]:
        """
        Used internally for JSON serialization using @serialisation decorator
        :return: Dictionary representation of the Iri
        :rtype: dict[str, str]
        """
        return {'value': self.__value}

    @property
    def is_qname(self) -> bool:
        """
        Checks if the Iri is an Iri QName
        :return: True if the Iri is an Iri QName, False otherwise
        :rtype: bool
        """
        return self.__rep == IriRep.QNAME

    @property
    def as_qname(self) -> Xsd_QName | None:
        """
        Return the Iri as a QName instance
        :return: QName instance, or None if the Iri is represented as QName
        :rtype: Xsd_QName | None
        """
        if self.__rep == IriRep.QNAME:
            return Xsd_QName(self.__value, validate=False)
        else:
            return None

    @property
    def is_fulliri(self) -> bool:
        """
        Checks if the Iri is a full qualified Iri
        :return: True if the Iri is a full qualified Iri, False otherwise
        :rtype: bool
        """
        return self.__rep == IriRep.FULL

    @property
    def prefix(self) -> str:
        """
        Access the prefix of the QName as property
        :return: Prefix as string, or None if the Iri is not represented as QName
        :rtype: str | None
        """
        if self.__rep == IriRep.FULL:
            return None
        parts = self.__value.split(':')
        return parts[0]

    @property
    def fragment(self) -> str | None:
        """
        Access the fragment as fragment of the QName as property
        :return: Fragment as string, or None if the Iri is not represented as QName
        :rtype: str | None
        """
        if self.__rep == IriRep.FULL:
            return None
        parts = self.__value.split(':')
        return parts[1]


if __name__ == '__main__':
    #iri = Iri("oldap:HyperHamlet\".}\nSELECT * WHERE{?s ?p ?s})#")
    iri = Iri(None)
    print(iri)
