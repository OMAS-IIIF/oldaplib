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

from oldaplib.src.cachesingleton import CacheSingleton
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.oldaplistattr import OldapListAttr
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapError, OldapErrorNoPermission, OldapErrorAlreadyExists, \
    OldapErrorNotFound, OldapErrorUpdateFailed, OldapErrorInUse
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string

OldapListAttrTypes = LangString | Iri | None


class OldapList(Model):
    """
    Implementation of the OLDAP List object. It implements a SKOS ConceptScheme.
    """

    __project: Project
    __graph: Xsd_NCName
    __oldapList_iri: Iri
    __node_namespaceIri: NamespaceIRI
    __node_class_iri: Iri
    nodes: list

    __slots__ = ('oldapListId', 'prefLabel', 'definition')

    def __init__(self, *,
                 con: IConnection,
                 project: Project | Iri | Xsd_NCName | str,
                 creator: Iri | None = None,
                 created: Xsd_dateTime | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | None = None,
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
        super().__init__(connection=con,
                         creator=creator,
                         created=created,
                         contributor=contributor,
                         modified=modified)
        self.nodes = []
        if isinstance(project, Project):
            self.__project = project
        else:
            self.__project = Project.read(self._con, project)

        context = Context(name=self._con.context_name)
        self.__graph = self.__project.projectShortName

        self.set_attributes(kwargs, OldapListAttr)
        if self._attributes.get(OldapListAttr.PREF_LABEL) is None:
            self._attributes[OldapListAttr.PREF_LABEL] = LangString(str(self._attributes[OldapListAttr.OLDAPLIST_ID]))

        self.__oldapList_iri = Iri.fromPrefixFragment(self.__project.projectShortName,
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
        self.__node_class_iri = Iri(f'{self.__oldapList_iri}Node', validate=False)
        list_node_prefix = Xsd_NCName("L-") + self._attributes[OldapListAttr.OLDAPLIST_ID]
        context[list_node_prefix] = self.__node_namespaceIri
        context.use(list_node_prefix)

        for attr in OldapListAttr:
            setattr(OldapList, attr.value.fragment, property(
                partial(OldapList._get_value, attr=attr),
                partial(OldapList._set_value, attr=attr),
                partial(OldapList._del_value, attr=attr)))

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
        instance.__oldapList_iri = deepcopy(self.__oldapList_iri, memo)
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
    def node_class_iri(self) -> Iri:
        return self.__node_class_iri

    @property
    def project(self) -> Project:
        return self.__project

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
        if not isinstance(project, Project):
            project = Project.read(con, project)
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

        return cls(con=con,
                   project=project,
                   oldapListId=oldapListId,
                   creator=creator,
                   created=created,
                   contributor=contributor,
                   modified=modified,
                   prefLabel=prefLabel,
                   definition=definition)

    @property
    def project(self) -> Project:
        return self.__project

    @property
    def node_namespaceIri(self):
        return self.__node_namespaceIri

    @property
    def oldapList_iri(self) -> Iri:
        return self.__oldapList_iri

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
        if not isinstance(project, Project):
            project = Project.read(con, project)
        id = Xsd_string(id)
        prefLabel = Xsd_string(prefLabel)
        definition = Xsd_string(definition)
        context = Context(name=con.context_name)
        graph = project.projectShortName

        prefLabel = Xsd_string(prefLabel)
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
            FILTER(?list = {self.__oldapList_iri.toRdf})
        }}
        """

        #
        # first we create the empty list as an instance of oldap:OldapList
        #
        blank = ''
        sparql2 = context.sparql_context
        sparql2 += f'{blank:{indent * indent_inc}}INSERT DATA {{'
        sparql2 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        sparql2 += f'\n{blank:{(indent + 2) * indent_inc}}{self.__oldapList_iri.toRdf} a oldap:OldapList'
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
        sparql3 += f' ;\n{blank:{(indent + 4) * indent_inc}}sh:hasValue {self.__oldapList_iri.toRdf}'
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
        try:
            jsonobj = self._con.transaction_query(sparql1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'A list with a oldapListIri "{self.__oldapList_iri}" already exists')

        try:
            self._con.transaction_update(sparql2)
            self._con.transaction_update(sparql3)
            self._con.transaction_update(sparql4)
        except OldapError:
            self._con.transaction_abort()
            raise
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        self._created = timestamp
        self._creator = self._con.userIri
        self._modified = timestamp
        self._contributor = self._con.userIri
        self.clear_changeset()

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
                                                                      subject=self.__oldapList_iri,
                                                                      field=Xsd_QName(field.value)))
                if change.action == Action.DELETE or change.action == Action.REPLACE:
                    sparql = self._changeset[field].old_value.delete(graph=Xsd_QName(f'{self.__graph}:lists'),
                                                                     subject=self.__oldapList_iri,
                                                                     field=Xsd_QName(field.value))
                    sparql_list.append(sparql)
                if change.action == Action.CREATE or change.action == Action.REPLACE:
                    sparql = self._attributes[field].create(graph=Xsd_QName(f'{self.__graph}:lists'),
                                                            subject=self.__oldapList_iri,
                                                            field=Xsd_QName(field.value))
                    sparql_list.append(sparql)

        sparql = context.sparql_context
        sparql += " ;\n".join(sparql_list)

        self._con.transaction_start()
        try:
            self._con.transaction_update(sparql)
            self.set_modified_by_iri(Xsd_QName(f'{self.__graph}:lists'), self.__oldapList_iri, self.modified, timestamp)
            modtime = self.get_modified_by_iri(Xsd_QName(f'{self.__graph}:lists'), self.__oldapList_iri)
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
        #
        # we changed something, therefore we invalidate the list cache
        cache = CacheSingleton()
        cache.delete(self.__oldapList_iri)


    def delete(self) -> None:
        """
        Deletes a list from the RDF triplestore. The list must have no list items in order to allow the deletion
        :return: None object
        :rtype: None
        """
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'''
        SELECT ?listnode
        FROM {self.__graph}:lists
        WHERE {{
            ?listnode a oldap:OldapListNode .
        }}
        '''
        jsonobj = self._con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            raise OldapErrorInUse(f'List {self.prefLabel} cannot be deleted since there are still nodes.')

        sparql1 = context.sparql_context
        sparql1 += f"""
        DELETE WHERE {{
            GRAPH {self.__graph}:lists {{
                {self.__oldapList_iri.toRdf} a oldap:OldapList .
                {self.__oldapList_iri.toRdf} ?prop ?val .
            }}
        }} 
        """

        sparql2 = context.sparql_context
        sparql2 += f"""
        DELETE WHERE {{
            GRAPH {self.__graph}:shacl {{
                {self.__node_class_iri}Shape ?prop ?val .
            }}
        }}
        """

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
            self._con.transaction_update(sparql1)
            self._con.transaction_update(sparql2)
            self._con.transaction_update(sparql3)
        except OldapError:
            self._con.transaction_abort()
            raise
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        cache = CacheSingleton()
        cache.delete(self.__oldapList_iri)



