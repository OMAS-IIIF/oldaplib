from pystrict import strict

from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd_ncname import Xsd_NCName


@strict
@serializer
class Xsd_ID(Xsd_NCName):
    """
    Implements the XML Schema [xsd:ID](https://www.w3.org/TR/xmlschema11-2/#ID) datatyoe. Inherits
    """

    def __repr__(self):
        """
        Constructor tring representation of Xsd_ID
        :return:
        """
        return f'Xsd_ID("{str(self)}")'

    @property
    def toRdf(self) -> str:
        """
        RDF representation of Xsd_ID
        :return:
        """
        return f'"{str(self)}"^^xsd:ID'
