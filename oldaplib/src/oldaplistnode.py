from dataclasses import dataclass
from functools import partial
from typing import Self

from oldaplib.src.connection import Connection
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.oldaplistnodeattr import OldapListNodeAttr
from oldaplib.src.enums.permissions import AdminPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorImmutable
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName

OldapListNodeAttrTypes = int | Xsd_NCName | LangString | Iri | None


@dataclass
class OldapListNodeAttrChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: OldapListNodeAttrTypes
    action: Action


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

    __project: Project
    __graph: Xsd_NCName
    __oldapListNode_iri: Iri | None
    __broaderTransitive: Iri | None
    __nextNode: Iri | None
    __leftIndex: int | None
    __rightIndex: int | None

    def __init__(self, *,
                 con: IConnection,
                 project: Project | Iri | Xsd_NCName | str,
                 creator: Iri | None = None,
                 created: Xsd_dateTime | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | None = None,
                 **kwargs):
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

        self.set_attributes(kwargs, OldapListNodeAttr)

        self.__oldapList_iri = Iri.fromPrefixFragment(self.__project.projectShortName,
                                                      self._attributes[OldapListNodeAttr.OLDAPLISTNODE_ID],
                                                      validate=False)

        self.__broaderTransitive = None
        self.__nextNode = None
        self.__leftIndex = None
        self.__rightIndex = None
        #
        # create all the attributes of the class according to the OldapListAttr definition
        #
        for attr in OldapListNodeAttr:
            setattr(OldapListNode, attr.value.fragment, property(
                partial(OldapListNode._get_value, attr=attr),
                partial(OldapListNode._set_value, attr=attr),
                partial(OldapListNode._del_value, attr=attr)))

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


if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     repo="oldap",
                     userId="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")
    oln = OldapListNode(con=con)
