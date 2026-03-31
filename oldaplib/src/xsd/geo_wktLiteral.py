from typing import Self

from shapely import wkt
from shapely.lib import ShapelyError

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd


@serializer
class Geo_wktLiteral(Xsd):
    __value: str | None

    def __init__(self, value: Self | str | None = None, validate: bool = False):
        if not value:
            self.__value = None
        elif isinstance(value, Geo_wktLiteral):
            self.__value = value.__value
        else:
            self.__value = str(value)
        if self.__value and validate:
            try:
                geom = wkt.loads(self.__value)
            except ShapelyError as err:
                raise OldapErrorValue(str(err))
            if not geom.is_valid:
                raise OldapErrorValue(f'WKT "{self.__value}" is not a valid geometry.')

    def __str__(self) -> str | None:
        return self.__value

    def __repr__(self) -> str:
        return f'Geo_wktLiteral("{self.__value}")'

    def __hash__(self) -> int:
        return hash(self.__value)

    def __eq__(self, other: Self | str | None) -> bool:
        if isinstance(other, Geo_wktLiteral):
            return self.__value == other.__value
        elif isinstance(other, str):
            return self.__value == other
        else:
            return False

    @classmethod
    def fromRdf(cls, value: str) -> Self:
        return cls(value, validate=False)

    @property
    def toRdf(self):
        """
        RDF representation of the Xsd_string instance
        :return: RDF representation of the Xsd_string instance
        :rtype: str
        """
        if self.__value is None:
            raise OldapErrorValue(f'Cannot convert empty geo_wktLiteral to RDF string.')
        return f'"{self.__value}"^^geo:wktLiteral'


    def _as_dict(self) -> dict[str, str]:
        return {'value': self.__value}

    @property
    def value(self) -> str:
        return self.__value