from pystrict import strict

from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd_ncname import Xsd_NCName


@strict
@serializer
class Xsd_IDREF(Xsd_NCName):

    def __repr__(self):
        return f'Xsd_IDREF("{str(self)}")'

    @property
    def toRdf(self) -> str:
        return f'"{str(self)}"^^xsd:IDREF'
