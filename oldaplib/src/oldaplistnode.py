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
from oldaplib.src.helpers.tools import lprint
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model, AttributeChange
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName

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
    __iri: Iri | None
    __sublist: list[Self] | None
    __leftIndex: Xsd_integer | None
    __rightIndex: Xsd_integer | None

    def __init__(self, *,
                 con: IConnection,
                 oldapList: OldapList,
                 creator: Iri | None = None,
                 created: Xsd_dateTime | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | None = None,
                 leftIndex: Xsd_integer | None = None,
                 rightIndex: Xsd_integer | None = None,
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

        self.__iri = Iri.fromPrefixFragment(self.__oldapList.oldapListId,
                                            self._attributes[OldapListNodeAttr.OLDAPLISTNODE_ID],
                                            validate=False)

        self.__leftIndex = leftIndex
        self.__rightIndex = rightIndex
        self.__sublist = None

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

    @property
    def iri(self) -> Iri:
        return self.__iri

    @property
    def leftIndex(self) -> Xsd_integer | None:
        return self.__leftIndex

    @property
    def rightIndex(self) -> Xsd_integer | None:
        return self.__rightIndex

    def notifier(self, attr: OldapListNodeAttr) -> None:
        """
        This method is called when a field is being changed.
        :param fieldname: Fieldname of the field being modified
        :return: None
        """
        self._changeset[attr] = AttributeChange(self._attributes[attr], Action.MODIFY)

    @classmethod
    def read(cls, *,
             con: IConnection,
             oldapList: OldapList,
             oldapListNodeId: Xsd_NCName | str):
        oldapListNodeId = Xsd_NCName(oldapListNodeId)

        node_iri = Iri.fromPrefixFragment(oldapList.oldapListId, oldapListNodeId, validate=False)

        context = Context(name=con.context_name)
        graph = oldapList.project.projectShortName
        query = context.sparql_context
        query += f'''
            SELECT ?prop ?val
            FROM {graph}:lists
            WHERE {{
                {node_iri.toRdf} ?prop ?val .
            }}
        '''
        jsonobj = con.query(query)
        res = QueryProcessor(context, jsonobj)
        creator: Iri | None = None
        created: Xsd_dateTime | None = None
        contributor: Iri | None = None
        modified: Xsd_dateTime | None = None
        prefLabel: LangString | None = None
        definition: LangString | None = None
        leftIndex: Xsd_integer | None = None
        rightIndex: Xsd_integer | None = None
        for r in res:
            match str(r.get('prop')):
                case 'dcterms:creator':
                    creator = r['val']
                case 'dcterms:created':
                    created = r['val']
                case 'dcterms:contributor':
                    contributor = r['val']
                case 'dcterms:modified':
                    modified = r['val']
                case OldapListNodeAttr.PREF_LABEL.value:
                    if not prefLabel:
                        prefLabel = LangString()
                    prefLabel.add(r['val'])
                case OldapListNodeAttr.DEFINITION.value:
                    if not definition:
                        definition = LangString()
                    definition.add(r['val'])
                case 'oldap:leftIndex':
                    leftIndex = r['val']
                case 'oldap:rightIndex':
                    rightIndex = r['val']
        if prefLabel:
            prefLabel.changeset_clear()
            prefLabel.set_notifier(cls.notifier, Xsd_QName(OldapListNodeAttr.PREF_LABEL.value))
        if definition:
            definition.changeset_clear()
            definition.set_notifier(cls.notifier, Xsd_QName(OldapListNodeAttr.DEFINITION.value))
        return cls(con=con,
                   oldapList=oldapList,
                   oldapListNodeId=oldapListNodeId,
                   creator=creator,
                   created=created,
                   contributor=contributor,
                   modified=modified,
                   prefLabel=prefLabel,
                   definition=definition,
                   leftIndex=leftIndex,
                   rightIndex=rightIndex)

    def create_root_node(self, indent: int = 0, indent_inc: int = 4) -> None:
        if self._con is None:
            raise OldapError("Cannot create: no connection")

        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        self.__leftIndex = Xsd_integer(1)
        self.__rightIndex = Xsd_integer(2)

        context = Context(name=self._con.context_name)

        timestamp = Xsd_dateTime.now()
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
        sparql2 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__iri.toRdf} a oldap:OldapListNode'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creationDate {timestamp.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:inScheme {self.__oldapList.oldapList_iri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:leftIndex {self.__leftIndex.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:rightIndex {self.__rightIndex.toRdf}'
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

    def insert_node_right_of(self, leftnode: Self, indent: int = 0, indent_inc: int = 4) -> None:

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
        update1 = context.sparql_context
        update1 += f'{blank:{indent * indent_inc}}DELETE {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f'\n{blank:{(indent + 2) * indent_inc}}{leftnode.iri.toRdf} oldap:nextNode ?rightNode'
        update1 += f' .\n{blank:{(indent + 1) * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}INSERT {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__iri.toRdf} a oldap:OldapListNode'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creationDate {timestamp.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:inScheme {self.__oldapList.oldapList_iri.toRdf}'
        if self.prefLabel:
            update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.PREF_LABEL.value} {self.prefLabel.toRdf}'
        if self.definition:
            update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.DEFINITION.value} {self.definition.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:leftIndex ?nlindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:rightIndex ?nrindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:broaderTransitive ?parent_node'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:nextNode ?rightNode'
        update1 += f' .\n{blank:{(indent + 2) * indent_inc}}{leftnode.iri.toRdf} oldap:nextNode {self.__iri.toRdf}'
        update1 += f' .\n{blank:{(indent + 1) * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}WHERE {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f' \n{blank:{(indent + 2) * indent_inc}}{leftnode.iri.toRdf} oldap:rightIndex ?rindex'
        update1 += f' ;\n{blank:{(indent + 2) * indent_inc}}OPTIONAL {{'
        update1 += f'\n{blank:{(indent + 3) * indent_inc}}{leftnode.iri.toRdf} skos:broaderTransitive ?parent_node'
        update1 += f' .\n{blank:{(indent + 2) * indent_inc}}}}'
        update1 += f'\n{blank:{(indent + 2) * indent_inc}}OPTIONAL {{'
        update1 += f'\n{blank:{(indent + 3) * indent_inc}}{leftnode.iri.toRdf} oldap:nextNode ?rightNode'
        update1 += f' .\n{blank:{(indent + 2) * indent_inc}}}}'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}}}'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}BIND((?rindex + 1) AS ?nlindex)'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}BIND((?rindex + 2) AS ?nrindex)'
        update1 += f'\n{blank:{indent * indent_inc}}}}'

        self._con.transaction_start()
        try:
            self._con.transaction_update(update1)
        except OldapError:
            lprint(update1)
            self._con.transaction_abort()
            raise

        query1 = context.sparql_context
        query1 += f"""
        SELECT ?node ?rindex ?lindex    
        WHERE {{
            GRAPH {self.__graph}:lists {{
                {self.__iri.toRdf} oldap:rightIndex ?rindex ;
                    oldap:leftIndex ?lindex .
            }}
        }}
        """
        try:
            jsonobj = self._con.transaction_query(query1)
        except OldapError:
            self._con.transaction_abort()
            raise
        rindex = 0
        lindex = 0
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            raise OldapError('Insert_node_right_of failed')
        for row in res:
            rindex = row['rindex']
            lindex = row['lindex']

        update2 = context.sparql_context
        update2 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?node oldap:leftIndex ?lindex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?node oldap:leftIndex ?nlindex .
            }}
        }}
        WHERE {{
            GRAPH {self.__graph}:lists {{
                ?node skos:inScheme {self.__oldapList.oldapList_iri.toRdf} ;
                      oldap:rightIndex ?rindex ;
                      oldap:leftIndex ?lindex .
            }}
            FILTER( ((?lindex + 1) >= {rindex}) && (?node != {self.__iri.toRdf}))
            BIND((?lindex + 2) AS ?nlindex)
        }}
        """
        try:
            self._con.transaction_update(update2)
        except OldapError:
            self._con.transaction_abort()
            raise

        update3 = context.sparql_context
        update3 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?node oldap:rightIndex ?rindex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?node oldap:rightIndex ?nrindex .
            }}
        }}
        WHERE {{
            GRAPH {self.__graph}:lists {{
                ?node skos:inScheme {self.__oldapList.oldapList_iri.toRdf} ;
                      oldap:rightIndex ?rindex ;
                      oldap:leftIndex ?lindex ;
            }}
            FILTER( (?rindex >= {lindex}) && (?node != {self.__iri.toRdf}))
            BIND((?rindex + 2) AS ?nrindex)
        }}
        """
        try:
            self._con.transaction_update(update3)
        except OldapError:
            self._con.transaction_abort()
            raise

        try:
            jsonobj = self._con.transaction_query(query1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            raise OldapError('Insert_node_right_of failed')
        for row in res:
            self.__leftIndex = row['lindex']
            self.__rightIndex = row['rindex']

        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise

    def insert_node_left_of(self, rightnode: Self, indent: int = 0, indent_inc: int = 4) -> None:

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
        update1 = context.sparql_context
        update1 = context.sparql_context
        update1 += f'{blank:{indent * indent_inc}}DELETE {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f'\n{blank:{(indent + 2) * indent_inc}}?node oldap:nextNode {rightnode.iri.toRdf}'
        update1 += f' .\n{blank:{(indent + 1) * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}INSERT {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__iri.toRdf} a oldap:OldapListNode'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creationDate {timestamp.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:inScheme {self.__oldapList.oldapList_iri.toRdf}'
        if self.prefLabel:
            update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.PREF_LABEL.value} {self.prefLabel.toRdf}'
        if self.definition:
            update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.DEFINITION.value} {self.definition.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:leftIndex ?lindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:rightIndex ?nrindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:broaderTransitive ?parent_node'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:nextNode {rightnode.iri.toRdf}'
        update1 += f' .\n{blank:{(indent + 2) * indent_inc}}?node oldap:nextNode {self.__iri.toRdf}'
        update1 += f' .\n{blank:{(indent + 1) * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}WHERE {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f' \n{blank:{(indent + 2) * indent_inc}}{rightnode.iri.toRdf} oldap:leftIndex ?lindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:rightIndex ?rindex'
        update1 += f' ;\n{blank:{(indent + 2) * indent_inc}}OPTIONAL {{'
        update1 += f'\n{blank:{(indent + 3) * indent_inc}}{rightnode.iri.toRdf} skos:broaderTransitive ?parent_node'
        update1 += f' .\n{blank:{(indent + 2) * indent_inc}}}}'
        update1 += f'\n{blank:{(indent + 2) * indent_inc}}OPTIONAL {{'
        update1 += f'\n{blank:{(indent + 3) * indent_inc}}?node oldap:nextNode {rightnode.iri.toRdf}'
        update1 += f' .\n{blank:{(indent + 2) * indent_inc}}}}'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}}}'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}BIND((?lindex + 1) AS ?nrindex)'
        update1 += f'\n{blank:{indent * indent_inc}}}}'

        self._con.transaction_start()
        try:
            self._con.transaction_update(update1)
        except OldapError:
            lprint(update1)
            self._con.transaction_abort()
            raise

        query1 = context.sparql_context
        query1 += f"""
        SELECT ?rindex ?lindex    
        WHERE {{
            GRAPH {self.__graph}:lists {{
                {self.__iri.toRdf} oldap:rightIndex ?rindex ;
                    oldap:leftIndex ?lindex .
            }}
        }}
        """
        try:
            jsonobj = self._con.transaction_query(query1)
        except OldapError:
            lprint(query1)
            self._con.transaction_abort()
            raise
        rindex = 0
        lindex = 0
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            raise OldapError('Insert_node_right_of failed')
        for row in res:
            rindex = row['rindex']
            lindex = row['lindex']

        update2 = context.sparql_context
        update2 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?node oldap:leftIndex ?lindex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?node oldap:leftIndex ?nlindex .
            }}
        }}
        WHERE {{
            GRAPH {self.__graph}:lists {{
                ?node skos:inScheme {self.__oldapList.oldapList_iri.toRdf} ;
                      oldap:leftIndex ?lindex .
            }}
            FILTER((?node != {self.__iri.toRdf}) && (?lindex >= {lindex}))
            BIND((?lindex + 2) AS ?nlindex)
        }}
        """
        try:
            self._con.transaction_update(update2)
        except OldapError:
            self._con.transaction_abort()
            raise

        update3 = context.sparql_context
        update3 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?node oldap:rightIndex ?rindex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?node oldap:rightIndex ?nrindex .
            }}
        }}
        WHERE {{
            GRAPH {self.__graph}:lists {{
               ?node skos:inScheme {self.__oldapList.oldapList_iri.toRdf} ;
                      oldap:rightIndex ?rindex ;
            }}
            FILTER((?node != {self.__iri.toRdf}) && (?rindex >= {rindex}))
            BIND((?rindex + 2) AS ?nrindex)
        }}
        """
        try:
            self._con.transaction_update(update3)
        except OldapError:
            lprint(update3)
            self._con.transaction_abort()
            raise

        try:
            jsonobj = self._con.transaction_query(query1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            raise OldapError('Insert_node_right_of failed')
        for row in res:
            self.__leftIndex = row['lindex']
            self.__rightIndex = row['rindex']

        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
