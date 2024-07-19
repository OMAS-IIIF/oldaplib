from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


class IriOrNCName:

    def __init__(self, value: Iri | Xsd_NCName | str):
        self.__iri: Iri | None = None
        self.__ncname: Xsd_NCName | None = None
        if isinstance(value, Iri):
            self.__iri = value
            self.__ncname = None
        elif isinstance(value, Xsd_NCName):
            self.__ncname = Xsd_NCName(value)
            self.__iri = None
        else:
            if ':' in str(value):  # must be IRI or QName
                self.__iri = Iri(value)
                self.__ncname = None
            else:
                self.__ncname = Xsd_NCName(value)
                self.__iri = None

    def value(self) -> tuple[Xsd_NCName| None, Iri | None]:
        return self.__ncname, self.__iri

    def __str__(self):
        if self.__iri is not None:
            return str(self.__iri)
        elif self.__ncname is not None:
            return str(self.__ncname)
        else:
            return "???"
