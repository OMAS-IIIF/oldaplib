from enum import unique, Enum

from oldaplib.src.connection import Connection
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.project import Project
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
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
    PREF_LABEL = 'skos:prefLabel'
    DEFINITION = 'skos:definition'

class OldapListNode(Model):
    __datatypes = {
        OldapListNodeAttr.OLDAPLISTNODE_IRI: Iri,
        OldapListNodeAttr.IN_SCHEME: Iri,
        OldapListNodeAttr.BROADER_TRANSITIVE: Iri,
        OldapListNodeAttr.NEXT_NODE: Iri,
        OldapListNodeAttr.LEFT_INDEX: int,
        OldapListNodeAttr.RIGHT_INDEX: int,
        OldapListNodeAttr.PREF_LABEL: LangString,
        OldapListNodeAttr.DEFINITION: LangString,
    }

    __system = None
    __listnodeclass = None
    __project: Project

    def __init__(self, *,
                 con: IConnection,
                 project: Project | Iri | Xsd_NCName | str,
                 creator: Iri | None = None,
                 created: Xsd_dateTime | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | None = None,
                 oldapListNodeIri: Iri | str | None = None,
                 inScheme: Iri | str,
                 broaderTransitive: Iri | str | None = None,
                 nextNode: Iri | str | None = None,
                 leftIndex: int,
                 rightIndex: int,
                 prefLabel: LangString | str | None = None,
                 definition: LangString | str | None = None):
        super().__init__(con)
        self.__creator = Iri(creator) if creator else con.userIri
        self.__created = Xsd_dateTime(created) if created else None
        self.__contributor = Iri(contributor) if contributor else con.userIri
        self.__modified = Xsd_dateTime(modified) if modified else None
        self.__attributes = {}

        self._graph = project.projectShortName
        if not isinstance(project, Project):
            raise OldapErrorValue('The project parameter must be a Project instance')
        self.__project = project
        self.__attributes[OldapListNodeAttr.OLDAPLISTNODE_IRI] = Iri(oldapListNodeIri)
        self.__attributes[OldapListNodeAttr.IN_SCHEME] = Iri(inScheme)
        if broaderTransitive:
            self.__attributes[OldapListNodeAttr.BROADER_TRANSITIVE] = Iri(broaderTransitive)
        if nextNode:
            self.__attributes[OldapListNodeAttr.NEXT_NODE] = Iri(nextNode)
        self.__attributes[OldapListNodeAttr.LEFT_INDEX] = leftIndex
        self.__attributes[OldapListNodeAttr.RIGHT_INDEX] = rightIndex
        self.__attributes[OldapListNodeAttr.PREF_LABEL] = LangString(prefLabel)
        self.__attributes[OldapListNodeAttr.PREF_LABEL].set_notifier(self.notifier, Iri(OldapListNodeAttr.PREF_LABEL.value))
        self.__attributes[OldapListNodeAttr.DEFINITION] = LangString(definition)
        self.__attributes[OldapListNodeAttr.DEFINITION].set_notifier(self.notifier, Iri(OldapListNodeAttr.DEFINITION.value))



if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     repo="oldap",
                     userId="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")
    oln = OldapListNode(con=con)
