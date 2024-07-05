from enum import unique

from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.helpers.propref import PropRef
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_integer import Xsd_integer


@unique
class HasPropertyAttr(AttributeClass):
    # order: (QName, mandatory, immutable, datatype)
    MIN_COUNT = ('sh:minCount', False, False, Xsd_integer)
    MAX_COUNT = ('sh:maxCount', False, False, Xsd_integer)
    ORDER = ('sh:order', False, False, Xsd_decimal)
    GROUP = ('sh:group', False, False, Iri)
