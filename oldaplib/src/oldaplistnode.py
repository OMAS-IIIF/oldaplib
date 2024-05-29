from enum import unique, Enum

from oldaplib.src.connection import Connection
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.project import Project
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_string import Xsd_string


@unique
class OldapListNodeAttr(Enum):
    """
    This enum class represents the fields used in the project model
    """
    OLDAPLISTNODE_IRI = 'oldap:oldapListNodeIri'  # virtual property, repents the RDF subject
    IN_SCHEME = 'skos:inScheme'
    BROADER_TRANSITIVE = 'skos:broaderTransitive'
    NEXT_NODE = 'oldap:nextNode'
    LEFT_INDEX = 'oldap:leftIndex'
    RIGHT_INDEX = 'oldap:rightIndex'
    NOTATION = 'skos:notation'
    NOTE = 'skos:note'
    PREF_LABEL = 'skos:prefLabel'
    ALT_LABEL = 'skos:altLabel'
    DEFINITION = 'skos:definition'
    CHANGE_NOTE = 'skos:changeNote'

class OldapListNode(Model):
    __datatypes = {
        OldapListNodeAttr.OLDAPLISTNODE_IRI: Iri,
        OldapListNodeAttr.IN_SCHEME: Iri,
        OldapListNodeAttr.BROADER_TRANSITIVE: Iri,
        OldapListNodeAttr.NEXT_NODE: Iri,
        OldapListNodeAttr.LEFT_INDEX: int,
        OldapListNodeAttr.RIGHT_INDEX: int,
        OldapListNodeAttr.NOTATION: Xsd_string,
        OldapListNodeAttr.NOTE: LangString,
        OldapListNodeAttr.PREF_LABEL: LangString,
        OldapListNodeAttr.ALT_LABEL: LangString,
        OldapListNodeAttr.DEFINITION: LangString,
        OldapListNodeAttr.CHANGE_NOTE: Xsd_string,
    }

    __system = None
    __listnodeclass = None

    def __init__(self, *,
                 con: IConnection,
                 project: Project,
                 creator: Iri | None = None,
                 created: Xsd_dateTime | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | None = None,
                 oldapListIri: Iri | str | None = None,
                 prefLabel: LangString | str | None = None,):

if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     repo="oldap",
                     userId="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")
    oln = OldapListNode(con=con)
