"""
# Hierarchical Lists / Thesauri

Hierarchical lists, thesauri, and categories are vital for databases in the humanities as they provide structured
frameworks for organizing and retrieving complex, multifaceted data. These tools facilitate semantic understanding by
establishing relationships between terms—such as broader, narrower, or equivalent concepts—allowing researchers to
navigate datasets intuitively and comprehensively. In disciplines like history, linguistics, and cultural studies,
where meanings and connections are often context-dependent, thesauri and hierarchical structures enable accurate
indexing, enhance search precision, and promote interdisciplinary linkages. Moreover, they support the standardization
and interoperability of data across projects, fostering collaborative research and the integration of diverse datasets
into unified, accessible knowledge systems.

## OLDAP implementation of Hierarchical Lists / Thesauri

### Modelling based on "Nested Set Model"

Hierarchical lists / thesauri are somehow inbetween the data model and the actual data. The usually remain static, but
may be extended/changed according to the needs that arise in the course of a research project.
OLDAP provides a highly efficient implementationm of hierarchical (or flat) lists / thesauri that is optimized for
retrieval. On the one hand, hierarchical lists are usually defined at the beginning of a project. They are used to
categorize database objects. For example, the following categories can be used to characterize a means of transport:

- on foot
- horse
- carriage
- railroad

Sub-categories could be assigned to each category, e.g. for railroad

- on foot
- horse
- carriage
    - ox cart
    - horse-drawn carriage
- railroad
    - milk train
    - regional train
    - express
    - special train

Such categories are usually static and do not change. However, the categories may need to be adjusted from
time to time during the course of a project. This has as consequence that the hierarchical lists must be optimized for
the search. In OLDAP, the [Nested Set Model](https://en.wikipedia.org/wiki/Nested_set_model) is used to store the
hierarchical lists. The hierarchical lists are stored in a graph, where each node is a list item. The list items are
connected to their parent list item by a directed edge. The root list item is the list item with no parent.

## SKOS

The OLDAP implementation relies to a great extent on the skos-vocabulary provided by
[SKOS](https://www.w3.org/TR/skos-reference/). The implementation is as follows:

### List object

A list object is a `skos:ConceptScheme` with the following properties:

- `skos:prefLabel`: The label (name) of the list. Must be a LangString.
- `skos:definition`: A description of the list. Must be a LangString.
- `skos:definition`: A LangString describing the list more verbose.

It identifies a hierarchical list, but is itself not a list item.

### List item object (node)

A list item object is a `skos:Concept` with the following properties:

- `skos:inScheme`: points to the list object
- `skos:broaderTransitive`: points to the parent node if there is one
- `skos:prefLabel`: A description of the list item. Must be a LangString.
- `skos:definition`: A LangString describing the list item more verbose.
- `oldap:nextNode`: Pointer to the next list item (will be automatically managed by OLDAP)
- `oldap:leftIndex`: Nested Set Model left value (will be automatically managed by OLDAP)
- `oldap:rightIndex`: Nested Set Model right value (will be automatically managed by OLDAP)

"""
from copy import deepcopy
from functools import partial
from pprint import pprint
from typing import Self, Any

from oldaplib.src.cachesingleton import CacheSingleton, CacheSingletonRedis
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.oldaplistattr import OldapListAttr
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.irincname import IriOrNCName
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapError, OldapErrorNoPermission, \
    OldapErrorAlreadyExists, \
    OldapErrorNotFound, OldapErrorUpdateFailed, OldapErrorInUse, OldapErrorInconsistency
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.oldaplistnode import OldapListNode
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string

OldapListAttrTypes = LangString | Iri | None

