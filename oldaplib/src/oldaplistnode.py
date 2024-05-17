from enum import unique, Enum

from oldaplib.src.connection import Connection
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.project import Project
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
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
                 **kwargs):
        super().__init__(connection=con)
        if self.__system is None:
            self.__system = Project.read(con, 'oldap')
        if self.__listnodeclass is None:
            self.__listnodeclass = ResourceClass.read(con, self.__system, Iri('oldap:OldapListNode'))
        print(self.__system)
        print(self.__listnodeclass)

if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     repo="oldap",
                     userId="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")
    oln = OldapListNode(con=con)
