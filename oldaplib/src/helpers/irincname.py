from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


class IriOrNCName:

    def __init__(self, value: Iri | Xsd_QName | Xsd_NCName | str, validate: bool = False):
        self.__iri: Iri | None = None
        self.__ncname: Xsd_NCName | None = None
        self.__qname: Xsd_QName | None = None
        if isinstance(value, Iri):
            self.__iri = value
            self.__ncname = None
            self.__qname = None
        elif isinstance(value, Xsd_NCName):
            self.__ncname = Xsd_NCName(value)
            self.__iri = None
            self.__qname = None
        elif isinstance(value, Xsd_QName):
            self.__qname = Xsd_QName(value)
            self.__iri = None
            self.__ncname = None
        else:
            if ':' in str(value):  # must be IRI or QName
                try:
                    self.__qname = Xsd_QName(value, validate=validate)
                    self.__iri = None
                    self.__ncname = None
                except:
                    self.__iri = Iri(value, validate=validate)
                    self.__ncname = None
                    self.__qname = None
            else:
                self.__ncname = Xsd_NCName(value, validate=validate)
                self.__iri = None
                self.__qname = None

    @property
    def is_iri(self) -> bool:
        return self.__iri is not None

    @property
    def is_ncname(self) -> bool:
        return self.__ncname is not None

    @property
    def is_qname(self) -> bool:
        return self.__qname is not None

    @property
    def as_iri(self) -> Iri | None:
        if self.__iri:
            return self.__iri
        elif self.__qname:
            return Iri(self.__qname)
        else:
            return None

    @property
    def as_qname(self) -> Xsd_QName | None:
            return self.__qname if self.__qname else None

    @property
    def as_ncname(self) -> Xsd_NCName | None:
        return self.__ncname if self.__ncname else None

    def value(self) -> tuple[Xsd_NCName| None, Iri | None]:
        return self.as_ncname, self.as_iri

    def __str__(self):
        if self.__iri is not None:
            return str(self.__iri)
        elif self.__ncname is not None:
            return str(self.__ncname)
        elif self.__qname is not None:
            return str(self.__qname)
        else:
            return "???"
