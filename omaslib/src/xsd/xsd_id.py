from pystrict import strict

from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd_ncname import Xsd_NCName


@strict
@serializer
class Xsd_ID(Xsd_NCName):

    def __repr__(self):
        return f'Xsd_ID("{str(self)}")'

    @property
    def toRdf(self) -> str:
        return f'"{str(self)}"^^xsd:ID'
