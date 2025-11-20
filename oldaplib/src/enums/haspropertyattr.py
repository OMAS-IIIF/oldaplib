from enum import unique

from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger
from oldaplib.src.xsd.xsd_qname import Xsd_QName


@unique
class HasPropertyAttr(AttributeClass):
    # order: (QName, mandatory, immutable, datatype)
    MIN_COUNT = ('sh:minCount', False, False, Xsd_integer)
    MAX_COUNT = ('sh:maxCount', False, False, Xsd_integer)
    ORDER = ('sh:order', False, False, Xsd_decimal)
    GROUP = ('sh:group', False, False, Xsd_QName)
