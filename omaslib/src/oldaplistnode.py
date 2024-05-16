from enum import unique, Enum

from omaslib.src.connection import Connection
from omaslib.src.helpers.langstring import LangString
from omaslib.src.iconnection import IConnection
from omaslib.src.model import Model
from omaslib.src.project import Project
from omaslib.src.resourceclass import ResourceClass
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_string import Xsd_string


@unique
class OldapListNodeAttr(Enum):
    """
    This enum class represents the fields used in the project model
    """
    OLDAPLISTNODE_IRI = 'omas:oldapListNodeIri'  # virtual property, repents the RDF subject
    IN_SCHEME = 'skos:inScheme'
    BROADER_TRANSITIVE = 'skos:broaderTransitive'
    NEXT_NODE = 'omas:nextNode'
    LEFT_INDEX = 'omas:leftIndex'
    RIGHT_INDEX = 'omas:rightIndex'
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
            self.__system = Project.read(con, 'omas')
        if self.__listnodeclass is None:
            self.__listnodeclass = ResourceClass.read(con, self.__system, Iri('omas:OldapListNode'))
        print(self.__system)
        print(self.__listnodeclass)

if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     repo="omas",
                     userId="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")
    oln = OldapListNode(con=con)
