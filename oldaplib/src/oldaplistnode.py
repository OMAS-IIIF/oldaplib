from dataclasses import dataclass
from functools import partial
from typing import Self

from oldaplib.src.connection import Connection
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.oldaplistnodeattr import OldapListNodeAttr
from oldaplib.src.enums.permissions import AdminPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorImmutable, OldapError, OldapErrorNoPermission, \
    OldapErrorAlreadyExists
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_integer import Xsd_integer
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
    __oldapList: OldapList
    __graph: Xsd_NCName
    __oldapListNode_iri: Iri | None
    __sublist: list[Self] | None
    __leftIndex: int | None
    __rightIndex: int | None

    def __init__(self, *,
                 con: IConnection,
                 oldapList: OldapList,
                 creator: Iri | None = None,
                 created: Xsd_dateTime | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | None = None,
                 sublist: list[Self] | None = None,
                 leftIndex: Xsd_integer | int | None = None,
                 rightIndex: Xsd_integer | int | None = None,
                 **kwargs):
        super().__init__(connection=con,
                         creator=creator,
                         created=created,
                         contributor=contributor,
                         modified=modified)
        self.__oldapList = oldapList
        context = Context(name=self._con.context_name)
        self.__graph = oldapList.project.projectShortName

        self.set_attributes(kwargs, OldapListNodeAttr)

        self.__oldapListNode_iri = Iri.fromPrefixFragment(self.__oldapList.oldapListId,
                                                      self._attributes[OldapListNodeAttr.OLDAPLISTNODE_ID],
                                                      validate=False)

        self.__rightIndex = Xsd_integer(rightIndex) if rightIndex is not None else None
        self.__leftIndex = Xsd_integer(leftIndex) if leftIndex is not None else None
        self.__sublist = sublist

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

    def create(self, indent: int = 0, indent_inc: int = 4):
        if self._con is None:
            raise OldapError("Cannot create: no connection")

        timestamp = Xsd_dateTime.now()
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        context = Context(name=self._con.context_name)

        blank = ''
        #
        # Sparql to check if list has already eny nodes. If so, root node creation is not possible!
        #
        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?list
        FROM {self.__graph}:lists
        WHERE {{
            ?listnode a oldap:OldapListNode .
            ?listnode skos:inScheme {self.__oldapList.oldapList_iri.toRdf}
        }}
        """

        sparql2 = context.sparql_context
        sparql2 += f'{blank:{indent * indent_inc}}INSERT DATA {{'
        sparql2 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        sparql2 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__oldapListNode_iri.toRdf} a oldap:OldapListNode'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creationDate {timestamp.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:inScheme {self.__oldapList.oldapList_iri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:leftIndex {self.__leftIndex.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:rightIndex {self.__leftIndex.toRdf}'
        if self.prefLabel:
            sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.PREF_LABEL.value} {self.prefLabel.toRdf}'
        if self.definition:
            sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.DEFINITION.value} {self.definition.toRdf}'
        sparql2 += f' .\n{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql2 += f'{blank:{indent * indent_inc}}}}\n'

        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(sparql1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'A root node for "{self.__oldapList.oldapList_iri}" already exists')

        try:
            self._con.transaction_update(sparql2)
        except OldapError:
            self._con.transaction_abort()
            raise
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise



    def create_root_node(self, *,
                         con: IConnection,
                         oldapList: OldapList,
                         **kwargs) -> Self:

        return node

    @classmethod
    def insert_node_right_of(cls, *,
                             con: IConnection,
                             oldapList: OldapList,
                             **kwargs) -> Self:

        node = cls(con=con, oldapList=oldapList)

        if con is None:
            raise OldapError("Cannot create: no connection")

        timestamp = Xsd_dateTime.now()
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        result, message = node.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        context = Context(name=con.context_name)


if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     repo="oldap",
                     userId="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")
    oln = OldapListNode.create_root_node(con=con, oldapListNodeId="first")
