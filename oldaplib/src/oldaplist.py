from functools import partial
from pprint import pprint
from typing import Self

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

    __project: Project
    __graph: Xsd_NCName
    __oldapList_iri: Iri
    __node_namespaceIri: NamespaceIRI
    __node_class_iri: Iri

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
        self.__graph = self.__project.projectShortName

        self.set_attributes(kwargs, OldapListAttr)

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
                return False, f'Actor has no ADMIN_LISTS permission for user {self.userId}.'
            allowed: list[Iri] = []
            for proj in actor.inProject.keys():
                if actor.inProject.get(proj) is None:
                    return False, f'Actor has no ADMIN_LISTS permission for project {proj}'
                else:
                    if AdminPermission.ADMIN_LISTS not in actor.inProject.get(proj):
                        return False, f'Actor has no ADMIN_LISTS permission for project {proj}'
            return True, "OK"

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

    @classmethod
    def read(cls,
             con: IConnection,
             project: Project | Iri | Xsd_NCName | str,
             oldapListId: Xsd_NCName | str) -> Self:
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

    def update(self, indent: int = 0, indent_inc: int = 4) -> None:
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

    def delete(self) -> None:
        """
        Delete the given user from the triplestore
        :return: None
        :raises OldapErrorNoPermission: No permission for operation
        :raises OldapError: generic internal error
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



