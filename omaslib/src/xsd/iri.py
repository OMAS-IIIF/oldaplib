import uuid
from enum import unique, Enum
from typing import Self

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_qname import Xsd_QName


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
    Implements the Iri class
    """

    __value: str
    __rep: IriRep

    def __init__(self, value: Self | Xsd_QName | Xsd_anyURI | str | None = None):
        """
        Constructor for the Iri class. If no parameter is supplied, the Iri class is initialized with
        a generated random Iri from the urn-namespace.
        :param value: an Iri value. If this parameter is omitted or None, a URN is being generated
        :type value: IriRep | Xsd_anyURI | str | None
        :raises OmasErrorValue: Invalid IRI string
        """
        if value is None:
            self.__value = uuid.uuid4().urn
            self.__rep = IriRep.FULL
        elif isinstance(value, Iri):
            self.__value = value.__value
            self.__rep = value.__rep
        elif isinstance(value, Xsd_QName):
            self.__value = str(value)
            self.__rep = IriRep.QNAME
            return
        elif isinstance(value, Xsd_anyURI):
            self.__value = str(value)
            self.__rep = IriRep.FULL
            return
        elif isinstance(value, str):
            try:
                tmp = Xsd_QName(value)
                self.__value = str(value)
                self.__rep = IriRep.QNAME
                return
            except:
                pass
            try:
                tmp = Xsd_anyURI(value)
                self.__value = str(value)
                self.__rep = IriRep.FULL
                return
            except:
                pass
            raise OmasErrorValue(f'Invalid string for IRI: "{value}"')
        else:
            raise OmasErrorValue(f'Invalid value for IRI: "{value}"')
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
        if isinstance(other, Iri):
            return self.__value == other.__value
        elif isinstance(other, Xsd_QName):
            return self.__value == str(other)
        elif isinstance(other, Xsd_anyURI):
            return self.__value == str(other)
        else:
            return self.__value == str(other)

    def __hash__(self) -> int:
        return hash(self.__value)

    @property
    def toRdf(self) -> str:
        if self.__rep == IriRep.FULL:
            return f'<{self.__value}>'
        else:
            return self.__value

    def _as_dict(self) -> dict[str, str]:
        return {'value': self.__value}

    @property
    def is_qname(self) -> bool:
        """
        Checks if the Iri is an Iri QName
        :return:
        """
        return self.__rep == IriRep.QNAME

    @property
    def is_fulliri(self) -> bool:
        """
        Checks if the Iri is a full qualified Iri
        :return:
        """
        return self.__rep == IriRep.FULL

    @property
    def prefix(self) -> str:
        """
        Access the prefix of the QName as property
        :return: Prefix as string
        """
        if self.__rep == IriRep.FULL:
            return None
        parts = self.__value.split(':')
        return parts[0]

    @property
    def fragment(self) -> str | None:
        """
        Access the fragment as fragment of the QName as property
        :return: Fragment as string
        """
        if self.__rep == IriRep.FULL:
            return None
        parts = self.__value.split(':')
        return parts[1]



