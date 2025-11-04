from copy import deepcopy
from datetime import datetime
from functools import partial
from typing import Any, Self, Callable

from elementpath.datatypes import NCName

from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.externalontologyattr import ExternalOntologyAttr
from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission, OldapErrorAlreadyExists, \
    OldapErrorNotFound, OldapErrorUpdateFailed
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string


@serializer
class ExternalOntology(Model, Notify):
    """Class representing external ontologies.

    This class provides methods for managing external ontologies.
    """
    __extonto_qname: Xsd_QName | None
    __graph: Xsd_NCName | None

    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | str |None = None,
                 created: Xsd_dateTime | datetime | str | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | datetime | str | None = None,
                 notifier: Callable[[Xsd_QName], None] | None = None,
                 notify_data: Xsd_QName | None = None,
                 graph: Xsd_NCName | str,
                 validate: bool = False,
                 **kwargs):
        Model.__init__(self,
                       connection=con,
                       creator=creator,
                       created=created,
                       contributor=contributor,
                       modified=modified,
                       validate=validate)
        Notify.__init__(self, notifier, notify_data)
        if isinstance(graph, Xsd_NCName):
            self.__graph = graph
        else:
            self.__graph = Xsd_NCName(graph, validate=validate)
        self.set_attributes(kwargs, ExternalOntologyAttr)
        self.__extonto_qname = Xsd_QName(self.__graph, self._attributes[ExternalOntologyAttr.PREFIX])

        for attr in ExternalOntologyAttr:
            setattr(ExternalOntology, attr.value.fragment, property(
                partial(ExternalOntology._get_value, attr=attr),
                partial(ExternalOntology._set_value, attr=attr),
                partial(ExternalOntology._del_value, attr=attr)))
        self._changeset = {}

    @property
    def extonto_qname(self) -> Xsd_QName:
        return self.__extonto_qname

    def update_notifier(self):
        for attr, value in self._attributes.items():
            if getattr(value, 'set_notifier', None) is not None:
                value.set_notifier(self.notifier, attr)

    def _as_dict(self):
        return {x.fragment: y for x, y in self._attributes.items()} | super()._as_dict() | {
            'graph': self.__graph
        }

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
        instance._changset = deepcopy(self._changeset, memo)
        instance.__graph = deepcopy(self.__graph, memo)
        instance.__extonto_qname = deepcopy(self.__extonto_qname, memo)
        return instance

    def check_for_permissions(self) -> (bool, str):
        """
        Internal method to check if a user may modify the permission set.
        :return: a tuple with a boolean (True, False) and the error message (or "OK")
        """
        #
        # First we check if the logged-in user ("actor") has the ADMIN_PERMISSION_SETS permission for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('oldap:SystemProject'))
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            #
            # user has root privileges!
            #
            return True, "OK"
        else:
            if actor.inProject.get(self.__project.projectIri) is None:
                return False, f'Actor has no ADMIN_MODEL permission for project {self.__project.projectIri}'
            else:
                if AdminPermission.ADMIN_MODEL not in actor.inProject.get(self.__project.projectIri):
                    return False, f'Actor has no ADMIN_MODEL permission for project {self.__project.projectIri}'
            return True, "OK"

    def notifier(self, what: ExternalOntologyAttr, value: Any = None) -> None:
        self._changeset[what] = AttributeChange(None, Action.MODIFY)

    def create_shacl(self, *,
                     timestamp: Xsd_dateTime,
                     indent: int = 0,
                     indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:shacl {{\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}} {self.__extonto_qname.toRdf} a oldap:ExternalOntology'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        for attr, value in self._attributes.items():
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{attr.value.toRdf} {value.toRdf}'
        sparql += f'\n{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        return sparql

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        if self._con is None:
            raise OldapError("Cannot create: no connection")

        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        timestamp = Xsd_dateTime()

        context = Context(name=self._con.context_name)
        blank = ''
        query1 = context.sparql_context
        query1 += f"""
        ASK {{
            GRAPH {self.__graph}:shacl {{
                {self.__extonto_qname.toRdf} a oldap:ExternalOntology .
            }}
        }}
        """

        sparql = context.sparql_context
        sparql += self.create_shacl(timestamp=timestamp)

        self._con.transaction_start()
        res1 = self.safe_query(query1)
        if res1['boolean']:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'An ExternalOntology with a graphIri "{self.__graph}" already exists.')
        self.safe_update(sparql)
        self._con.transaction_commit()
        self._created = timestamp
        self._creator = self._con.userIri
        self._modified = timestamp
        self._contributor = self._con.userIri
        context[self._attributes[ExternalOntologyAttr.PREFIX]] = NamespaceIRI(str(self._attributes[ExternalOntologyAttr.NAMESPACE_IRI]))
        cache = CacheSingletonRedis()
        cache.set(self.__extonto_qname, self)

    @classmethod
    def read(cls, *,
             con: IConnection,
             graph: Xsd_NCName | str,
             prefix: NCName | str | None = None,
             validate: bool = False,
             ignore_cache: bool = False):
        if not isinstance(graph, Xsd_NCName):
            graph = Xsd_NCName(graph, validate=validate)
        if isinstance(prefix, NCName):
            extonto_qname = Xsd_QName(graph, prefix, validate=validate)
        else:
            extonto_qname = Xsd_QName(graph, Xsd_NCName(prefix, validate=validate), validate=validate)
        if not ignore_cache:
            cache = CacheSingletonRedis()
            tmp = cache.get(extonto_qname, connection=con)
            if tmp is not None:
                tmp.update_notifier()
                return tmp
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?extonto ?p ?o
        FROM {graph}:shacl
        WHERE {{
            BIND({extonto_qname.toRdf} as ?extonto)
            ?extonto a oldap:ExternalOntology .
            ?extonto ?p ?o .
        }}
        """
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OldapErrorNotFound(f'No external ontology "{cls.__extonto_qname}" found.')
        creator: Iri | None = None
        created: Xsd_dateTime | None = None
        contributor: Iri | None = None
        modified: Xsd_dateTime | None = None
        namespace_iri: NamespaceIRI | None = None
        prefix: NCName | None = None
        label: LangString = LangString()
        comment: LangString = LangString()
        for r in res:
            match str(r['p']):
                case 'dcterms:creator':
                    creator = r['o']
                case 'dcterms:created':
                    created = r['o']
                case 'dcterms:contributor':
                    contributor = r['o']
                case 'dcterms:modified':
                    modified = r['o']
                case 'oldap:namespaceIri':
                    namespace_iri = NamespaceIRI(r['o'])
                case 'oldap:prefix':
                    prefix = r['o']
                case 'rdfs:label':
                    label.add(r['o'])
                case 'rdfs:comment':
                    comment.add(r['o'])
        if comment:
            comment.changeset_clear()
            comment.set_notifier(cls.notifier, Xsd_QName(ExternalOntologyAttr.LABEL.value))
        if label:
            label.changeset_clear()
            label.set_notifier(cls.notifier, Xsd_QName(ExternalOntologyAttr.LABEL.value))
        instance = cls(con=con,
                       graph=graph,
                       creator=creator,
                       created=created,
                       contributor=contributor,
                       modified=modified,
                       prefix=prefix,
                       namespaceIri=namespace_iri,
                       label=label,
                       comment=comment,
                       validate=False)
        cache = CacheSingletonRedis()
        cache.set(instance.__extonto_qname, instance)
        return instance

    @staticmethod
    def search(con: IConnection, *,  # TODO: finish work here!!! This is just a small sceleton!
               graph: Xsd_NCName | str,
               prefix: NCName | str | None = None,
               namespaceIri: NamespaceIRI | str | None = None,
               label: Xsd_string | str | None = None,
               validate: bool = False) -> dict[Xsd_QName, 'ExternalOntology']:
        if not isinstance(graph, Xsd_NCName):
            graph = Xsd_NCName(graph, validate=validate)

        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += f"SELECT DISTINCT ?extonto ?p ?o"
        sparql += f"\nFROM {graph}:shacl"
        sparql += "\nWHERE {"
        sparql += "\n    ?extonto a oldap:ExternalOntology ."
        sparql += "\n    ?extonto ?p ?o ."
        if prefix:
            sparql += f'\n    FILTER( REPLACE(STR(?extonto), ".+[#/]", "") = "{prefix}" ) )'
        elif namespaceIri:
            sparql += f'\n    ?extonto oldap:namespaceIri ?namespaceIri .'
            sparql += f'\n    FILTER( ?namespaceIri = "{namespaceIri}" )'
        elif label:
            sparql += f'\n    ?extonto rdfs:label ?label .'
            if label.lang:
                sparql += f'?label = {label.toRdf}'
            else:
                sparql += f'CONTAINS(STR(?label), "{Xsd_string.escaping(label.value)}")'
        sparql += "\n}"
        sparql += "\nORDER BY ?extonto"
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        result: dict[Xsd_QName, ExternalOntology] = {}
        working_on: Xsd_QName | None = None
        data: dict = {}
        for r in res:
            if working_on is None or working_on != r['extonto']:
                if working_on:
                    result[working_on] = ExternalOntology(con=con,
                                                          graph=graph,
                                                          **data)
                data = {}
                data['label'] = LangString()
                data['comment'] = LangString()
                working_on = r['extonto']
            if r['p'] == 'rdf:type':
                continue
            if r['p'] == 'rdfs:label':
                data['label'].add(r['o'])
            elif r['p'] == 'rdfs:comment':
                data['comment'].add(r['o'])
            elif r['p'] == 'oldap:namespaceIri':
                data['namespaceIri'] = NamespaceIRI(r['o'])
            else:
                data[str(r['p'].fragment)] = r['o']
        if working_on:
            result[working_on] = ExternalOntology(con=con,
                                                  graph=graph,
                                                  **data)
        return result

    def update(self, indent: int = 0, indent_inc: int = 4) -> None:
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)
        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)
        blank = ''
        sparql_list = []

        for attr, change in self._changeset.items():
            if attr == ExternalOntologyAttr.LABEL or attr == ExternalOntologyAttr.COMMENT:
                if change.action == Action.MODIFY:
                    sparql_list.extend(self._attributes[attr].update(graph=Xsd_QName(self.__graph, 'shacl'),
                                                                     subject=self.__extonto_qname,
                                                                     field=attr.value))
                if change.action == Action.DELETE or change.action == Action.REPLACE:
                    sparql = self._changeset[attr].old_value.delete(graph=Xsd_QName(self.__graph, 'shacl'),
                                                            subject=self.__extonto_qname,
                                                            field=attr.value)
                    sparql_list.append(sparql)
                if change.action == Action.CREATE or change.action == Action.REPLACE:
                    sparql = self._attributes[attr].create(graph=Xsd_QName(self.__graph, 'shacl'),
                                                            subject=self.__extonto_qname,
                                                            field=attr.value)
                    sparql_list.append(sparql)
                continue
            sparql = f'{blank:{indent * indent_inc}}WITH {self.__graph}:shacl\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}{self.__extonto_qname.toRdf} {attr.value} {change.old_value.toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}{self.__extonto_qname.toRdf} {attr.value} {self._attributes[attr].toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}{self.__extonto_qname.toRdf} {attr.value} {change.old_value.toRdf} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        sparql = context.sparql_context
        sparql += " ;\n".join(sparql_list)

        self._con.transaction_start()
        try:
            self._con.transaction_update(sparql)
            self.set_modified_by_iri(Xsd_QName(self.__graph, 'shacl'), self.__extonto_qname, self._modified, timestamp)
            modtime = self.get_modified_by_iri(Xsd_QName(self.__graph, 'shacl'), self.__extonto_qname)
        except OldapError:
            self._con.transaction_abort()
            raise
        if timestamp != modtime:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed(f'Update of ExternalOntology "{self.__extonto_qname}" failed! Timestamp does not match"')
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        self._modified = timestamp
        self._contributor = self._con.userIri  # TODO: move creator, created etc. to Model!
        cache = CacheSingletonRedis()
        cache.set(self.__extonto_qname, self)

    def in_use_queries(self) -> (str, str):
        """
        Generates two SPARQL ASK queries to check the usage of a permission set in two contexts:
        assigned to a user or used by a data object (resource). The generated queries are used
        to confirm whether the specified permission set is currently in use within the system.

        The first query checks if the permission set is assigned to any user. The second query
        validates if the permission set is associated with any data object or resource.

        :return: A tuple containing two SPARQL ASK queries as strings. The first query checks
                 if the permission set is assigned to a user, and the second query checks if
                 the permission set is associated with a data object or resource.
        :rtype: tuple[str, str]
        """
        context = Context(name=self._con.context_name)

        #
        # first check if the external ontology is used in the datamodel
        # TODO: Exlucde ExternalOntology definitions itself....
        #
        query1 = context.sparql_context
        query1 += f"""
        ASK {{
            GRAPH {self.__graph}:shacl {{
                ?s ?p ?o .
                FILTER(
                    STRSTARTS(STR(?s), "{self.namespaceIri}") ||
                    STRSTARTS(STR(?p), "{self.namespaceIri}") ||
                    (isIRI(?o) && STRSTARTS(STR(?o), "{self.namespaceIri}"))
                )
            }}
        }}
        """

        #
        # now check if the permission set is used by a data object (resource)
        #
        query2 = context.sparql_context
        query2 += f"""
        ASK {{
            VALUES ?g {{ {self.__graph}:data {self.__graph}:lists }}
            GRAPH ?g {{
                ?s ?p ?o .
                 FILTER(
                    STRSTARTS(STR(?p), "{self.namespaceIri}") ||
                    (isIRI(?o) && STRSTARTS(STR(?o), "{self.namespaceIri}"))
                )
           }}
        }}
        """


    def delete(self, indent: int = 0, indent_inc: int = 4) -> None:
        pass


