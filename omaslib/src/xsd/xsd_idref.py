from pystrict import strict

from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd_ncname import Xsd_NCName


@strict
@serializer
class Xsd_IDREF(Xsd_NCName):
    """
    Implements the XML Schema [xsd:IDREF](https://www.w3.org/TR/xmlschema11-2/#IDREF) datatype.
    Inherits from Xsd_NCName.
    """

    def __repr__(self):
        """
        Constrcutor string representation
        :return:
        """
        return f'Xsd_IDREF("{str(self)}")'

    @property
    def toRdf(self) -> str:
        """
        RDF representation of Xsd_IDREF
        :return:
        """
        return f'"{str(self)}"^^xsd:IDREF'