@serializer
class OldapList(Model):
    """
    Implementation of the OLDAP List object. It implements a SKOS ConceptScheme.
    """

    __project: Project
    __graph: Xsd_NCName
    __iri: Iri
    __node_namespaceIri: NamespaceIRI
    __node_prefix: Xsd_NCName
    __node_class_iri: Iri
    nodes: list[OldapListNode]  # used for building complete list including all it's nodes!

    __slots__ = ('oldapListId', 'prefLabel', 'definition')

    def __init__(self, *,
                 con: IConnection,
                 project: Project | Iri | Xsd_NCName | str,
                 creator: Iri | None = None,
                 created: Xsd_dateTime | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | None = None,
                 nodes: list[OldapListNode] = [],
                 validate: bool = False,
                 **kwargs):
        """
        Constructor for OldapList
        :param con: Active connection to the OLDAP server.
        :type con: IConnection
        :param project: a Project object, project short name or IRI.
        :type project: Project | Iri | Xsd_NCName | st
        :param creator: Creator IRI (INTERNAL USE ONLY!)
        :type creator: Iri
        :param created: creation date (INTERNAL USE ONLY!)
        :type created: Xsd_dateTime
        :param contributor: Contributor IRI (INTERNAL USE ONLY!)
        :type contributor: Iri
        :param modified: Modification timestamp (INTERNAL USE ONLY!)
        :type modified: Xsd_dateTime
        :param kwargs: Further parameters (see enum/oldaplistattr.py)
        :type kwargs: see enum/oldaplistattr.py
        """
        if not isinstance(con, IConnection):
            raise ValueError(f'Connection must be an instance of IConnection, not {type(con)}')
        super().__init__(connection=con,
                         creator=creator,
                         created=created,
                         contributor=contributor,
                         modified=modified,
                         validate=validate)
        self.nodes = nodes
        if isinstance(project, Project):
            self.__project = project
        else:
            if not isinstance(project, (Iri, Xsd_NCName)):
                project = IriOrNCName(project, validate=validate)
            self.__project = Project.read(self._con, project)

        context = Context(name=self._con.context_name)
        self.__graph = self.__project.projectShortName

        self.set_attributes(kwargs, OldapListAttr)
        if self._attributes.get(OldapListAttr.PREF_LABEL) is None:
            self._attributes[OldapListAttr.PREF_LABEL] = LangString(str(self._attributes[OldapListAttr.OLDAPLIST_ID]))

        self.__iri = Iri.fromPrefixFragment(self.__project.projectShortName,
                                            self._attributes[OldapListAttr.OLDAPLIST_ID],
                                            validate=False)
        #
        # we will use a special prefix for the ListNodes instances: "<project.namespace_iri>/<list_id>#"
        # This will allow us to have unique ListNode IRI's even if the same ListNode-ID is used for different lists.
        # (Within a list, the ListNode-ID's must be unique)
        # This we create a context as follows:
        # @PREFIX L-<list-id>: <project.namespace_iri>/<list_id>#
        #
        self.__node_namespaceIri = self.__project.namespaceIri.expand(self._attributes[OldapListAttr.OLDAPLIST_ID])
        self.__node_class_iri = Iri(f'{self.__iri}Node', validate=False)
        self.__node_prefix = Xsd_NCName("L-") + self._attributes[OldapListAttr.OLDAPLIST_ID]
        context[self.__node_prefix] = self.__node_namespaceIri
        context.use(self.__node_prefix)

        for attr in OldapListAttr:
            setattr(OldapList, attr.value.fragment, property(
                partial(OldapList._get_value, attr=attr),
                partial(OldapList._set_value, attr=attr),
                partial(OldapList._del_value, attr=attr)))

    def _as_dict(self):
        return {x.fragment: y for x, y in self._attributes.items()} | super()._as_dict() | {
            'project': self.__project.projectShortName,
            'nodes': self.nodes
        }

    def check_for_permissions(self) -> (bool, str):
        """
        Check the permission of the connected user to manipulate hierarchical lists
        :return: Tuple with True, if the user has the ADMIN_LISTS permission, False otherwise, and a message
        :rtype: bool, str
        """
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
            if len(actor.inProject) == 0:
                return False, f'Actor has no ADMIN_LISTS permission for project "{self.__project.projectIri}".'
            if not actor.inProject.get(self.__project.projectIri):
                return False, f'Actor has no ADMIN_LISTS permission for project "{self.__project.projectIri}".'
            if AdminPermission.ADMIN_LISTS not in actor.inProject.get(self.__project.projectIri):
                return False, f'Actor has no ADMIN_LISTS permission for project "{self.__project.projectIri}".'
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
        instance._changeset = deepcopy(self._changeset, memo)

        instance.__graph = deepcopy(self.__graph, memo)
        instance.__project = deepcopy(self.__project, memo)
        instance.__iri = deepcopy(self.__iri, memo)
        instance.__node_namespaceIri = deepcopy(self.__node_namespaceIri, memo)
        instance.__node_class_iri = deepcopy(self.__node_class_iri, memo)
        instance.nodes = deepcopy(self.nodes, memo)

        return instance


    def notifier(self, attr: OldapListAttr) -> None:
        """
        This method is called when a field is being changed.
        :param fieldname: Fieldname of the field being modified
        :return: None
        """
        self._changeset[attr] = AttributeChange(self._attributes[attr], Action.MODIFY)

    @property
    def node_classIri(self) -> Iri:
        return self.__node_class_iri

    @property
    def project(self) -> Project:
        return self.__project

    @property
    def node_namespaceIri(self):
        return self.__node_namespaceIri

    @property
    def node_prefix(self) -> Xsd_NCName:
        return self.__node_prefix

    @property
    def iri(self) -> Iri:
        return self.__iri

    @property
    def info(self):
        return {
            'projectShortName': self.__project.projectShortName,
            'projectIri': self.__project.projectIri,  # Iri
            'oldapListId': self.oldapListId,  # Xsd_NCName
            'oldapListIri': self.__iri,  # Iri
            'node_classIri': self.__node_class_iri,  # Iri
        }

    def get_nodes_from_list(self) -> list[OldapListNode]:
        context = Context(name=self._con.context_name)
        graph = self.project.projectShortName

        query = context.sparql_context
        query += f"""    
        SELECT ?node ?created ?creator ?modified ?contributor ?rindex ?lindex ?parent ?prefLabel ?definition
        WHERE {{
            GRAPH {graph}:lists {{
                ?node skos:inScheme {self.iri.toRdf} ;
                    dcterms:created ?created ;
                    dcterms:creator ?creator ;
                    dcterms:modified ?modified ;
                    dcterms:contributor ?contributor ;
                    oldap:leftIndex ?lindex ;
                    oldap:rightIndex ?rindex .
                OPTIONAL {{
                    ?node skos:prefLabel ?prefLabel .
                }}
                OPTIONAL {{
                    ?node skos:definition ?definition .
                }}
                OPTIONAL {{
                    ?node skos:broaderTransitive ?parent .
                }}
            }}
        }}
        ORDER BY ?lindex
        """
        jsonobj = self._con.query(query)
        res = QueryProcessor(context, jsonobj)
        nodes: list[OldapListNode] = []
        all_nodes: list[OldapListNode] = []
        last_nodeiri = None
        for r in res:
            nodeiri = r['node']
            if last_nodeiri != nodeiri:
                prefix, id = str(nodeiri).split(':')
                ln = OldapListNode(con=self._con,
                                   **self.info,
                                   oldapListNodeId=Xsd_NCName(id, validate=False),
                                   created=r['created'],
                                   creator=r['creator'],
                                   modified=r['modified'],
                                   contributor=r['contributor'],
                                   leftIndex=r['lindex'],
                                   rightIndex=r['rindex'],
                                   defaultLabel=False)
                if r.get('parent') is not None:
                    parent_prefix, parent_id = str(r['parent']).split(':')
                    pnodes = [x for x in all_nodes if x.oldapListNodeId == parent_id]
                    pnodes[0].add_node_to_nodes(ln)
                else:
                    nodes.append(ln)
                all_nodes.append(ln)
            if r.get('prefLabel'):
                if ln.prefLabel:
                    ln.prefLabel.add(r['prefLabel'])
                else:
                    ln.prefLabel = LangString(r['prefLabel'])
            if r.get('definition'):
                if ln.definition:
                    ln.definition.add(r['definition'])
                else:
                    ln.definition = LangString(r['definition'])

            last_nodeiri = nodeiri
        return nodes

    @classmethod
    def read(cls,
             con: IConnection,
             project: Project | Iri | Xsd_NCName | str,
             oldapListId: Xsd_NCName | str) -> Self:
        """
        Read a list from the OLDAP server. This function reads only the list object, but it will _not_ read the
        nodes belonging to the list.
        :param con: Active connection to the OLDAP server.
        :type con: IConnection
        :param project: a Project object, project short name or IRI.
        :type project: Project | Iri | Xsd_NCName | str
        :param oldapListId: An ID that uniquely identifies the list. The name must be unique within a given project. However, different projects may use the same list-ID for identifying there respective lists.
        :type oldapListId: Xsd_NCName | str. Must be convertible to an NCName.
        :return: A list object
        :rtype: OldapList
        """

        if isinstance(project, Project):
            oldaplist_iri = Iri.fromPrefixFragment(project.projectShortName, oldapListId, validate=False)
        elif isinstance(project, Iri):
            oldaplist_iri = Iri.fromPrefixFragment(project, oldapListId, validate=False)
        elif isinstance(project, (Xsd_NCName, str)):
            project = Project.read(con, project)
            oldaplist_iri = Iri.fromPrefixFragment(project.projectShortName, oldapListId, validate=False)

        cache = CacheSingletonRedis()
        tmp = cache.get(oldaplist_iri, connection=con)
        if tmp is not None:
            return tmp

        if not isinstance(project, Project):
            project = Project.read(con, project)
        if not isinstance(oldapListId, Xsd_NCName):
            oldapListId = Xsd_NCName(oldapListId)
        oldaplist_iri = Iri.fromPrefixFragment(project.projectShortName, oldapListId, validate=False)

        context = Context(name=con.context_name)

        graph = project.projectShortName

        query = context.sparql_context
        query += f"""
            SELECT ?prop ?val
            FROM {graph}:lists
            WHERE {{
                {oldaplist_iri.toRdf} ?prop ?val
            }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OldapErrorNotFound(f'OldapList with IRI "{oldaplist_iri}" not found.')
        creator: Iri | None = None
        created: Xsd_dateTime | None = None
        contributor: Iri | None = None
        modified: Xsd_dateTime | None = None
        prefLabel: LangString | None = None
        definition: LangString | None = None
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
                case OldapListAttr.PREF_LABEL.value:
                    if not prefLabel:
                        prefLabel = LangString()
                    prefLabel.add(r['val'])
                case OldapListAttr.DEFINITION.value:
                    if not definition:
                        definition = LangString()
                    definition.add(r['val'])
        if prefLabel:
            prefLabel.changeset_clear()
            prefLabel.set_notifier(cls.notifier, Xsd_QName(OldapListAttr.PREF_LABEL.value))
        if definition:
            definition.changeset_clear()
            definition.set_notifier(cls.notifier, Xsd_QName(OldapListAttr.DEFINITION.value))

        instance = cls(con=con,
                       project=project,
                       oldapListId=oldapListId,
                       creator=creator,
                       created=created,
                       contributor=contributor,
                       modified=modified,
                       prefLabel=prefLabel,
                       definition=definition)
        instance.nodes = instance.get_nodes_from_list()
        cache.set(oldaplist_iri, instance)
        return instance

    @staticmethod
    def search(con: IConnection,
               project: Project | Iri | Xsd_NCName | str,
               id: Xsd_string | str | None = None,
               prefLabel: Xsd_string | str | None = None,
               definition: str | None = None,
               exactMatch: bool = False) -> list[Iri]:
        """
        Search for a specific list. The search can be made by given either an ID, a prefLabel or a definition. The
        required match can either be exact or by substring. If more than one search item is given, the search will
        combine the results by AND.
        :param con: Active connection to the OLDAP server.
        :type con: IConnection
        :param project: Project object or project short name or IRI.
        :type project: Project | Iri | Xsd_NCName | str
        :param id: List ID.
        :type id: Xsd_string | str | None
        :param prefLabel: Label of the list. All languages are being searched, if exactMatch is False.
        :type prefLabel: Xsd_string | str | None
        :param definition: Definition of the list. All languages are being searched, if exactMatch is False.
        :type definition: Xsd_string | str | None
        :param exactMatch: Exact match in search terms
        :type exactMatch: bool
        :return: List of hierarchival list's IRI's
        :rtype: list[Iri]
        """
        if not isinstance(con, IConnection):
            raise TypeError("con must be an IConnection object")
        if not isinstance(project, Project):
            if not isinstance(project, (Iri, Xsd_NCName)):
                project = IriOrNCName(project, validate=True)
            project = Project.read(con, project)
        id = Xsd_string(id, validate=True)
        prefLabel = Xsd_string(prefLabel, validate=True)
        definition = Xsd_string(definition, validate=True)

        context = Context(name=con.context_name)
        graph = project.projectShortName

        sparql = context.sparql_context
        sparql += 'SELECT DISTINCT ?node\n'
        sparql += f'FROM {graph}:lists\n'
        sparql += 'WHERE {\n'
        sparql += '   ?node a oldap:OldapList .\n'
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

        try:
            jsonobj = con.query(sparql)
        except OldapError as e:
            return[]
        res = QueryProcessor(context, jsonobj)
        lists: list[Iri] = []
        if len(res) > 0:
            for r in res:
                lists.append(r['node'])
        return lists

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Create a new list in the RDF triplestore. The method checks if a list with the same name is already existing
        :param indent: Start indent fpr beautifying the sparql query (INTERNAL USE/DEBUGGING)
        :type indent: int
        :param indent_inc: Indent increment for beautifying the sparql query (INTERNAL USE/DEBUGGING)
        :type indent_inc: int
        :return: None object
        :rtype: None
        :throws OldapErrorAlreadyExists: If a list with the same name already exists
        :throws OldapErrorNoPermission: If the logged-in user has no permission to create a list for the given project
        :throws OldapError: All other error conditions
        """
        if self._con is None:
            raise OldapError("Cannot create: no connection")
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        timestamp = Xsd_dateTime.now()
        #indent: int = 0
        #indent_inc: int = 4

        context = Context(name=self._con.context_name)

        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?list
        FROM {self.__graph}:lists
        WHERE {{
            ?list a oldap:OldapList .
            FILTER(?list = {self.__iri.toRdf})
        }}
        """

        #
        # first we create the empty list as an instance of oldap:OldapList
        #
        blank = ''
        sparql2 = context.sparql_context
        sparql2 += f'{blank:{indent * indent_inc}}INSERT DATA {{'
        sparql2 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        sparql2 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__iri.toRdf} a oldap:OldapList'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        if self.prefLabel:
            sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListAttr.PREF_LABEL.value} {self.prefLabel.toRdf}'
        if self.definition:
            sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListAttr.DEFINITION.value} {self.definition.toRdf}'
        sparql2 += f' .\n{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql2 += f'{blank:{indent * indent_inc}}}}\n'

        #
        # Now we create a SHACL subclass of oldap:OldapListNode that allows the validation of ListNodes.
        #
        sparql3 = context.sparql_context
        sparql3 += f'{blank:{indent * indent_inc}}INSERT DATA {{'
        sparql3 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:shacl {{'
        sparql3 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__node_class_iri}Shape a sh:NodeShape, {self.__node_class_iri.toRdf}'
        sparql3 += f' ;\n{blank:{(indent + 3) * indent_inc}}sh:targetClass {self.__node_class_iri.toRdf}'
        sparql3 += f' ;\n{blank:{(indent + 3) * indent_inc}}sh:node oldap:OldapListNodeShape'
        sparql3 += f' ;\n{blank:{(indent + 3) * indent_inc}}sh:property [ sh:path rdf:type ; ]'

        sparql3 += f' ;\n{blank:{(indent + 3) * indent_inc}}sh:property ['
        sparql3 += f'\n{blank:{(indent + 4) * indent_inc}}sh:path skos:inScheme'
        sparql3 += f' ;\n{blank:{(indent + 4) * indent_inc}}sh:class oldap:OldapList'
        sparql3 += f' ;\n{blank:{(indent + 4) * indent_inc}}sh:hasValue {self.__iri.toRdf}'
        sparql3 += f' ;\n{blank:{(indent + 3) * indent_inc}}]'

        sparql3 += f' .\n{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql3 += f'{blank:{indent * indent_inc}}}}\n'

        sparql4 = context.sparql_context
        sparql4 += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql4 += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:onto {{\n'
        sparql4 += f'{blank:{(indent + 2) * indent_inc}}{self.__node_class_iri.toRdf} rdf:type owl:Class ;\n'
        sparql4 += f'{blank:{(indent + 3) * indent_inc}}rdfs:subClassOf oldap:OldapListNode .\n'
        sparql4 += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql4 += f'{blank:{indent * indent_inc}}}}\n'

        self._con.transaction_start()
        jsonobj = self.safe_query(sparql1)
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'A list with a oldapListIri "{self.__iri}" already exists')

        try:
            self._con.transaction_update(sparql2)
            self._con.transaction_update(sparql3)
            self._con.transaction_update(sparql4)
        except OldapError:
            self._con.transaction_abort()
            raise
        self.safe_commit()
        self._created = timestamp
        self._creator = self._con.userIri
        self._modified = timestamp
        self._contributor = self._con.userIri
        self.clear_changeset()

        cache = CacheSingletonRedis()
        cache.set(self.__iri, self)

    def update(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Updates the metadata of an hierarchical list
        :param indent: Start indent for beautifying the sparql query (INTERNAL USE/DEBUGGING)
        :type indent: int
        :param indent_inc: Indent increment for beautifying the sparql query (INTERNAL USE/DEBUGGING)
        :type indent_inc: int
        :return: None object
        :rtype: None
        :throws OldapErrorNoPermission: If the logged-in user has no permission to update a list for the given project
        :throws OldapError: All other error conditions
        """
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)
        blank = ''
        sparql_list = []

        for field, change in self._changeset.items():
            if field == OldapListAttr.PREF_LABEL or field == OldapListAttr.DEFINITION:
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
        #
        # we changed something, therefore we invalidate the list cache
        #
        cache = CacheSingletonRedis()
        cache.delete(self.__iri)


    def in_use_queries(self) -> (str, str):
        """
        Checks if the list is in use. A list is in use if at least one list item is in use or
        if the list is referenced in a datamodel as property.
        :return: True if the list is in use, False otherwise
        :rtype: bool
        """

        #
        # first we check if a list item is in use by some resource instance
        #
        context = Context(name=self._con.context_name)
        query1 = context.sparql_context
        query1 += f'''
        ASK {{
            GRAPH {self.__graph}:data {{
	            ?s ?p ?o .
            }}
            GRAPH {self.__graph}:lists {{
	            ?o skos:inScheme {self.iri.toRdf} .
            }}
        }}
        '''

        #
        # now we check if a list is references as target from a property definition
        #
        context = Context(name=self._con.context_name)
        query2 = context.sparql_context
        query2 += f'''
        ASK {{
            GRAPH {self.__graph}:shacl {{
                ?propobj sh:class {self.__node_class_iri.toRdf} .
            }}
        }}
        '''
        return query1, query2

    def in_use(self) -> bool:
        query1, query2 = self.in_use_queries()

        self._con.transaction_start()
        res1 = self.safe_query(query1)
        if res1['boolean']:
            self._con.transaction_abort()
            return True
        res2 = self.safe_query(query2)
        if res2['boolean']:
            self._con.transaction_abort()
            return True
        self._con.transaction_commit()
        return False

    def delete(self) -> None:
        """
        Deletes a list from the RDF triplestore. The list must have no list items in order to allow the deletion
        :return: None object
        :rtype: None
        """
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)


        query1, query2 = self.in_use_queries()

        context = Context(name=self._con.context_name)
        #
        # first let's delete all nodes with all information
        #
        sparql0 = context.sparql_context
        sparql0 += f"""
        DELETE WHERE {{
            GRAPH {self.__graph}:lists {{
                ?node a {self.__node_class_iri.toRdf} .
                ?node ?prop ?val .
            }}
        }}
        """

        #
        # let's delete the list resource (that holds the information of the list)
        #
        sparql1 = context.sparql_context
        sparql1 += f"""
        DELETE WHERE {{
            GRAPH {self.__graph}:lists {{
                {self.__iri.toRdf} a oldap:OldapList .
                {self.__iri.toRdf} ?prop ?val .
            }}
        }} 
        """

        #
        # let's delete the SHACL definition
        #
        sparql2 = context.sparql_context
        sparql2 += f"""
        DELETE WHERE {{
            GRAPH {self.__graph}:shacl {{
                {self.__node_class_iri}Shape ?prop ?val .
            }}
        }}
        """

        #
        # let's delete the OWL class definition
        #
        sparql3 = context.sparql_context
        sparql3 += f"""
        DELETE WHERE {{
            GRAPH {self.__graph}:onto {{
                {self.__node_class_iri.toRdf} ?prop ?val .
            }}
        }}
        """

        self._con.transaction_start()
        try:
            result1 = self._con.query(query1)
            if result1['boolean']:
                raise OldapErrorInUse(f'Cannot delete list: "{self.__iri}" is in use')
            result2 = self._con.query(query2)
            if result2['boolean']:
                raise OldapErrorInUse(f'Cannot delete list: "{self.__iri}" is in use')
            self._con.transaction_update(sparql0)
            self._con.transaction_update(sparql1)
            self._con.transaction_update(sparql2)
            self._con.transaction_update(sparql3)
        except OldapError:
            self._con.transaction_abort()
            raise
        self.safe_commit()
        cache = CacheSingletonRedis()
        cache.delete(self.__iri)

