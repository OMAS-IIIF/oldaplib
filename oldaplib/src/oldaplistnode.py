from dataclasses import dataclass
from enum import unique, Enum
from functools import partial
from typing import Self

from oldaplib.src.connection import Connection
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.permissions import AdminPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorImmutable
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.project import Project
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_string import Xsd_string


OldapListNodeAttrTypes = int | Xsd_NCName | LangString | Iri | None


@dataclass
class OldapListNodeAttrChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: OldapListNodeAttrTypes
    action: Action


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
        OldapListNodeAttr.OLDAPLISTNODE_ID: Xsd_NCName,
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
                 oldapListNodeId: Xsd_NCName | str,
                 inScheme: Iri | str,
                 leftIndex: int,
                 rightIndex: int,
                 creator: Iri | None = None,
                 created: Xsd_dateTime | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | None = None,
                 broaderTransitive: Iri | str | None = None,
                 nextNode: Iri | str | None = None,
                 prefLabel: LangString | str | None = None,
                 definition: LangString | str | None = None):
        super().__init__(connection=con,
                         creator=creator,
                         created=created,
                         contributor=contributor,
                         modified=modified)
        if isinstance(project, Project):
            self.__project = project
        else:
            self.__project = Project.read(self._con, project)
        context = Context(name=self._con.context_name)
        context[project.projectShortName] = project.namespaceIri
        context.use(project.projectShortName)
        self.__graph = project.projectShortName

        self.__attributes = {}

        self._graph = project.projectShortName
        if not isinstance(project, Project):
            raise OldapErrorValue('The project parameter must be a Project instance')
        self.__project = project
        self.__attributes[OldapListNodeAttr.OLDAPLISTNODE_ID] = Iri(oldapListNodeId)
        self.__attributes[OldapListNodeAttr.IN_SCHEME] = Iri(inScheme)
        if broaderTransitive:
            self.__attributes[OldapListNodeAttr.BROADER_TRANSITIVE] = Iri(broaderTransitive)
        if nextNode:
            self.__attributes[OldapListNodeAttr.NEXT_NODE] = Iri(nextNode)
        self.__attributes[OldapListNodeAttr.LEFT_INDEX] = leftIndex
        self.__attributes[OldapListNodeAttr.RIGHT_INDEX] = rightIndex
        if prefLabel:
            self.__attributes[OldapListNodeAttr.PREF_LABEL] = LangString(prefLabel)
            self.__attributes[OldapListNodeAttr.PREF_LABEL].set_notifier(self.notifier, Iri(OldapListNodeAttr.PREF_LABEL.value))
        if definition:
            self.__attributes[OldapListNodeAttr.DEFINITION] = LangString(definition)
            self.__attributes[OldapListNodeAttr.DEFINITION].set_notifier(self.notifier, Iri(OldapListNodeAttr.DEFINITION.value))
        #
        # create all the attributes of the class according to the OldapListAttr definition
        #
        for attr in OldapListNodeAttr:
            prefix, name = attr.value.split(':')
            setattr(OldapListNode, name, property(
                partial(OldapListNode.__get_value, attr=attr),
                partial(OldapListNode.__set_value, attr=attr),
                partial(OldapListNode.__del_value, attr=attr)))
        self.__changeset = {}

    def check_for_permissions(self) -> (bool, str):
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('oldap:SystemProject'))
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            #
            # user has root privileges!
            #
            return True, "OK – IS ROOT"
        else:
            if len(self.inProject) == 0:
                return False, f'Actor has no ADMIN_LISTS permission for user {self.userId}.'
            allowed: list[Iri] = []
            for proj in self.inProject.keys():
                if actor.inProject.get(proj) is None:
                    return False, f'Actor has no ADMIN_LISTS permission for project {proj}'
                else:
                    if AdminPermission.ADMIN_LISTS not in actor.inProject.get(proj):
                        return False, f'Actor has no ADMIN_LISTS permission for project {proj}'
            return True, "OK"

    def __get_value(self: Self, attr: OldapListNodeAttr) -> OldapListNodeAttrTypes | None:
        return self.__attributes.get(attr)

    def __set_value(self: Self, value: OldapListNodeAttrTypes, attr: OldapListNodeAttr) -> None:
        self.__change_setter(attr, value)

    def __del_value(self: Self, attr: OldapListNodeAttr) -> None:
        self.__changeset[attr] = OldapListNodeAttrChange(self.__attributes[attr], Action.DELETE)
        del self.__attributes[attr]

    def __change_setter(self, attr: OldapListNodeAttr, value: OldapListNodeAttrTypes) -> None:
        if self.__attributes.get(attr) == value:
            return
        if attr in {OldapListNodeAttr.OLDAPLIST_ID, OldapListNodeAttr.IN_SCHEME}:
            raise OldapErrorImmutable(f'Field {attr.value} is immutable.')
        if self.__attributes.get(attr) is None:
            if self.__changeset.get(attr) is None:
                self.__changeset[attr] = OldapListNodeAttrChange(None, Action.CREATE)
        else:
            if value is None:
                if self.__changeset.get(attr) is None:
                    self.__changeset[attr] = OldapListNodeAttrChange(self.__attributes[attr], Action.DELETE)
            else:
                if self.__changeset.get(attr) is None:
                    self.__changeset[attr] = OldapListNodeAttrChange(self.__attributes[attr], Action.REPLACE)
        if value is None:
            del self.__attributes[attr]
        else:
            if not isinstance(value, self.__datatypes[attr]):
                self.__attributes[attr] = self.__datatypes[attr](value)
            else:
                self.__attributes[attr] = value

    def __str__(self):
        res = f'OldapList: {self.__attributes[OldapListNodeAttr.OLDAPLIST_ID]} ({self.__oldaplist_iri})\n'\
              f'  Creation: {self._created} by {self._creator}\n'\
              f'  Modified: {self._modified} by {self._contributor}\n'\
              f'  Preferred label: {self.__attributes.get(OldapListNodeAttr.PREF_LABEL)}\n'\
              f'  Definition: {self.__attributes.get(OldapListNodeAttr.DEFINITION)}'
        return res

    def __getitem__(self, attr: OldapListNodeAttr) -> OldapListNodeAttrTypes:
        return self.__attributes[attr]

    def get(self, attr: OldapListNodeAttr) -> OldapListNodeAttrTypes:
        return self.__attributes.get(attr)

    def __setitem__(self, attr: OldapListNodeAttr, value: OldapListNodeAttrTypes) -> None:
        self.__change_setter(attr, value)

    def __delitem__(self, attr: OldapListNodeAttr) -> None:
        if self.__attributes.get(attr) is not None:
            self.__changeset[attr] = OldapListNodeAttrChange(self.__attributes[attr], Action.DELETE)
            del self.__attributes[attr]

if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     repo="oldap",
                     userId="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")
    oln = OldapListNode(con=con)
