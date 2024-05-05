from enum import Enum, unique

from omaslib.src.helpers.langstring import LangString
from omaslib.src.model import Model
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_datetime import Xsd_dateTime


ProjectAttrTypes = LangString | Iri | None

@unique
class OldapListAttr(Enum):
    """
    This enum class represents the fields used in the project model
    """
    OLDAPLIST_IRI = 'omas:oldapListIri'  # virtual property, repents the RDF subject
    PREF_LABEL = 'skos:prefLabel'
    DEFINITION = 'skos:definition'

class OldapList(Model):

    __datatypes = {
        OldapListAttr.OLDAPLIST_IRI: Iri,
        OldapListAttr.PREF_LABEL: LangString,
        OldapListAttr.DEFINITION: LangString,
    }

    __creator: Iri | None
    __created: Xsd_dateTime | None
    __contributor: Iri | None
    __modified: Xsd_dateTime | None

    __fields: dict[OldapListAttr, ProjectAttrTypes]

    __changeset: dict[OldapListAttr, ProjectAttrTypes]

    def __init__(self):
        pass