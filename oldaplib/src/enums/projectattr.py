from enum import unique

from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.observable_dict import ObservableDict
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


@unique
class ProjectAttr(AttributeClass):
    """
    This enum class represents the fields used in the project model
    """
    # order: (QName, mandatory, immutable, datatype)
    PROJECT_IRI = ('oldap:projectIri', False, True, Iri)  # virtual property, represents the RDF subject
    PROJECT_SHORTNAME = ('oldap:projectShortName', True, True, Xsd_NCName)
    LABEL = ('rdfs:label', False, False, LangString)
    COMMENT = ('rdfs:comment', False, False, LangString)
    NAMESPACE_IRI = ('oldap:namespaceIri', True, True, NamespaceIRI)
    PROJECT_START = ('oldap:projectStart', False, False, Xsd_date)
    PROJECT_END = ('oldap:projectEnd', False, False, Xsd_date)
