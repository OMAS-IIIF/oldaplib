from enum import unique

from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


@unique
class ExternalOntologyAttr(AttributeClass):
    """Enumeration of attributes from external ontologies.

    Attributes are defined as tuples with the following structure:
    (QName, mandatory, immutable, datatype)
    """
    # order: (QName, mandatory, immutable, datatype)
    PREFIX = ('oldap:prefix', True, True, Xsd_NCName)
    NAMESPACE_IRI = ('oldap:namespaceIri', True, True, NamespaceIRI)
