from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from typing import Self, Any

from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.oldaplistnodeattr import OldapListNodeAttr
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission, \
    OldapErrorAlreadyExists, OldapErrorInconsistency, OldapErrorNotFound, OldapErrorUpdateFailed, OldapErrorInUse
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.helpers.tools import lprint
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string
#if TYPE_CHECKING:
#    from oldaplib.src.oldaplist import OldapList

OldapListNodeAttrTypes = int | Xsd_NCName | LangString | Iri | None


@dataclass
class OldapListNodeAttrChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: OldapListNodeAttrTypes
    action: Action


@serializer
class OldapListNode(Model):
    """
    Represents a node in an ordered list, with attributes and behaviors specific to managing and maintaining
    relations within a hierarchical data structure. This class encapsulates details pertaining to the project,
    graph structure, and metadata associated with each node. It also facilitates permissions checking and supports
    deep copying for instances.

    Detailed description of attributes, including their roles within hierarchical structures, supports serialization,
    and ensures object uniqueness by comparing key attributes.

    :ivar oldapListNodeId: Unique identifier of the node within the ordered list.
    :type oldapListNodeId: str
    :ivar prefLabel: Preferred label for the node.
    :type prefLabel: str
    :ivar definition: Definition or description for the node.
    :type definition: str
    """
    __projectShortName: Xsd_NCName
    __projectIri: Iri
    __oldapListId: Xsd_NCName
    __oldapListIri: Iri
    __node_classIri: Iri

    __graph: Xsd_NCName
    __iri: Iri | None
    __nodes: list[Self] | None
    __leftIndex: Xsd_integer | None
    __rightIndex: Xsd_integer | None

    __slots__ = ('oldapListNodeId', 'prefLabel', 'definition')

    def __init__(self, *,
                 con: IConnection,
                 projectShortName: Xsd_NCName,  # Coming from OldapList as **OldapList.info
                 projectIri: Iri,  # Coming from OldapList as **OldapList.info
                 oldapListId: Xsd_NCName,  # Coming from OldapList as **OldapList.info
                 oldapListIri: Iri,  # Coming from OldapList as **OldapList.info
                 node_classIri: Iri,  # Coming from OldapList as **OldapList.info
                 creator: Iri | None = None,  # INTERNAL USE ONLY!
                 created: Xsd_dateTime | None = None,  # INTERNAL USE ONLY!
                 contributor: Iri | None = None,  # INTERNAL USE ONLY!
                 modified: Xsd_dateTime | None = None,  # INTERNAL USE ONLY!
                 leftIndex: Xsd_integer | None = None,
                 rightIndex: Xsd_integer | None = None,
                 defaultLabel: bool = True,
                 nodes: list[Self] | None = None,
                 validate: bool = False,
                 **kwargs):
        """
        Initializes an instance with various parameters for defining and interacting
        with a node structure.

        The constructor initializes an object with attributes related to its
        identity, hierarchy, and semantics. It configures the node object while
        considering its internal and external relationships, enabling its use
        within a structured project context. Optional parameters allow customization
        of the node's runtime behavior.

        :param con: Connection to the server
        :type con: IConnection
        :param projectShortName: Shortname of the project (**oldaplist.info)
        :type projectShortName: Xsd_NCName
        :param projectIri: IRI of the project (**oldaplist.info)
        :type projectIri: Iri
        :param oldapListId: ID of the list (**oldaplist.info)
        :type oldapListId: Xsd_NCName
        :param oldapListIri: IRI of the list (**oldaplist.info)
        :type oldapListIri: Iri
        :param node_classIri: IRI of the node class, representing "node a node_classIri ."
        :type node_classIri: Iri
        :param leftIndex: Left index of the node
        :type leftIndex: Xsd_integer | None
        :param rightIndex: Right index of the node
        :type rightIndex: Xsd_integer | None
        :param defaultLabel: Flag indicating whether to use nodeId as the default
            label if no label is provided
        :type defaultLabel: bool
        :param nodes: Subnodes of this node; primarily for use by the serializer
        :type nodes: list[Self] | None
        :param validate: Flag to enable or disable validation
        :type validate: bool
        :param kwargs: Additional keyword arguments for customization
        """
        super().__init__(connection=con,
                         creator=creator,
                         created=created,
                         contributor=contributor,
                         modified=modified,
                         validate=validate)
        self.__projectShortName = projectShortName
        self.__projectIri = projectIri
        self.__oldapListId = oldapListId
        self.__oldapListIri = oldapListIri
        self.__node_classIri = node_classIri

        self.__graph = self.__projectShortName

        self.set_attributes(kwargs, OldapListNodeAttr)
        if self._attributes.get(OldapListNodeAttr.PREF_LABEL) is None and defaultLabel:
            self._attributes[OldapListNodeAttr.PREF_LABEL] = LangString(str(self._attributes[OldapListNodeAttr.OLDAPLISTNODE_ID]))

        list_node_prefix = Xsd_NCName("L-") + self.__oldapListId
        self.__iri = Iri.fromPrefixFragment(list_node_prefix,
                                            self._attributes[OldapListNodeAttr.OLDAPLISTNODE_ID],
                                            validate=False)

        self.__leftIndex = leftIndex
        self.__rightIndex = rightIndex
        self.__nodes = nodes

        #
        # create all the attributes of the class according to the OldapListAttr definition
        #
        for attr in OldapListNodeAttr:
            setattr(OldapListNode, attr.value.fragment, property(
                partial(OldapListNode._get_value, attr=attr),
                partial(OldapListNode._set_value, attr=attr),
                partial(OldapListNode._del_value, attr=attr)))

    def _as_dict(self):
        return {x.fragment: y for x, y in self._attributes.items()} | super()._as_dict() | {
            'projectShortName': self.__projectShortName,
            'projectIri': self.__projectIri,
            'oldapListId': self.__oldapListId,
            'oldapListIri': self.__oldapListIri,
            'node_classIri': self.__node_classIri,
            'leftIndex': self.__leftIndex,
            'rightIndex': self.__rightIndex,
            'nodes': self.__nodes
        }

    def __eq__(self, other: Self) -> bool:
        return self.__oldapListId == other.__oldapListId and \
            self.__oldapListIri == other.__oldapListIri and \
            self.__node_classIri == other.__node_classIri and \
            self.__projectIri == other.__projectIri and \
            self.__projectShortName == other.__projectShortName and \
            self.__leftIndex == other.__leftIndex and \
            self.__rightIndex == other.__rightIndex and \
            self.__graph == other.__graph and \
            self.prefLabel == other.prefLabel and \
            self.definition == other.definition


    def check_for_permissions(self) -> (bool, str):
        #
        # First we check if the logged-in user ("actor") has the permission to create a ListNode for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('oldap:SystemProject'))
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            #
            # user has root privileges!
            #
            return True, "OK – IS ROOT"
        else: # TODO: totally wrong what's being done below!!!
            if len(actor.inProject) == 0:
                return False, f'Actor has no ADMIN_LISTS permission for project "{self.__projectIri}".'
            if not actor.inProject.get(self.__projectIri):
                return False, f'Actor has no ADMIN_LISTS permission.'
            if AdminPermission.ADMIN_LISTS not in actor.inProject.get(self.__projectIri):
                return False, f'Actor has no ADMIN_LISTS permission for project "{self.__projectIri}".'
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
        instance.__projectShortName = deepcopy(self.__projectShortName, memo)
        instance.__projectIri = deepcopy(self.__projectIri, memo)
        instance.__oldapListId = deepcopy(self.__oldapListId, memo)
        instance.__oldapListIri = deepcopy(self.__oldapListIri, memo)
        instance.__node_classIri = deepcopy(self.__node_classIri, memo)
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
             projectShortName: Xsd_NCName,
             projectIri: Iri,
             oldapListId: Xsd_NCName,
             oldapListIri: Iri,
             node_classIri: Iri,
             oldapListNodeId: Xsd_NCName | str):
        """
        Reads and initializes an instance of the class using information retrieved from
        a graph database. This method queries a SPARQL endpoint to gather properties
        and values associated with a specific node, identified by its IRI. It processes
        the query results and constructs an object with attributes populated based on
        retrieved data. If the specified node does not exist in the database, an error
        is raised.

        :param con: Connection object to the SPARQL endpoint used to execute queries.
        :type con: IConnection
        :param projectShortName: Short name of the project to identify the graph.
        :type projectShortName: Xsd_NCName
        :param projectIri: The IRI identifying the project in the data store.
        :type projectIri: Iri
        :param oldapListId: Identifier of the list to which the node belongs.
        :type oldapListId: Xsd_NCName
        :param oldapListIri: The IRI of the list to which the node belongs.
        :type oldapListIri: Iri
        :param node_classIri: The IRI representing the class of the node in the ontology.
        :type node_classIri: Iri
        :param oldapListNodeId: The identifier of the specific node in the list. Can be a string or an Xsd_NCName.
        :type oldapListNodeId: Xsd_NCName | str
        :return: An instance of the class populated with data retrieved for the specified node.
        :rtype: cls
        :raises OldapErrorNotFound: If the node cannot be found in the graph database.
        """
        oldapListNodeId = Xsd_NCName(oldapListNodeId, validate=True)

        list_node_prefix = Xsd_NCName("L-", validate=False) + oldapListId
        node_iri = Iri.fromPrefixFragment(list_node_prefix, oldapListNodeId, validate=False)

        context = Context(name=con.context_name)
        graph = projectShortName
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
            prefLabel.clear_changeset()
            prefLabel.set_notifier(cls.notifier, Xsd_QName(OldapListNodeAttr.PREF_LABEL.value))
        if definition:
            definition.clear_changeset()
            definition.set_notifier(cls.notifier, Xsd_QName(OldapListNodeAttr.DEFINITION.value))
        return cls(con=con,
                   projectShortName=projectShortName,
                   projectIri=projectIri,
                   oldapListId=oldapListId,
                   oldapListIri=oldapListIri,
                   node_classIri=node_classIri,
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
        """
        Creates a root node in the specified list within the context of the given graph. This method
        ensures all necessary conditions are fulfilled before creating the node. It verifies if the
        logged-in user has the necessary permissions and validates that no existing root node is
        present in the targeted list. The newly created root node is populated with initial attributes,
        such as left and right indices, timestamps, and other metadata, and committed to the data
        store. If a root node already exists, the operation is aborted and an error is raised.

        :param indent: An integer value used to define the base indentation level. Default is 0.
        :param indent_inc: An integer that specifies the increase in indentation for every nesting
            level. Default is 4.
        :return: None

        :raises OldapErrorNoPermission: If the logged-in user does not have the necessary permissions.
        :raises OldapErrorAlreadyExists: If a root node already exists in the targeted list.
        :raises OldapErrorUpdateFailed: If the update of the root node failed.
        :raises OldapError: If an unexpected error occurs during the operation.
        """
        OldapError
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
        # Sparql to check if list has already any nodes. If so, root node creation is not possible!
        #
        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?list
        FROM {self.__graph}:lists
        WHERE {{
            ?listnode a {self.__node_classIri} .
            ?listnode skos:inScheme {self.__oldapListIri.toRdf}
        }}
        """

        sparql2 = context.sparql_context
        sparql2 += f'{blank:{indent * indent_inc}}INSERT DATA {{'
        sparql2 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        sparql2 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__iri.toRdf} a {self.__node_classIri}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:inScheme {self.__oldapListIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:leftIndex {self.__leftIndex.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:rightIndex {self.__rightIndex.toRdf}'
        if self.prefLabel:
            sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.PREF_LABEL.value} {self.prefLabel.toRdf}'
        if self.definition:
            sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.DEFINITION.value} {self.definition.toRdf}'
        sparql2 += f' .\n{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql2 += f'{blank:{indent * indent_inc}}}}\n'

        self._con.transaction_start()
        jsonobj = self.safe_query(sparql1)
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'A root node for "{self.__oldapListIri}" already exists')

        self.safe_update(sparql2)
        self.safe_commit()
        cache = CacheSingletonRedis()
        cache.delete(self.__oldapListIri)

    def update(self, indent: int = 0, indent_inc: int = 4):
        """
        Updates an entity within the system by ensuring that all necessary changes are
        applied and associated permissions are respected. The method performs updates
        on fields specified in the changeset, along with transaction management to
        maintain data consistency. Additionally, timestamps and modification tracking
        are updated to reflect the changes made.

        :param indent: The initial indentation level for formatting the output.
        :param indent_inc: The increment value for indentation levels.
        :return: None
        :raises OldapErrorNoPermission: Raised if the user does not have the necessary permissions to perform the update.
        :raises OldapErrorUpdateFailed: Raised if the update fails due to mismatched modification timestamps.
        :raises OldapError: Raised when any transaction-related error occurs during the update process.
        """
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
        self.safe_commit()
        self._modified = timestamp
        self._contributor = self._con.userIri  # TODO: move creator, created etc. to Model!
        self.clear_changeset()
        cache = CacheSingletonRedis()
        cache.delete(self.__oldapListIri)

    def insert_node_right_of(self, leftnode: Self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Inserts a new node to the right of a given left node in a controlled hierarchical structure.
        This operation involves multiple SPARQL updates and queries to maintain the consistency
        of left and right index values for nodes in the hierarchy, ensuring proper ordering
        and relationships between nodes.

        :param leftnode: The node to the left of which the new node will be inserted.
        :type leftnode: Self
        :param indent: Indentation level for the SPARQL query formatting. Default is 0.
        :type indent: int
        :param indent_inc: Increment of indentation per level for SPARQL query formatting. Default is 4.
        :type indent_inc: int
        :return: None. This function modifies the data structure and does not return any values.
        :rtype: None
        :raises OldapError: If the operation fails for any generic reason.
        :raises OldapErrorNoPermission: If the current user lacks permission to insert nodes.
        """

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
        update1 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__iri.toRdf} a {self.__node_classIri}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:inScheme {self.__oldapListIri.toRdf}'
        if self.prefLabel:
            update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.PREF_LABEL.value} {self.prefLabel.toRdf}'
        if self.definition:
            update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.DEFINITION.value} {self.definition.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:leftIndex ?nlindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:rightIndex ?nrindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:broader ?parent_node'
        update1 += f' .\n{blank:{(indent + 1) * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}WHERE {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f' \n{blank:{(indent + 2) * indent_inc}}{leftnode.iri.toRdf} oldap:rightIndex ?rindex'
        update1 += f' ;\n{blank:{(indent + 2) * indent_inc}}OPTIONAL {{'
        update1 += f'\n{blank:{(indent + 3) * indent_inc}}{leftnode.iri.toRdf} skos:broader ?parent_node'
        update1 += f' .\n{blank:{(indent + 2) * indent_inc}}}}'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}}}'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}BIND((?rindex + 1) AS ?nlindex)'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}BIND((?rindex + 2) AS ?nrindex)'
        update1 += f'\n{blank:{indent * indent_inc}}}}'

        self._con.transaction_start()
        self.safe_update(update1)

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
        jsonobj = self.safe_query(query1)
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
                ?node skos:inScheme {self.__oldapListIri.toRdf} ;
                      oldap:rightIndex ?rindex ;
                      oldap:leftIndex ?lindex .
            }}
            FILTER( ((?lindex + 1) >= {rindex}) && (?node != {self.__iri.toRdf}))
            BIND((?lindex + 2) AS ?nlindex)
        }}
        """
        self.safe_update(update2)

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
                ?node skos:inScheme {self.__oldapListIri.toRdf} ;
                      oldap:rightIndex ?rindex ;
                      oldap:leftIndex ?lindex ;
            }}
            FILTER( (?rindex >= {lindex}) && (?node != {self.__iri.toRdf}))
            BIND((?rindex + 2) AS ?nrindex)
        }}
        """
        self.safe_update(update3)

        jsonobj = self.safe_query(query1)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            self._con.transaction_abort()
            raise OldapError('Insert_node_right_of failed')
        for row in res:
            self.__leftIndex = row['lindex']
            self.__rightIndex = row['rindex']

        self.safe_commit()
        self.clear_changeset()
        cache = CacheSingletonRedis()
        cache.delete(self.__oldapListIri)

    def insert_node_left_of(self, rightnode: Self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Inserts a node to the left of the specified rightnode in a list hierarchy
        while maintaining consistent indexing and properties. This operation
        validates permissions, builds SPARQL update queries for performing the
        insertion, adjusts index consistency across the list, and updates the
        store and cache as needed. This ensures that the hierarchy and index
        are maintained correctly even after new nodes are added.

        :param rightnode: The node to the right of which the new node will
                          be inserted.
        :type rightnode: Self
        :param indent: The base level of indentation for formatting update
                       queries. Defaults to 0.
        :param indent_inc: The increment in the indentation level for nested
                           elements in update queries. Defaults to 4.
        :type indent_inc: int
        :return: None
        :rtype: None
        :raises OldapError: If there is no existing connection or the
                            transaction fails.
        :raises OldapErrorNoPermission: If the user does not have permission
                                        for the operation.
        """
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
        update1 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__iri.toRdf} a {self.__node_classIri}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:inScheme {self.__oldapListIri.toRdf}'
        if self.prefLabel:
            update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.PREF_LABEL.value} {self.prefLabel.toRdf}'
        if self.definition:
            update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.DEFINITION.value} {self.definition.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:leftIndex ?lindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:rightIndex ?nrindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:broader ?parent_node'
        update1 += f' .\n{blank:{(indent + 1) * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}}}'
        update1 += f'\n{blank:{indent * indent_inc}}WHERE {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f' \n{blank:{(indent + 2) * indent_inc}}{rightnode.iri.toRdf} oldap:leftIndex ?lindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:rightIndex ?rindex'
        update1 += f' ;\n{blank:{(indent + 2) * indent_inc}}OPTIONAL {{'
        update1 += f'\n{blank:{(indent + 3) * indent_inc}}{rightnode.iri.toRdf} skos:broader ?parent_node'
        update1 += f' .\n{blank:{(indent + 2) * indent_inc}}}}'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}}}'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}BIND((?lindex + 1) AS ?nrindex)'
        update1 += f'\n{blank:{indent * indent_inc}}}}'

        self._con.transaction_start()
        self.safe_update(update1)

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
        jsonobj = self.safe_query(query1)
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
                ?node skos:inScheme {self.__oldapListIri.toRdf} ;
                      oldap:leftIndex ?lindex .
            }}
            FILTER((?node != {self.__iri.toRdf}) && (?lindex >= {lindex}))
            BIND((?lindex + 2) AS ?nlindex)
        }}
        """
        self.safe_update(update2)

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
               ?node skos:inScheme {self.__oldapListIri.toRdf} ;
                      oldap:rightIndex ?rindex ;
            }}
            FILTER((?node != {self.__iri.toRdf}) && (?rindex >= {rindex}))
            BIND((?rindex + 2) AS ?nrindex)
        }}
        """
        self.safe_update(update3)

        jsonobj = self.safe_query(query1)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            self._con.transaction_abort()
            raise OldapError('Insert_node_left_of failed')
        for row in res:
            self.__leftIndex = row['lindex']
            self.__rightIndex = row['rindex']

        self.safe_commit()
        self.clear_changeset()
        cache = CacheSingletonRedis()
        cache.delete(self.__oldapListIri)

    def insert_node_below_of(self, parentnode: Self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Inserts a new node as a child of the specified parent node in a semantic data structure.

        This method ensures that the new node is correctly added as a hierarchical child node
        of the provided parent node while maintaining logical consistency in the data graph.
        The operation includes SPARQL queries and updates performed within a transactional
        context to safeguard against potential inconsistencies.

        :param parentnode: The parent node under which the new node is to be inserted.
        :type parentnode: Self
        :param indent: The base indentation level for formatting SPARQL queries. Default is 0.
        :type indent: int
        :param indent_inc: The increment amount for each indentation level in SPARQL query formatting. Default is 4.
        :type indent_inc: int
        :return: None
        :rtype: None
        :raises OldapError: Raised if the operation cannot start due to missing connection.
        :raises OldapErrorNoPermission: Raised if the current user lacks permissions for the operation.
        :raises OldapErrorInconsistency: Raised if an insertion point already contains sub-nodes.
        :raises OldapError: Raised if the insertion operation encounters unexpected issues or inconsistencies.
        """
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
                ?node skos:broader {parentnode.iri.toRdf} .
            }}
        }}
        """
        self._con.transaction_start()

        jsonobj = self.safe_query(query1)
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OldapErrorInconsistency(f'insert_node_below_of: Insertion point already has sub-node(s)!')

        blank = ''
        update1 = context.sparql_context
        update1 += f'{blank:{indent * indent_inc}}INSERT {{'
        update1 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        update1 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__iri.toRdf} a {self.__node_classIri}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:inScheme {self.__oldapListIri.toRdf}'
        if self.prefLabel:
            update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.PREF_LABEL.value} {self.prefLabel.toRdf}'
        if self.definition:
            update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListNodeAttr.DEFINITION.value} {self.definition.toRdf}'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:leftIndex ?nlindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:rightIndex ?nrindex'
        update1 += f' ;\n{blank:{(indent + 3) * indent_inc}}skos:broader {parentnode.iri.toRdf}'
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

        self.safe_update(update1)

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
        jsonobj = self.safe_query(query2)
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
                    ?node skos:inScheme {self.__oldapListIri.toRdf} ;
                          oldap:leftIndex ?lindex ;
                          oldap:rightIndex ?rindex .
                }}
                FILTER((?node != {self.__iri.toRdf}) && (?rindex >= {lindex}))
                BIND((?rindex + 2) AS ?nrindex)
            }}
        """
        self.safe_update(update2)

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
                    ?node skos:inScheme {self.__oldapListIri.toRdf} ;
                          oldap:leftIndex ?lindex ;
                          oldap:rightIndex ?rindex .
                }}
                FILTER((?node != {self.__iri.toRdf}) && (?lindex >= {rindex}))
                BIND((?lindex + 2) AS ?nlindex)
            }}
        """
        self.safe_update(update3)

        jsonobj = self.safe_query(query2)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            self._con.transaction_abort()
            raise OldapError('Insert_node_below_of failed')
        for row in res:
            self.__leftIndex = row['lindex']
            self.__rightIndex = row['rindex']

        self.safe_commit()
        self.clear_changeset()
        cache = CacheSingletonRedis()
        cache.delete(self.__oldapListIri)

    def in_use(self) -> bool:
        """
        Checks if the current node is currently in use within the specified graph context.

        The method constructs a SPARQL `ASK` query using the context's graph name and
        the IRI in question to determine if it is used in any triple within the graph.

        :return: A SPARQL `ASK` query as a string to determine the IRI usage.
        :rtype: str
        """
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        query += f"""
        ASK {{
            {{ GRAPH {self.__graph}:data
                {{
                    ?s ?p {self.__iri.toRdf}
                }}
            }}
        }}
        """
        return query

    def in_use_recursively(self) -> bool:
        """
        Determine whether the current node and its descendants is in use recursively by generating an
        ASK SPARQL query. This query checks if certain conditions, such as the context
        and index range, are satisfied for elements within the defined graph.

        :raises ValueError: If internal state variables are not properly initialized or lack
            required formatting for the SPARQL query.

        :return: Boolean value indicating whether the graph element is in use recursively as per
            the defined query.
        :rtype: bool
        """
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        query += f"""
        ASK  {{
            GRAPH {self.__graph}:data {{
	            ?s ?p ?o .
            }}
            GRAPH {self.__graph}:lists {{
	            ?o skos:inScheme {self.__oldapListIri.toRdf} .
	            ?o oldap:leftIndex ?leftIndex .
	            ?o oldap:rightIndex ?rightIndex .
            }}
            FILTER (?leftIndex >= {int(self.__leftIndex)} && ?rightIndex <= {int(self.__rightIndex)})
        }}
        """
        return query


    def delete_node(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Deletes a node with the provided indices and ensures proper index adjustments. The method
        performs transaction operations to safeguard against inconsistencies during the deletion
        process. Additionally, it ensures no dependent nodes or references are left unresolved.

        :param indent: The initial indentation level used in logging or display.
        :param indent_inc: Increment value for each level of indentation in logging or display.
        :return: None
        """
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

        self._con.transaction_start()

        query0 = self.in_use()
        result = self.safe_query(query0)
        if result['boolean']:
            self._con.transaction_abort()
            raise OldapErrorInUse(f'Cannot delete: node "{self.__iri}" is in use')

        context = Context(name=self._con.context_name)
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?node
        WHERE {{
            GRAPH {self.__graph}:lists {{
                ?node skos:broader {self.__iri.toRdf}
            }}
        }}
        """
        jsonobj = self.safe_query(query1)
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OldapErrorInUse(f'Cannot delete node with skos:broader pointing to it!')

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
        jsonobj = self.safe_query(query2)
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
        self.safe_update(update1)

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
        self.safe_update(update2)

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
        self.safe_update(update3)

        self.safe_commit()
        self.clear_changeset()
        cache = CacheSingletonRedis()
        cache.delete(self.__oldapListIri)

    def delete_node_recursively(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Recursively deletes a node and its child nodes while ensuring consistency in the
        underlying hierarchical structure. The method performs various operations such as
        permission checking, deletion of nodes, and adjustments to indices of nodes to
        the right of the deleted node.

        :param indent: Initial indent level for log or trace purposes.
        :type indent: int
        :param indent_inc: Incremental value used for adjusting indent level.
        :type indent_inc: int
        :return: This method does not return a value, its purpose is execution of node deletion.
        :rtype: None
        :raises OldapError: When there is no connection available for performing the operation.
        :raises OldapErrorNoPermission: When permissions to delete a node are insufficient.
        :raises OldapErrorInUse: When the node is in use and cannot be deleted.
        :raises OldapErrorInconsistency: When an inconsistency is encountered retrieving the node.
        """
        if self._con is None:
            raise OldapError("Cannot create: no connection")

        context = Context(name=self._con.context_name)
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        self._con.transaction_start()

        query0 = self.in_use_recursively()
        result = self.safe_query(query0)
        if result['boolean']:
            self._con.transaction_abort()
            raise OldapErrorInUse(f'Cannot delete: some node are in use')

        #
        # first we get the node info, especially leftIndex and rightIndex
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
        jsonobj = self.safe_query(query1)
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
            GRAPH {self.__graph}:lists {{
                ?subject oldap:leftIndex ?leftIndex ;
        	        oldap:rightIndex ?rightIndex ;
        	        skos:inScheme {self.__oldapListIri.toRdf} ;
        	        ?p ?o .
    	        FILTER (?leftIndex >= {int(lindex)} && ?rightIndex <= {int(rindex)})
            }}
        }}
        """
        self.safe_update(update1)

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
                skos:inScheme {self.__oldapListIri.toRdf} .
            FILTER(?oldLeftIndex > {int(lindex)})
            BIND(?oldLeftIndex - {int(diff)} AS ?newLeftIndex)
        }}
        """
        self.safe_update(update2)

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
                skos:inScheme {self.__oldapListIri.toRdf} .
            FILTER(?oldRightIndex > {int(rindex)})
            BIND(?oldRightIndex - {int(diff)} AS ?newRightIndex)
        }}
        """
        self.safe_update(update3)

        self.safe_commit()
        cache = CacheSingletonRedis()
        cache.delete(self.__oldapListIri)


    def move_node_below(self, con: IConnection, target: Self, indent: int = 0, indent_inc: int = 4):
        """
        Moves a node and its subtree below a target node within a hierarchical structure. This operation
        modifies the index values (`leftIndex` and `rightIndex`) of the nodes to reflect their new position
        in the hierarchy. The function ensures consistency in the index values and prevents any invalid
        hierarchical relationships. The function also updates the parent reference (`broader`)
        after the move and commits the changes to the graph.

        :param con: The connection interface to interact with the graph/database.
        :type con: IConnection
        :param target: The node that will become the new parent of the moved node.
        :type target: Self
        :param indent: The starting level of indentation for logging or debugging.
        :type indent: int
        :param indent_inc: Increment of indentation for nested structures or operations.
        :type indent_inc: int
        :return: None

        :raises OldapError: When there is no connection available for performing the operation.
        :raises OldapErrorNoPermission: When the user does not have permission to perform the operation.
        :raises OldapErrorInUse: When the node is in use and cannot be moved.
        """
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
                    {self.__iri.toRdf} skos:broader ?parent_iri .
                }}
            }}
        }}
        """
        self._con.transaction_start()
        jsonobj = self.safe_query(query1)
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
        jsonobj = self.safe_query(query1)
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
        # target node may not be below moving node!
        #
        if (target_lindex >= moving_lindex) and (target_rindex <= moving_rindex):
            raise OldapErrorInconsistency(f"Cannot move node to target node that is part of the tree to be moved!")

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
                skos:inScheme {self.__oldapListIri.toRdf} .
            FILTER (?oldLeftIndex >= {int(moving_lindex)} && ?oldRightIndex <= {int(moving_rindex)})
            BIND(-?oldLeftIndex AS ?newLeftIndex)
            BIND(-?oldRightIndex AS ?newRightIndex)
        }}
        """
        self.safe_update(update1)

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
                skos:inScheme {self.__oldapListIri.toRdf} .
            {filter}
            BIND(?oldLeftIndex - {int(diff1)} AS ?newLeftIndex)
        }}
        """
        self.safe_update(update2)

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
                skos:inScheme {self.__oldapListIri.toRdf} .
            {filter}
            BIND(?oldRightIndex - {int(diff1)} AS ?newRightIndex)
        }}
        """
        self.safe_update(update3)

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
        self.safe_update(update4)

        #
        # update parent (skos:broader)
        #
        update5 = context.sparql_context
        if moving_parent_iri:
            update5 += f"""
            DELETE {{
                GRAPH {self.__graph}:lists {{
                    ?subject skos:broader ?parent .
                }}
            }}
            """
        update5 += f"""
        INSERT {{
            GRAPH {self.__graph}:lists {{
                ?subject skos:broader {target.__iri.toRdf} .
            }}
        }}
        WHERE {{
            BIND({self.__iri.toRdf} AS ?subject)
            OPTIONAL {{
                ?subject skos:broader ?parent .
            }}
        }}
        """
        self.safe_update(update5)

        #
        # commit
        #
        self.safe_commit()
        cache = CacheSingletonRedis()
        cache.delete(self.__oldapListIri)

    def move_node_right_of(self, con: IConnection, leftnode: Self, indent: int = 0, indent_inc: int = 4):
        """
        Move a node to the right of a specified left node, adjusting its position and relationship in a hierarchical
        structure. This operation includes permission checks, positional adjustments, and hierarchy consistency checks.

        :param con: The connection object used to interact with the database
            or remote system.
        :type con: IConnection
        :param leftnode: The node to which the current node will be moved
            to the right of.
        :type leftnode: Self
        :param indent: The base level of indentation, default is 0.
        :type indent: int, optional
        :param indent_inc: Increment to adjust indentation levels, default is 4.
        :type indent_inc: int, optional
        :return: None
        :rtype: None
        :raises OldapError: If no connection is established.
        :raises OldapErrorNoPermission: If the user lacks necessary permissions to execute the operation.
        :raises OldapErrorInconsistency: If inconsistencies are detected during the operation.
        """
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
                    {self.__iri.toRdf} skos:broader ?parent_iri .
                }}
            }}
        }}
        """
        self._con.transaction_start()
        jsonobj = self.safe_query(query1)
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
                    {leftnode.__iri.toRdf} skos:broader ?parent_iri .
                }}
            }}
        }}
        """
        self._con.transaction_start()
        jsonobj = self.safe_query(query1)
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
        # target node may not be below moving node!
        #
        if (left_lindex >= moving_lindex) and (left_rindex <= moving_rindex):
            raise OldapErrorInconsistency(f"Cannot move node to target node that is part of the tree to be moved!")

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
                skos:inScheme {self.__oldapListIri.toRdf} .
            FILTER (?oldLeftIndex >= {int(moving_lindex)} && ?oldRightIndex <= {int(moving_rindex)})
            BIND(-?oldLeftIndex AS ?newLeftIndex)
            BIND(-?oldRightIndex AS ?newRightIndex)
        }}
        """
        self.safe_update(update1)

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
                skos:inScheme {self.__oldapListIri.toRdf} .
            {filter}
            BIND(?oldLeftIndex - {int(diff1)} AS ?newLeftIndex)
        }}
        """
        self.safe_update(update2)

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
                skos:inScheme {self.__oldapListIri.toRdf} .
            {filter}
            BIND(?oldRightIndex - {int(diff1)} AS ?newRightIndex)
        }}
        """
        self.safe_update(update3)

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
        self.safe_update(update4)

        update5 = context.sparql_context
        if moving_parent_iri:
            update5 += f"""
            DELETE {{
                GRAPH {self.__graph}:lists {{
                    ?subject skos:broader ?parent .
                }}
            }}
        """
        if left_parent_iri:
            update5 += f"""
            INSERT {{
                GRAPH {self.__graph}:lists {{
                    ?subject skos:broader {left_parent_iri.toRdf} .
                }}
            }}
        """
        update5 += f"""
        WHERE {{
            BIND({self.__iri.toRdf} AS ?subject)
            ?subject skos:broader ?parent .
        }}
        """
        if moving_parent_iri or left_parent_iri:
            self.safe_update(update5)

        #
        # commit
        #
        self.safe_commit()
        cache = CacheSingletonRedis()
        cache.delete(self.__oldapListIri)

    def move_node_left_of(self, con: IConnection, rightnode: Self, indent: int = 0, indent_inc: int = 4):
        """
        Moves a node in a tree structure to the left of a specified sibling node. The method ensures that the
        node's position is properly updated based on the given tree's left and right indices, adjusting all
        relevant indices within the tree and validating the operation.

        :param con: The connection object used for the database operations.
        :type con: IConnection
        :param rightnode: The target sibling node to place the given node to the left of.
        :type rightnode: Self
        :param indent: The base indentation level for the operation.
        :type indent: int
        :param indent_inc: The amount by which to increment the indentation for subsequent operations.
        :type indent_inc: int
        :return: None

        :raises OldapError: If the operation fails.
        :raises OldapErrorNoPermission: If the user does not have permission to perform the operation.
        """
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
                    {self.__iri.toRdf} skos:broader ?parent_iri .
                }}
            }}
        }}
        """
        self._con.transaction_start()
        jsonobj = self.safe_query(query1)
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
                    {rightnode.__iri.toRdf} skos:broader ?parent_iri .
                }}
            }}
        }}
        """
        jsonobj = self.safe_query(query1)
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
        # target node may not be below moving node!
        #
        if (right_lindex >= moving_lindex) and (right_rindex <= moving_rindex):
            raise OldapErrorInconsistency(f"Cannot move node to target node that is part of the tree to be moved!")

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
                skos:inScheme {self.__oldapListIri.toRdf} .
            FILTER (?oldLeftIndex >= {int(moving_lindex)} && ?oldRightIndex <= {int(moving_rindex)})
            BIND(-?oldLeftIndex AS ?newLeftIndex)
            BIND(-?oldRightIndex AS ?newRightIndex)
        }}
        """
        self.safe_update(update1)

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
                skos:inScheme {self.__oldapListIri.toRdf} .
            {filter}
            BIND(?oldLeftIndex - {int(diff1)} AS ?newLeftIndex)
        }}
        """
        self.safe_update(update2)

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
                skos:inScheme {self.__oldapListIri.toRdf} .
            {filter}
            BIND(?oldRightIndex - {int(diff1)} AS ?newRightIndex)
        }}
        """
        self.safe_update(update3)

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
        self.safe_update(update4)

        update5 = context.sparql_context
        if moving_parent_iri:
            update5 += f"""
            DELETE {{
                GRAPH {self.__graph}:lists {{
                    ?subject skos:broader ?parent .
                }}
            }}
        """
        if right_parent_iri:
            update5 += f"""
            INSERT {{
                GRAPH {self.__graph}:lists {{
                    ?subject skos:broader {right_parent_iri.toRdf} .
                }}
            }}
        """
        update5 += f"""
        WHERE {{
            BIND({self.__iri.toRdf} AS ?subject)
            ?subject skos:broader ?parent .
        }}
        """
        if moving_parent_iri or right_parent_iri:
            self.safe_update(update5)
        #
        # commit
        #
        self.safe_commit()
        cache = CacheSingletonRedis()
        cache.delete(self.__oldapListIri)

    @staticmethod
    def search(con: IConnection,
               projectShortName: Xsd_NCName,
               projectIri: Iri,
               oldapListId: Xsd_NCName,
               oldapListIri: Iri,
               node_classIri: Iri,
               #oldapList: "OldapList",
               id: Xsd_string | str | None = None,
               prefLabel: Xsd_string | str | None = None,
               definition: str | None = None,
               exactMatch: bool = False) -> list[Iri]:
        """
        Searches for nodes in the graph associated with the provided parameters and returns a list of their IRIs.

        :param con: The connection interface to the knowledge graph.
        :type con: IConnection
        :param projectShortName: The short name of the project where the search is performed.
        :type projectShortName: Xsd_NCName
        :param projectIri: The IRI of the project where the search is performed.
        :type projectIri: Iri
        :param oldapListId: The identifier of the oldap list in the project.
        :type oldapListId: Xsd_NCName
        :param oldapListIri: The IRI of the oldap list in the project.
        :type oldapListIri: Iri
        :param node_classIri: The IRI of the node class to filter in the search.
        :type node_classIri: Iri
        :param id: The identifier of the node to search for. Optional.
        :type id: Xsd_string | str | None
        :param prefLabel: The preferred label of the node to search for. Optional.
        :type prefLabel: Xsd_string | str | None
        :param definition: The definition of the node to search for. Optional.
        :type definition: str | None
        :param exactMatch: A flag indicating whether the search should use exact matching for the provided parameters.
        :type exactMatch: bool
        :return: A list of IRIs of the found nodes.
        :rtype: list[Iri]

        :raises OldapError: If the operation fails.
        """
        id = Xsd_string(id)
        prefLabel = Xsd_string(prefLabel)
        definition = Xsd_string(definition)
        context = Context(name=con.context_name)
        graph = projectShortName

        prefLabel = Xsd_string(prefLabel)
        sparql = context.sparql_context
        sparql += 'SELECT DISTINCT ?node\n'
        sparql += f'FROM {graph}:lists\n'
        sparql += 'WHERE {\n'
        sparql += f'   ?node a {node_classIri} ;\n'
        sparql += f'       skos:inScheme {oldapListIri.toRdf} .\n'
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


