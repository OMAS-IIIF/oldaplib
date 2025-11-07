from copy import deepcopy
from datetime import datetime
from functools import partial
from typing import Any, Self, Callable

from elementpath.datatypes import NCName

from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.dtypes.xsdset import XsdSet
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.enums.externalontologyattr import ExternalOntologyAttr
from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission, OldapErrorAlreadyExists, \
    OldapErrorNotFound, OldapErrorUpdateFailed, OldapErrorInUse
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
    __projectShortName: Xsd_NCName | None

    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | str |None = None,
                 created: Xsd_dateTime | datetime | str | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | datetime | str | None = None,
                 notifier: Callable[[Xsd_QName], None] | None = None,
                 notify_data: Xsd_QName | None = None,
                 projectShortName: Xsd_NCName | str,
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
        if isinstance(projectShortName, Xsd_NCName):
            self.__projectShortName = projectShortName
        else:
            self.__projectShortName = Xsd_NCName(projectShortName, validate=validate)
        self.set_attributes(kwargs, ExternalOntologyAttr)
        self.__extonto_qname = Xsd_QName(self.__projectShortName, self._attributes[ExternalOntologyAttr.PREFIX])

        for attr in ExternalOntologyAttr:
            setattr(ExternalOntology, attr.value.fragment, property(
                partial(ExternalOntology._get_value, attr=attr),
                partial(ExternalOntology._set_value, attr=attr),
                partial(ExternalOntology._del_value, attr=attr)))
        self.update_notifier()
        #self._changeset = {}

    def __len__(self):
        return len(self._attributes)


    @property
    def extonto_qname(self) -> Xsd_QName:
        return self.__extonto_qname

    def update_notifier(self,
                        notifier: Callable[[AttributeClass | Xsd_QName], None] | None = None,
                        notify_data: AttributeClass | None = None,):
        self.set_notifier(notifier, notify_data)
        for attr, value in self._attributes.items():
            if getattr(value, 'set_notifier', None) is not None:
                value.set_notifier(self.notifier, attr)

    def _as_dict(self):
        return {x.fragment: y for x, y in self._attributes.items()} | super()._as_dict() | {
            'projectShortName': self.__projectShortName
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
        Notify.__init__(instance,
                        notifier=self._notifier,
                        data=deepcopy(self._notify_data, memo))
        # Copy internals of Model:
        instance._attributes = deepcopy(self._attributes, memo)
        instance._changset = deepcopy(self._changeset, memo)
        instance.__projectShortName = deepcopy(self.__projectShortName, memo)
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

    def notifier(self, attr: ExternalOntologyAttr, value: Any = None) -> None:
        self._changeset[attr] = AttributeChange(None, Action.MODIFY)
        self.notify()

    def create_shacl(self, *,
                     timestamp: Xsd_dateTime,
                     indent: int = 0,
                     indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self.__projectShortName}:shacl {{\n'
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
            GRAPH {self.__projectShortName}:shacl {{
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
            raise OldapErrorAlreadyExists(f'An ExternalOntology with a graphIri "{self.__projectShortName}" already exists.')
        self.safe_update(sparql)
        self._con.transaction_commit()
        self._created = timestamp
        self._creator = self._con.userIri
        self._modified = timestamp
        self._contributor = self._con.userIri
        #context[self._attributes[ExternalOntologyAttr.PREFIX]] = NamespaceIRI(str(self._attributes[ExternalOntologyAttr.NAMESPACE_IRI]))
        cache = CacheSingletonRedis()
        cache.set(self.__extonto_qname, self)

    @classmethod
    def read(cls, *,
             con: IConnection,
             projectShortName: Xsd_NCName | str,
             prefix: NCName | str | None = None,
             validate: bool = False,
             ignore_cache: bool = False):
        if not isinstance(projectShortName, Xsd_NCName):
            projectShortName = Xsd_NCName(projectShortName, validate=validate)
        if isinstance(prefix, NCName):
            extonto_qname = Xsd_QName(projectShortName, prefix, validate=validate)
        else:
            extonto_qname = Xsd_QName(projectShortName, Xsd_NCName(prefix, validate=validate), validate=validate)
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
        FROM {projectShortName}:shacl
        WHERE {{
            BIND({extonto_qname} as ?extonto)
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
            comment.clear_changeset()
            comment.set_notifier(cls.notifier, Xsd_QName(ExternalOntologyAttr.LABEL.value))
        if label:
            label.clear_changeset()
            label.set_notifier(cls.notifier, Xsd_QName(ExternalOntologyAttr.LABEL.value))
        instance = cls(con=con,
                       projectShortName=projectShortName,
                       creator=creator,
                       created=created,
                       contributor=contributor,
                       modified=modified,
                       prefix=prefix,
                       namespaceIri=namespace_iri,
                       label=label,
                       comment=comment,
                       validate=False)
        instance.update_notifier()
        cache = CacheSingletonRedis()
        cache.set(instance.__extonto_qname, instance)
        return instance

    @staticmethod
    def search(con: IConnection, *,  # TODO: finish work here!!! This is just a small sceleton!
               projectShortName: Xsd_NCName | str,
               prefix: NCName | str | None = None,
               namespaceIri: NamespaceIRI | str | None = None,
               label: Xsd_string | str | None = None,
               validate: bool = False) -> list['ExternalOntology']:
        if not isinstance(projectShortName, Xsd_NCName):
            projectShortName = Xsd_NCName(projectShortName, validate=validate)

        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += f"SELECT DISTINCT ?extonto ?p ?o"
        sparql += f"\nFROM {projectShortName}:shacl"
        sparql += "\nWHERE {"
        sparql += "\n    ?extonto a oldap:ExternalOntology ."
        sparql += "\n    ?extonto ?p ?o ."
        if prefix:
            sparql += f'\n    FILTER( REPLACE(STR(?extonto), ".+[#/]", "") = "{prefix}" )'
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
        result: list[ExternalOntology] = []
        working_on: Xsd_QName | None = None
        data: dict = {}
        cache = CacheSingletonRedis()
        for r in res:
            if working_on is None or working_on != r['extonto']:
                if working_on:
                    tmp = ExternalOntology(con=con,
                                           projectShortName=projectShortName,
                                           **data)
                    result.append(tmp)
                    cache.set(tmp.__extonto_qname, tmp)
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
            tmp = ExternalOntology(con=con,
                                   projectShortName=projectShortName,
                                   **data)
            result.append(tmp)
            cache.set(tmp.__extonto_qname, tmp)

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
                    sparql_list.extend(
                        self._attributes[attr].update(graph=Xsd_QName(self.__projectShortName, 'shacl'),
                                                      subject=self.__extonto_qname,
                                                      field=attr.value))
                if change.action == Action.DELETE or change.action == Action.REPLACE:
                    sparql = self._changeset[attr].old_value.delete(graph=Xsd_QName(self.__projectShortName, 'shacl'),
                                                                    subject=self.__extonto_qname,
                                                                    field=attr.value)
                    sparql_list.append(sparql)
                if change.action == Action.CREATE or change.action == Action.REPLACE:
                    sparql = self._attributes[attr].create(graph=Xsd_QName(self.__projectShortName, 'shacl'),
                                                           subject=self.__extonto_qname,
                                                           field=attr.value)
                    sparql_list.append(sparql)
                continue
            sparql = f'{blank:{indent * indent_inc}}WITH {self.__projectShortName}:shacl\n'
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
            self.set_modified_by_iri(Xsd_QName(self.__projectShortName, 'shacl'), self.__extonto_qname, self._modified, timestamp)
            modtime = self.get_modified_by_iri(Xsd_QName(self.__projectShortName, 'shacl'), self.__extonto_qname)
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
            GRAPH {self.__projectShortName}:shacl {{
                ?s ?p ?o .
                FILTER(
                    (STRSTARTS(STR(?p), "{self.namespaceIri}") ||
                    (isIRI(?o) && STRSTARTS(STR(?o), "{self.namespaceIri}"))) &&
                    ?p != oldap:namespaceIri
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
            VALUES ?g {{ {self.__projectShortName}:data {self.__projectShortName}:lists }}
            GRAPH ?g {{
                ?s ?p ?o .
                 FILTER(
                    STRSTARTS(STR(?p), "{self.namespaceIri}") ||
                    (isIRI(?o) && STRSTARTS(STR(?o), "{self.namespaceIri}"))
                )
           }}
        }}
        """
        return query1, query2

    def in_use(self) -> bool:
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        query1, query2 = self.in_use_queries()
        result1 = self._con.query(query1)
        if result1['boolean']:
            return True
        result2 = self._con.query(query2)
        if result2['boolean']:
            return True
        return False

    def delete(self, indent: int = 0, indent_inc: int = 4) -> None:
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        query1, query2 = self.in_use_queries()
        context = Context(name=self._con.context_name)

        #
        # Now prepare the queries for deleting the permission set
        #
        sparql = context.sparql_context
        sparql += f"""
        DELETE WHERE {{
            GRAPH {self.__projectShortName}:shacl {{
                {self.__extonto_qname.toRdf} ?prop ?val .
            }}
        }} 
        """

        self._con.transaction_start()
        result1 = self.safe_query(query1)
        if result1['boolean']:
            self._con.transaction_abort()
            raise OldapErrorInUse(f"External ontology is used in the data model.")
        result2 = self.safe_query(query2)
        if result2['boolean']:
            self._con.transaction_abort()
            raise OldapErrorInUse("External ontology is used in the data.")
        self.safe_update(sparql)
        self._con.transaction_commit()
        cache = CacheSingletonRedis()
        cache.delete(self.__extonto_qname)

    @classmethod
    def delete_all(cls, *,
                   con: IConnection,
                   projectShortName: Xsd_NCName | str,
                   validate: bool = False) -> None:
        if not isinstance(projectShortName, Xsd_NCName):
            projectShortName = Xsd_NCName(projectShortName, validate=validate)
        context = Context(name=con.context_name)

        query0 = context.sparql_context
        query0 += f"""
        SELECT DISTINCT ?extonto
        FROM {projectShortName}:shacl
        WHERE {{
            ?extonto a oldap:ExternalOntology .
        }}
        """

        sparql = context.sparql_context
        sparql += f"""
        DELETE {{
            GRAPH {projectShortName}:shacl {{
                ?s ?p ?o .
            }}
        }}
        WHERE {{
            GRAPH {projectShortName}:shacl {{
                ?s a oldap:ExternalOntology .
                ?s ?p ?o .
            }}
        }}
        """
        con.update_query(sparql)



