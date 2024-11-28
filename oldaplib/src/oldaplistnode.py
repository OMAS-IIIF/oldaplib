from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from typing import Self, Any

from oldaplib.src.cachesingleton import CacheSingleton
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.oldaplistnodeattr import OldapListNodeAttr
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission, \
    OldapErrorAlreadyExists, OldapErrorInconsistency, OldapErrorNotFound, OldapErrorUpdateFailed
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.tools import lprint
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string

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
    __nodes: list[Self] | None
    __leftIndex: Xsd_integer | None
    __rightIndex: Xsd_integer | None

    #__slots__ = OldapListNodeAttr.nametuple()
    __slots__ = ('oldapListNodeId', 'prefLabel', 'definition')

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
        if self._attributes.get(OldapListNodeAttr.PREF_LABEL) is None:
            self._attributes[OldapListNodeAttr.PREF_LABEL] = LangString(str(self._attributes[OldapListNodeAttr.OLDAPLISTNODE_ID]))

        list_node_prefix = Xsd_NCName("L-") + self.__oldapList.oldapListId
        self.__iri = Iri.fromPrefixFragment(list_node_prefix,
                                            self._attributes[OldapListNodeAttr.OLDAPLISTNODE_ID],
                                            validate=False)

        self.__leftIndex = leftIndex
        self.__rightIndex = rightIndex
        self.__nodes = None

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


    def __deepcopy__(self, memo: dict[Any, Any]) -> Self:
        if id(self) in memo:
            return memo[id(self)]
        cls = self.__class__
        instance = cls.__new__(cls)
        memo[id(self)] = instance
        Model.__init__(instance,
                       connection=deepcopy(self._con, memo),
                       creator=deepcopy(self._creator, memo),
                       created=deepcopy(self._created, memo),
                       contributor=deepcopy(self._contributor, memo),
                       modified=deepcopy(self._modified, memo))

        # Copy internals of Model:
        instance._attributes = deepcopy(self._attributes, memo)
        instance.__oldapList = deepcopy(self.__oldapList, memo)
        instance.__graph = deepcopy(self.__graph, memo)
        instance.__iri = deepcopy(self.__iri, memo)
        instance.__nodes = deepcopy(self.__nodes, memo)
        instance.__leftIndex = deepcopy(self.__leftIndex, memo)
        instance.__rightIndex = deepcopy(self.__rightIndex, memo)

        return instance



    @property
    def iri(self) -> Iri:
        return self.__iri

    @property
    def leftIndex(self) -> Xsd_integer | None:
        return self.__leftIndex

    @property
    def rightIndex(self) -> Xsd_integer | None:
        return self.__rightIndex

    @property
    def nodes(self) -> list[Self]:
        return self.__nodes

    @nodes.setter
    def nodes(self, nodes: list[Self]):
        self.__nodes = nodes

    def add_node_to_nodes(self, node: Self) -> None:
        if self.__nodes is None:
            self.__nodes = [node]
        else:
            self.__nodes.append(node)

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

        list_node_prefix = Xsd_NCName("L-", validate=False) + oldapList.oldapListId
        node_iri = Iri.fromPrefixFragment(list_node_prefix, oldapListNodeId, validate=False)

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
        if len(res) == 0:
            raise OldapErrorNotFound(f'Node with id "{oldapListNodeId}" not found.')
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
        sparql2 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__iri.toRdf} a {self.__oldapList.node_class_iri}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
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
            print(sparql2)
            raise
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        cache = CacheSingleton()
        cache.delete(self.__oldapList.oldapList_iri)


    def update(self, indent: int = 0, indent_inc: int = 4):
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)
        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)
        blank = ''
        sparql_list = []

        for field, change in self._changeset.items():
            if field == OldapListNodeAttr.PREF_LABEL or field == OldapListNodeAttr.DEFINITION:
                if change.action == Action.MODIFY:
                    sparql_list.extend(self._attributes[field].update(graph=Xsd_QName(f'{self.__graph}:lists'),
                                                                      subject=self.__iri,
                                                                      field=Xsd_QName(field.value)))
                if change.action == Action.DELETE or change.action == Action.REPLACE:
                    sparql = self._changeset[field].old_value.delete(graph=Xsd_QName(f'{self.__graph}:lists'),
                                                                     subject=self.__iri,
                                                                     field=Xsd_QName(field.value))
                    sparql_list.append(sparql)
                if change.action == Action.CREATE or change.action == Action.REPLACE:
                    sparql = self._attributes[field].create(graph=Xsd_QName(f'{self.__graph}:lists'),
                                                            subject=self.__iri,
                                                            field=Xsd_QName(field.value))
                    sparql_list.append(sparql)

        sparql = context.sparql_context
        sparql += " ;\n".join(sparql_list)

        self._con.transaction_start()
        try:
            self._con.transaction_update(sparql)
            self.set_modified_by_iri(Xsd_QName(f'{self.__graph}:lists'), self.__iri, self.modified, timestamp)
            modtime = self.get_modified_by_iri(Xsd_QName(f'{self.__graph}:lists'), self.__iri)
        except OldapError:
            self._con.transaction_abort()
            raise
        if timestamp != modtime:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed("Update failed! Timestamp does not match")
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        self._modified = timestamp
        self._contributor = self._con.userIri  # TODO: move creator, created etc. to Model!
        self.clear_changeset()
        cache = CacheSingleton()
        cache.delete(self.__oldapList.oldapList_iri)

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
        update1 += f'\n{blank:{indent * indent_inc}}INSERT {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__iri.toRdf} a {self.__oldapList.node_class_iri}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
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
        update1 += f' .\n{blank:{(indent + 1) * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}WHERE {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f' \n{blank:{(indent + 2) * indent_inc}}{leftnode.iri.toRdf} oldap:rightIndex ?rindex'
        update1 += f' ;\n{blank:{(indent + 2) * indent_inc}}OPTIONAL {{'
        update1 += f'\n{blank:{(indent + 3) * indent_inc}}{leftnode.iri.toRdf} skos:broaderTransitive ?parent_node'
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
            self._con.transaction_abort()
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
            self._con.transaction_abort()
            raise OldapError('Insert_node_right_of failed')
        for row in res:
            self.__leftIndex = row['lindex']
            self.__rightIndex = row['rindex']

        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        self.clear_changeset()
        cache = CacheSingleton()
        cache.delete(self.__oldapList.oldapList_iri)

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
        update1 += f'\n{blank:{indent * indent_inc}}INSERT {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__iri.toRdf} a {self.__oldapList.node_class_iri}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
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
        update1 += f' .\n{blank:{(indent + 1) * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}WHERE {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f' \n{blank:{(indent + 2) * indent_inc}}{rightnode.iri.toRdf} oldap:leftIndex ?lindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:rightIndex ?rindex'
        update1 += f' ;\n{blank:{(indent + 2) * indent_inc}}OPTIONAL {{'
        update1 += f'\n{blank:{(indent + 3) * indent_inc}}{rightnode.iri.toRdf} skos:broaderTransitive ?parent_node'
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
            self._con.transaction_abort()
            raise OldapError('Insert_node_left_of failed')
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
            self._con.transaction_abort()
            raise OldapError('Insert_node_left_of failed')
        for row in res:
            self.__leftIndex = row['lindex']
            self.__rightIndex = row['rindex']

        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        self.clear_changeset()
        cache = CacheSingleton()
        cache.delete(self.__oldapList.oldapList_iri)

    def insert_node_below_of(self, parentnode: Self, indent: int = 0, indent_inc: int = 4) -> None:
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

        query1 = context.sparql_context
        query1 += f"""
        SELECT ?node
        WHERE {{
            GRAPH {self.__graph}:lists {{
                ?node skos:broaderTransitive {parentnode.iri.toRdf} .
            }}
        }}
        """
        self._con.transaction_start()

        try:
            jsonobj = self._con.transaction_query(query1)
        except OldapError:
            lprint(query1)
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OldapErrorInconsistency(f'insert_node_below_of: Insertion point already has sub-node(s)!')

        blank = ''
        update1 = context.sparql_context
        update1 += f'{blank:{indent * indent_inc}}INSERT {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__iri.toRdf} a {self.__oldapList.node_class_iri}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:inScheme {self.__oldapList.oldapList_iri.toRdf}'
        if self.prefLabel:
            update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.PREF_LABEL.value} {self.prefLabel.toRdf}'
        if self.definition:
            update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.DEFINITION.value} {self.definition.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:leftIndex ?nlindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:rightIndex ?nrindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:broaderTransitive {parentnode.iri.toRdf}'
        update1 += f' .\n{blank:{(indent + 1) * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}WHERE {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f' \n{blank:{(indent + 2) * indent_inc}}{parentnode.iri.toRdf} oldap:leftIndex ?lindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:rightIndex ?rindex'
        update1 += f' ;\n{blank:{(indent + 2) * indent_inc}}BIND(?rindex AS ?nlindex)'
        update1 += f'\n{blank:{(indent + 2) * indent_inc}}BIND((?rindex + 1) AS ?nrindex)'
        #update1 += f' ;\n{blank:{(indent + 1) * indent_inc}}BIND((?rindex + 2) AS ?npindex)'
        update1 += f' .\n{blank:{(indent + 1) * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}}}'

        try:
            self._con.transaction_update(update1)
        except OldapError:
            lprint(update1)
            self._con.transaction_abort()
            raise

        query2 = context.sparql_context
        query2 += f"""
        SELECT ?lindex ?rindex
        WHERE {{
            GRAPH {self.__graph}:lists {{
                {self.__iri.toRdf} 
                    oldap:leftIndex ?lindex ;
                    oldap:rightIndex ?rindex .
            }}
        }}
        """
        try:
            jsonobj = self._con.transaction_query(query2)
        except OldapError:
            lprint(query2)
            self._con.transaction_abort()
            raise
        rindex = 0
        lindex = 0
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            self._con.transaction_abort()
            raise OldapError('Insert_node_below_of failed')
        for row in res:
            rindex = row['rindex']
            lindex = row['lindex']

        update2 = context.sparql_context
        update2 += f"""
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
                          oldap:leftIndex ?lindex ;
                          oldap:rightIndex ?rindex .
                }}
                FILTER((?node != {self.__iri.toRdf}) && (?rindex >= {lindex}))
                BIND((?rindex + 2) AS ?nrindex)
            }}
        """
        try:
            self._con.transaction_update(update2)
        except OldapError:
            lprint(update2)
            self._con.transaction_abort()
            raise

        update3 = context.sparql_context
        update3 += f"""
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
                          oldap:leftIndex ?lindex ;
                          oldap:rightIndex ?rindex .
                }}
                FILTER((?node != {self.__iri.toRdf}) && (?lindex >= {rindex}))
                BIND((?lindex + 2) AS ?nlindex)
            }}
        """
        try:
            self._con.transaction_update(update3)
        except OldapError:
            lprint(update3)
            self._con.transaction_abort()
            raise

        try:
            jsonobj = self._con.transaction_query(query2)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            self._con.transaction_abort()
            raise OldapError('Insert_node_below_of failed')
        for row in res:
            self.__leftIndex = row['lindex']
            self.__rightIndex = row['rindex']

        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        self.clear_changeset()
        cache = CacheSingleton()
        cache.delete(self.__oldapList.oldapList_iri)

    def delete_node(self, indent: int = 0, indent_inc: int = 4) -> None:
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
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?node
        WHERE {{
            GRAPH {self.__graph}:lists {{
                ?node skos:broaderTransitive {self.__iri.toRdf}
            }}
        }}
        """
        self._con.transaction_start()

        try:
            jsonobj = self._con.transaction_query(query1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OldapErrorInconsistency(f'Cannot delete node with skos:broaderTransitive pointing to it!')

        query2 = context.sparql_context
        query2 += f"""
        SELECT ?lindex ?rindex
        WHERE {{
            GRAPH {self.__graph}:lists {{
                {self.__iri.toRdf}
                    oldap:leftIndex ?lindex ;
                    oldap:rightIndex ?rindex .
            }}
        }}
        """
        try:
            jsonobj = self._con.transaction_query(query2)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        lindex = 0
        rindex = 0
        if len(res) != 1:
            self._con.transaction_abort()
            raise OldapErrorInconsistency(f"Couldn't get node to delete")
        for r in res:
            lindex = r['lindex']
            rindex = r['rindex']

        update1 = context.sparql_context
        update1 += f"""
        DELETE 
        WHERE {{
            GRAPH {self.__graph}:lists {{
                {self.__iri.toRdf} ?p ?o
            }}
        }}
        """
        try:
            self._con.transaction_update(update1)
        except OldapError:
            self._con.transaction_abort()
            raise

        update2 = context.sparql_context
        update2 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?node
                    oldap:leftIndex ?lindex ;
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?node
                    oldap:leftIndex ?nlindex ;
            }}
        }}
        WHERE {{
            GRAPH {self.__graph}:lists {{
                ?node
                    oldap:leftIndex ?lindex ;
            }}
            FILTER(?lindex > {lindex})
            BIND((?lindex - 2) AS ?nlindex)
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
                ?node
                    oldap:rightIndex ?rindex ;
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?node
                    oldap:rightIndex ?nrindex ;
            }}
        }}
        WHERE {{
            GRAPH {self.__graph}:lists {{
                ?node
                    oldap:rightIndex ?rindex ;
            }}
            FILTER(?rindex > {rindex})
            BIND((?rindex - 2) AS ?nrindex)
        }}
        """
        try:
            self._con.transaction_update(update3)
        except OldapError:
            self._con.transaction_abort()
            raise

        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        self.clear_changeset()
        cache = CacheSingleton()
        cache.delete(self.__oldapList.oldapList_iri)

    def delete_node_recursively(self, indent: int = 0, indent_inc: int = 4) -> None:
        if self._con is None:
            raise OldapError("Cannot create: no connection")

        context = Context(name=self._con.context_name)
        timestamp = Xsd_dateTime.now()
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        #
        # first we get the node info, especialle leftIndex and rightIndex
        #
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?lindex ?rindex
        WHERE {{
            GRAPH {self.__graph}:lists {{
                {self.__iri.toRdf}
                    oldap:leftIndex ?lindex ;
                    oldap:rightIndex ?rindex .
            }}
        }}
        """
        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(query1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        lindex = 0
        rindex = 0
        if len(res) != 1:
            self._con.transaction_abort()
            raise OldapErrorInconsistency(f"Couldn't get node to delete")
        for r in res:
            lindex = r['lindex']
            rindex = r['rindex']

        #
        # now delete the node and all nodes below
        #
        update1 = context.sparql_context
        update1 += f"""        
        DELETE {{
            ?subject ?p ?o
        }}
        WHERE {{
            GRAPH test:lists {{
                ?subject oldap:leftIndex ?leftIndex ;
        	        oldap:rightIndex ?rightIndex ;
        	        skos:inScheme {self.__oldapList.oldapList_iri.toRdf} ;
        	        ?p ?o .
    	        FILTER (?leftIndex >= {int(lindex)} && ?rightIndex <= {int(rindex)})
            }}
        }}
        """
        try:
            self._con.transaction_update(update1)
        except OldapError:
            print(update1)
            self._con.transaction_abort()
            raise

        #
        # now adjust all leftIndex'es of the nodes "to the right"
        #
        diff: Xsd_integer = rindex - lindex + 1
        update2 = context.sparql_context
        update2 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?oldLeftIndex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?newLeftIndex .
            }}
        }}
        WHERE {{
            ?subject oldap:leftIndex ?oldLeftIndex ;
                skos:inScheme {self.__oldapList.oldapList_iri.toRdf} .
            FILTER(?oldLeftIndex > {int(lindex)})
            BIND(?oldLeftIndex - {int(diff)} AS ?newLeftIndex)
        }}
        """
        try:
            self._con.transaction_update(update2)
        except OldapError:
            self._con.transaction_abort()
            raise

        #
        # now adjust all rightIndex'es of the nodes "to the right"
        #
        update3 = context.sparql_context
        update3 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:rightIndex ?oldRightIndex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:rightIndex ?newRightIndex .
            }}
        }}
        WHERE {{
            ?subject oldap:rightIndex ?oldRightIndex ;
                skos:inScheme {self.__oldapList.oldapList_iri.toRdf} .
            FILTER(?oldRightIndex > {int(rindex)})
            BIND(?oldRightIndex - {int(diff)} AS ?newRightIndex)
        }}
        """
        try:
            self._con.transaction_update(update3)
        except OldapError:
            self._con.transaction_abort()
            raise

        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        cache = CacheSingleton()
        cache.delete(self.__oldapList.oldapList_iri)


    def move_node_below(self, con: IConnection, target: Self, indent: int = 0, indent_inc: int = 4):
        if self._con is None:
            raise OldapError("Cannot create: no connection")

        context = Context(name=self._con.context_name)
        timestamp = Xsd_dateTime.now()
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        #
        # first we get the node info, especially leftIndex and rightIndex
        #
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?lindex ?rindex ?parent_iri
        WHERE {{
            GRAPH {self.__graph}:lists {{
                {self.__iri.toRdf}
                    oldap:leftIndex ?lindex ;
                    oldap:rightIndex ?rindex ;
                OPTIONAL {{
                    {self.__iri.toRdf} skos:broaderTransitive ?parent_iri .
                }}
            }}
        }}
        """
        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(query1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        moving_lindex: int = 0
        moving_rindex: int = 0
        moving_parent_iri: Iri | None = None
        if len(res) != 1:
            self._con.transaction_abort()
            raise OldapErrorInconsistency(f"Couldn't get node to delete")
        for r in res:
            moving_lindex = r['lindex']
            moving_rindex = r['rindex']
            moving_parent_iri = r.get('parent_iri')

        #
        # now we the get information of the target node
        #
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?lindex ?rindex ?parent_iri
        WHERE {{
            GRAPH {self.__graph}:lists {{
                {target.__iri.toRdf}
                    oldap:leftIndex ?lindex ;
                    oldap:rightIndex ?rindex ;
            }}
        }}
        """
        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(query1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        target_lindex: int = 0
        target_rindex: int = 0
        if len(res) != 1:
            self._con.transaction_abort()
            raise OldapErrorInconsistency(f"Couldn't get target node of move below")
        for r in res:
            target_lindex = r['lindex']
            target_rindex = r['rindex']

        #
        # Set oldap:leftIndex and oldap:rightIndex of all nodes to be moved to the negative value
        #
        update1 = context.sparql_context
        update1 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?oldLeftIndex .
                ?subject oldap:rightIndex ?oldRightIndex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?newLeftIndex .
                ?subject oldap:rightIndex ?newRightIndex .
            }}
        }}
        WHERE {{
            ?subject oldap:leftIndex ?oldLeftIndex ;
                oldap:rightIndex ?oldRightIndex ;
                skos:inScheme {self.__oldapList.oldapList_iri.toRdf} .
            FILTER (?oldLeftIndex >= {int(moving_lindex)} && ?oldRightIndex <= {int(moving_rindex)})
            BIND(-?oldLeftIndex AS ?newLeftIndex)
            BIND(-?oldRightIndex AS ?newRightIndex)
        }}
        """
        try:
            self._con.transaction_update(update1)
        except OldapError:
            self._con.transaction_abort()
            raise

        #
        # set the new left index
        #
        diff1 = moving_rindex - moving_lindex + 1
        if moving_rindex < target_lindex:
            # moving to the right
            filter = f'FILTER (?oldLeftIndex > {int(moving_rindex)} && ?oldLeftIndex <= {int(target_lindex)})'
        else:
            # moving to the left
            diff1 = -diff1
            filter = f'FILTER (?oldLeftIndex > {int(target_rindex)} && ?oldLeftIndex <= {int(moving_rindex)})'

        update2 = context.sparql_context
        update2 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?oldLeftIndex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?newLeftIndex .
            }}
        }}
        WHERE {{
            ?subject oldap:leftIndex ?oldLeftIndex ;
                skos:inScheme {self.__oldapList.oldapList_iri.toRdf} .
            {filter}
            BIND(?oldLeftIndex - {int(diff1)} AS ?newLeftIndex)
        }}
        """
        try:
            self._con.transaction_update(update2)
        except OldapError:
            self._con.transaction_abort()
            raise

        #
        # set the right index
        #
        if moving_rindex < target_lindex:
            # moving to the right
            filter = f'FILTER (?oldRightIndex > {int(moving_rindex)} && ?oldRightIndex < {int(target_rindex)})'
        else:
            # moving to the left
            filter = f'FILTER (?oldRightIndex >= {int(target_rindex)} && ?oldLeftIndex < {int(moving_lindex)})'
        update3 = context.sparql_context
        update3 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:rightIndex ?oldRightIndex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:rightIndex ?newRightIndex .
            }}
        }}
        WHERE {{
            ?subject oldap:rightIndex ?oldRightIndex ;
                oldap:rightIndex ?oldLeftIndex ;
                skos:inScheme {self.__oldapList.oldapList_iri.toRdf} .
            {filter}
            BIND(?oldRightIndex - {int(diff1)} AS ?newRightIndex)
        }}
        """
        try:
            self._con.transaction_update(update3)
        except OldapError:
            self._con.transaction_abort()
            raise


        #
        # Correct leftIndex and rightIndex of the moved nodes
        #
        if moving_rindex < target_lindex:
            diff2 = target_rindex - moving_lindex -diff1
        else:
            diff2 = target_rindex - moving_lindex
        update4 = context.sparql_context
        update4 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?oldLeftIndex .
                ?subject oldap:rightIndex ?oldRightIndex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?newLeftIndex .
                ?subject oldap:rightIndex ?newRightIndex .
            }}
        }}
        WHERE {{
            ?subject oldap:leftIndex ?oldLeftIndex ;
                oldap:rightIndex ?oldRightIndex .
            FILTER(?oldLeftIndex < 0)
            BIND(-?oldLeftIndex + {int(diff2)} AS ?newLeftIndex)
            BIND(-?oldRightIndex + {int(diff2)} AS ?newRightIndex)
        }}
        """
        try:
            self._con.transaction_update(update4)
        except OldapError:
            self._con.transaction_abort()
            raise

        #
        # update parent (skos:broaderTransitive)
        #
        update5 = context.sparql_context
        if moving_parent_iri:
            update5 += f"""
            DELETE {{
                GRAPH {self.__graph}:lists {{
                    ?subject skos:broaderTransitive ?parent .
                }}
            }}
            """
        update5 += f"""
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject skos:broaderTransitive {target.__iri.toRdf} .
            }}
        }}
        WHERE {{
            BIND({self.__iri.toRdf} AS ?subject)
            OPTIONAL {{
                ?subject skos:broaderTransitive ?parent .
            }}
        }}
        """
        try:
            self._con.transaction_update(update5)
        except OldapError:
            print(update5)
            self._con.transaction_abort()
            raise

        #
        # commit
        #
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        cache = CacheSingleton()
        cache.delete(self.__oldapList.oldapList_iri)

    def move_node_right_of(self, con: IConnection, leftnode: Self, indent: int = 0, indent_inc: int = 4):
        if self._con is None:
            raise OldapError("Cannot create: no connection")

        context = Context(name=self._con.context_name)
        timestamp = Xsd_dateTime.now()
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        #
        # first we get the node info, especially leftIndex and rightIndex
        #
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?lindex ?rindex ?parent_iri
        WHERE {{
            GRAPH {self.__graph}:lists {{
                {self.__iri.toRdf}
                    oldap:leftIndex ?lindex ;
                    oldap:rightIndex ?rindex .
                OPTIONAL {{
                    {self.__iri.toRdf} skos:broaderTransitive ?parent_iri .
                }}
            }}
        }}
        """
        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(query1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        moving_lindex: int = 0
        moving_rindex: int = 0
        moving_parent_iri: Iri | None = None
        if len(res) != 1:
            self._con.transaction_abort()
            raise OldapErrorInconsistency(f"Couldn't get node to delete")
        for r in res:
            moving_lindex = r['lindex']
            moving_rindex = r['rindex']
            moving_parent_iri = r.get('parent_iri')

        #
        # now we the get information of the left node
        #
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?lindex ?rindex ?parent_iri
        WHERE {{
            GRAPH {self.__graph}:lists {{
                {leftnode.__iri.toRdf}
                    oldap:leftIndex ?lindex ;
                    oldap:rightIndex ?rindex ;
                OPTIONAL {{
                    {leftnode.__iri.toRdf} skos:broaderTransitive ?parent_iri .
                }}
            }}
        }}
        """
        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(query1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        left_lindex: int = 0
        left_rindex: int = 0
        left_parent_iri: Iri | None = None
        if len(res) != 1:
            self._con.transaction_abort()
            raise OldapErrorInconsistency(f'Could not get the "left"-node')
        for r in res:
            left_lindex = r['lindex']
            left_rindex = r['rindex']
            left_parent_iri = r.get('parent_iri')

        #
        # Set oldap:leftIndex and oldap:rightIndex of all nodes to be moved to the negative value
        #
        update1 = context.sparql_context
        update1 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?oldLeftIndex .
                ?subject oldap:rightIndex ?oldRightIndex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?newLeftIndex .
                ?subject oldap:rightIndex ?newRightIndex .
            }}
        }}
        WHERE {{
            ?subject oldap:leftIndex ?oldLeftIndex ;
                oldap:rightIndex ?oldRightIndex ;
                skos:inScheme {self.__oldapList.oldapList_iri.toRdf} .
            FILTER (?oldLeftIndex >= {int(moving_lindex)} && ?oldRightIndex <= {int(moving_rindex)})
            BIND(-?oldLeftIndex AS ?newLeftIndex)
            BIND(-?oldRightIndex AS ?newRightIndex)
        }}
        """
        try:
            self._con.transaction_update(update1)
        except OldapError:
            self._con.transaction_abort()
            raise

        #
        # set the new left index
        #
        diff1 = moving_rindex - moving_lindex + 1
        if moving_rindex < left_lindex:
            # moving to the right
            filter = f'FILTER (?oldLeftIndex > {int(moving_rindex)} && ?oldLeftIndex <= {int(left_rindex)})'
        else:
            # moving to the left
            diff1 = -diff1
            filter = f'FILTER (?oldLeftIndex > {int(left_rindex)} && ?oldLeftIndex < {int(moving_rindex)})'

        update2 = context.sparql_context
        update2 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?oldLeftIndex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?newLeftIndex .
            }}
        }}
        WHERE {{
            ?subject oldap:leftIndex ?oldLeftIndex ;
                skos:inScheme {self.__oldapList.oldapList_iri.toRdf} .
            {filter}
            BIND(?oldLeftIndex - {int(diff1)} AS ?newLeftIndex)
        }}
        """
        try:
            self._con.transaction_update(update2)
        except OldapError:
            self._con.transaction_abort()
            raise

        #
        # set the right index
        #
        if moving_rindex < left_lindex:
            # moving to the right
            filter = f'FILTER (?oldRightIndex > {int(moving_rindex)} && ?oldRightIndex <= {int(left_rindex)})'
        else:
            # moving to the left
            filter = f'FILTER (?oldRightIndex > {int(left_rindex)} && ?oldLeftIndex < {int(moving_lindex)})'
        update3 = context.sparql_context
        update3 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:rightIndex ?oldRightIndex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:rightIndex ?newRightIndex .
            }}
        }}
        WHERE {{
            ?subject oldap:rightIndex ?oldRightIndex ;
                oldap:rightIndex ?oldLeftIndex ;
                skos:inScheme {self.__oldapList.oldapList_iri.toRdf} .
            {filter}
            BIND(?oldRightIndex - {int(diff1)} AS ?newRightIndex)
        }}
        """
        try:
            self._con.transaction_update(update3)
        except OldapError:
            self._con.transaction_abort()
            raise


        #
        # Correct leftIndex and rightIndex of the moved nodes
        #
        if moving_rindex < left_lindex:
            diff2 = left_rindex - moving_rindex
        else:
            diff2 = left_rindex - moving_lindex + 1
        update4 = context.sparql_context
        update4 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?oldLeftIndex .
                ?subject oldap:rightIndex ?oldRightIndex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?newLeftIndex .
                ?subject oldap:rightIndex ?newRightIndex .
            }}
        }}
        WHERE {{
            ?subject oldap:leftIndex ?oldLeftIndex ;
                oldap:rightIndex ?oldRightIndex .
            FILTER(?oldLeftIndex < 0)
            BIND(-?oldLeftIndex + {int(diff2)} AS ?newLeftIndex)
            BIND(-?oldRightIndex + {int(diff2)} AS ?newRightIndex)
        }}
        """
        try:
            self._con.transaction_update(update4)
        except OldapError:
            self._con.transaction_abort()
            raise

        update5 = context.sparql_context
        if moving_parent_iri:
            update5 += f"""
            DELETE {{
                GRAPH {self.__graph}:lists {{
                    ?subject skos:broaderTransitive ?parent .
                }}
            }}
        """
        if left_parent_iri:
            update5 += f"""
            INSERT {{
                GRAPH {self.__graph}:lists {{
                    ?subject skos:broaderTransitive {left_parent_iri.toRdf} .
                }}
            }}
        """
        update5 += f"""
        WHERE {{
            BIND({self.__iri.toRdf} AS ?subject)
            ?subject skos:broaderTransitive ?parent .
        }}
        """
        if moving_parent_iri or left_parent_iri:
            try:
                self._con.transaction_update(update5)
            except OldapError:
                print(update5)
                self._con.transaction_abort()
                raise

        #
        # commit
        #
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        cache = CacheSingleton()
        cache.delete(self.__oldapList.oldapList_iri)

    def move_node_left_of(self, con: IConnection, rightnode: Self, indent: int = 0, indent_inc: int = 4):
        if self._con is None:
            raise OldapError("Cannot create: no connection")

        context = Context(name=self._con.context_name)
        timestamp = Xsd_dateTime.now()
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        #
        # first we get the node info, especially leftIndex and rightIndex
        #
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?lindex ?rindex ?parent_iri
        WHERE {{
            GRAPH {self.__graph}:lists {{
                {self.__iri.toRdf}
                    oldap:leftIndex ?lindex ;
                    oldap:rightIndex ?rindex .
                OPTIONAL {{
                    {self.__iri.toRdf} skos:broaderTransitive ?parent_iri .
                }}
            }}
        }}
        """
        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(query1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        moving_lindex: int = 0
        moving_rindex: int = 0
        moving_parent_iri: Iri | None = None
        if len(res) != 1:
            self._con.transaction_abort()
            raise OldapErrorInconsistency(f"Couldn't get node to delete")
        for r in res:
            moving_lindex = r['lindex']
            moving_rindex = r['rindex']
            moving_parent_iri = r.get('parent_iri')

        #
        # now we the get information of the right node
        #
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?lindex ?rindex ?parent_iri
        WHERE {{
            GRAPH {self.__graph}:lists {{
                {rightnode.__iri.toRdf}
                    oldap:leftIndex ?lindex ;
                    oldap:rightIndex ?rindex ;
                OPTIONAL {{
                    {rightnode.__iri.toRdf} skos:broaderTransitive ?parent_iri .
                }}
            }}
        }}
        """
        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(query1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        right_lindex: int = 0
        right_rindex: int = 0
        right_parent_iri: Iri | None = None
        if len(res) != 1:
            self._con.transaction_abort()
            raise OldapErrorInconsistency(f'Could not get the "left"-node')
        for r in res:
            right_lindex = r['lindex']
            right_rindex = r['rindex']
            right_parent_iri = r.get('parent_iri')

        #
        # Set oldap:leftIndex and oldap:rightIndex of all nodes to be moved to the negative value
        #
        update1 = context.sparql_context
        update1 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?oldLeftIndex .
                ?subject oldap:rightIndex ?oldRightIndex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?newLeftIndex .
                ?subject oldap:rightIndex ?newRightIndex .
            }}
        }}
        WHERE {{
            ?subject oldap:leftIndex ?oldLeftIndex ;
                oldap:rightIndex ?oldRightIndex ;
                skos:inScheme {self.__oldapList.oldapList_iri.toRdf} .
            FILTER (?oldLeftIndex >= {int(moving_lindex)} && ?oldRightIndex <= {int(moving_rindex)})
            BIND(-?oldLeftIndex AS ?newLeftIndex)
            BIND(-?oldRightIndex AS ?newRightIndex)
        }}
        """
        try:
            self._con.transaction_update(update1)
        except OldapError:
            self._con.transaction_abort()
            raise

        #
        # set the new left index
        #
        diff1 = moving_rindex - moving_lindex + 1
        if moving_rindex < right_lindex:
            # moving to the right
            filter = f'FILTER (?oldLeftIndex > {int(moving_rindex)} && ?oldLeftIndex < {int(right_lindex)})'
        else:
            # moving to the left
            diff1 = -diff1
            filter = f'FILTER (?oldLeftIndex >= {int(right_lindex)} && ?oldLeftIndex < {int(moving_lindex)})'

        update2 = context.sparql_context
        update2 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?oldLeftIndex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?newLeftIndex .
            }}
        }}
        WHERE {{
            ?subject oldap:leftIndex ?oldLeftIndex ;
                oldap:rightIndex ?oldRightIndex ;
                skos:inScheme {self.__oldapList.oldapList_iri.toRdf} .
            {filter}
            BIND(?oldLeftIndex - {int(diff1)} AS ?newLeftIndex)
        }}
        """
        try:
            self._con.transaction_update(update2)
        except OldapError:
            self._con.transaction_abort()
            raise

        #
        # set the right index
        #
        if moving_rindex < right_lindex:
            # moving to the right
            filter = f'FILTER (?oldRightIndex > {int(moving_rindex)} && ?oldRightIndex < {int(right_lindex)})'
        else:
            # moving to the left
            filter = f'FILTER (?oldLeftIndex >= {int(right_lindex)} && ?oldRightIndex < {int(moving_lindex)})'
        update3 = context.sparql_context
        update3 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:rightIndex ?oldRightIndex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:rightIndex ?newRightIndex .
            }}
        }}
        WHERE {{
            ?subject oldap:rightIndex ?oldRightIndex ;
                oldap:leftIndex ?oldLeftIndex ;
                skos:inScheme {self.__oldapList.oldapList_iri.toRdf} .
            {filter}
            BIND(?oldRightIndex - {int(diff1)} AS ?newRightIndex)
        }}
        """
        try:
            self._con.transaction_update(update3)
        except OldapError:
            self._con.transaction_abort()
            raise


        #
        # Correct leftIndex and rightIndex of the moved nodes
        #
        if moving_rindex < right_lindex:
            diff2 = right_lindex - moving_rindex - 1
        else:
            diff2 = right_lindex - moving_lindex
        update4 = context.sparql_context
        update4 += f"""
        DELETE {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?oldLeftIndex .
                ?subject oldap:rightIndex ?oldRightIndex .
            }}
        }}
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?newLeftIndex .
                ?subject oldap:rightIndex ?newRightIndex .
            }}
        }}
        WHERE {{
            ?subject oldap:leftIndex ?oldLeftIndex ;
                oldap:rightIndex ?oldRightIndex .
            FILTER(?oldLeftIndex < 0)
            BIND(-?oldLeftIndex + {int(diff2)} AS ?newLeftIndex)
            BIND(-?oldRightIndex + {int(diff2)} AS ?newRightIndex)
        }}
        """
        try:
            self._con.transaction_update(update4)
        except OldapError:
            self._con.transaction_abort()
            raise

        update5 = context.sparql_context
        if moving_parent_iri:
            update5 += f"""
            DELETE {{
                GRAPH {self.__graph}:lists {{
                    ?subject skos:broaderTransitive ?parent .
                }}
            }}
        """
        if right_parent_iri:
            update5 += f"""
            INSERT {{
                GRAPH {self.__graph}:lists {{
                    ?subject skos:broaderTransitive {right_parent_iri.toRdf} .
                }}
            }}
        """
        update5 += f"""
        WHERE {{
            BIND({self.__iri.toRdf} AS ?subject)
            ?subject skos:broaderTransitive ?parent .
        }}
        """
        if moving_parent_iri or right_parent_iri:
            try:
                self._con.transaction_update(update5)
            except OldapError:
                print(update5)
                self._con.transaction_abort()
                raise

        #
        # commit
        #
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        cache = CacheSingleton()
        cache.delete(self.__oldapList.oldapList_iri)

    @staticmethod
    def search(con: IConnection,
               oldapList: OldapList,
               id: Xsd_string | str | None = None,
               prefLabel: Xsd_string | str | None = None,
               definition: str | None = None,
               exactMatch: bool = False) -> list[Iri]:
        id = Xsd_string(id)
        prefLabel = Xsd_string(prefLabel)
        definition = Xsd_string(definition)
        context = Context(name=con.context_name)
        graph = oldapList.project.projectShortName

        prefLabel = Xsd_string(prefLabel)
        sparql = context.sparql_context
        sparql += 'SELECT DISTINCT ?node\n'
        sparql += f'FROM {graph}:lists\n'
        sparql += 'WHERE {\n'
        sparql += f'   ?node a {oldapList.node_class_iri} ;\n'
        sparql += f'       skos:inScheme {oldapList.oldapList_iri.toRdf} .\n'
        if prefLabel:
            sparql += '   ?node skos:prefLabel ?label .\n'
        if definition:
            sparql += '   ?node skos:definition ?definition .\n'
        if id:
            if exactMatch:
                sparql += f'    FILTER(STRAFTER(STR(?node), "#") = "{Xsd_string.escaping(id.value)}")\n'
            else:
                sparql += f'    FILTER(CONTAINS(STRAFTER(STR(?node), "#"), "{Xsd_string.escaping(id.value)}"))\n'
        if prefLabel:
            if prefLabel.lang:
                if exactMatch:
                    sparql += f'   FILTER(?label = {prefLabel.toRdf})\n'
                else:
                    sparql += f'   FILTER(CONTAINS(?label, {prefLabel.toRdf}))\n'
            else:
                if exactMatch:
                    sparql += f'   FILTER(STR(?label) = "{Xsd_string.escaping(prefLabel.value)}")\n'
                else:
                    sparql += f'   FILTER(CONTAINS(STR(?label), "{Xsd_string.escaping(prefLabel.value)}"))\n'
        if definition:
            if definition.lang:
                if exactMatch:
                    sparql += f'   FILTER(?definition = {definition.toRdf})\n'
                else:
                    sparql += f'   FILTER(CONTAINS(?definition, {definition.toRdf}))\n'
            else:
                if exactMatch:
                    sparql += f'   FILTER(STR(?definition) = "{Xsd_string.escaping(definition.value)}")\n'
                else:
                    sparql += f'   FILTER(CONTAINS(STR(?definition), "{Xsd_string.escaping(definition.value)}"))\n'
        sparql += '}\n'

        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        lists: list[Iri] = []
        if len(res) > 0:
            for r in res:
                lists.append(r['node'])
        return lists


