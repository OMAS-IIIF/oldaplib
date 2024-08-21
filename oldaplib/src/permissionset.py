from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Dict, Self, Any

from pystrict import strict

from oldaplib.src.cachesingleton import CacheSingleton
from oldaplib.src.connection import Connection
from oldaplib.src.enums.permissionsetattr import PermissionSetAttr
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.action import Action
from oldaplib.src.helpers.tools import lprint
from oldaplib.src.project import Project
from oldaplib.src.enums.projectattr import ProjectAttr
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorAlreadyExists, OldapErrorNoPermission, OldapError, \
    OldapErrorInconsistency, OldapErrorUpdateFailed, OldapErrorImmutable, OldapErrorNotFound
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.xsd.xsd_string import Xsd_string


#@strict
class PermissionSet(Model):

    __permset_iri: Iri | None
    __project: Project | None

    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | str |None = None,
                 created: Xsd_dateTime | datetime | str | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | datetime | str | None = None,
                 **kwargs):
        """
        Constructor for a permission set.
        :param con: Subclass of IConnection
        :type con: IConnection
        :param creator: Usually not being used (internal use only)
        :type creator: Iri | None
        :param created: Usually not being used (internal use only)
        :type created: Xsd_dateTime | datetime | str | None
        :param contributor: Usually not being used (internal use only)
        :type contributor: Iri | None
        :param modified: Usually not being used (internal use only)
        :type modified: Xsd_dateTime | datetime | str | None
        :param permissionSetId: A unique identifier for the permission set (unique within the project as given be :definedByProject)
        :type permissionSetId: Xsd_NCName | str
        :param label: A meaninful label for the permission set (several languages allowed)
        :type label: LangString | str
        :param comment: A meaningful comment for the permission set (several languages allowed)
        :type comment: LangString | str
        :param givesPermission: The permission that this permision set grants
        :type givesPermission: DataPermission
        :param definedByProject: The project that defines this permission set (either the IRI or the shortname)
        :type definedByProject: Iri | Xsd_NCName
        :raises OldapErrorNoFound: Given project does not exist
        """
        super().__init__(connection=con,
                         creator=creator,
                         created=created,
                         contributor=contributor,
                         modified=modified)
        self.__project = None
        self.set_attributes(kwargs, PermissionSetAttr)
        #
        # Consistency checks
        #
        if self._attributes.get(PermissionSetAttr.DEFINED_BY_PROJECT):
            self.check_consistency(PermissionSetAttr.DEFINED_BY_PROJECT, self._attributes[PermissionSetAttr.DEFINED_BY_PROJECT])

        self.__permset_iri = Iri.fromPrefixFragment(self.__project.projectShortName, self._attributes[PermissionSetAttr.PERMISSION_SET_ID], validate=False)

        for attr in PermissionSetAttr:
            setattr(PermissionSet, attr.value.fragment, property(
                partial(PermissionSet._get_value, attr=attr),
                partial(PermissionSet._set_value, attr=attr),
                partial(PermissionSet._del_value, attr=attr)))
        self._changeset = {}

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
        instance.__permset_iri = deepcopy(self.__permset_iri, memo)
        instance.__project = deepcopy(self.__project, memo)
        return instance

    def check_consistency(self, attr: PermissionSetAttr, value: Any) -> None:
        if attr == PermissionSetAttr.DEFINED_BY_PROJECT:
            if not isinstance(value, Project):
                self.__project = Project.read(self._con, value)
                self._attributes[attr] = self.__project.projectIri

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
            if actor.inProject.get(self.definedByProject) is None:
                return False, f'Actor has no ADMIN_PERMISSION_SETS permission for project {self.definedByProject}'
            else:
                if AdminPermission.ADMIN_PERMISSION_SETS not in actor.inProject.get(self.definedByProject):
                    return False, f'Actor has no ADMIN_PERMISSION_SETS permission for project {self.definedByProject}'
            return True, "OK"

    def notifier(self, what: PermissionSetAttr) -> None:
        self._changeset[what] = AttributeChange(None, Action.MODIFY)

    @property
    def iri(self) -> Iri:
        return self.__permset_iri

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Create the given permission set in the triple store.
        :param indent: indentation for SPARQL text
        :type indent: int
        :param indent_inc: indentation increment for the SPARQL text
        :type indent_inc: int
        :return: None
        """
        if self._con is None:
            raise OldapError("Cannot create: no connection")

        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        context = Context(name=self._con.context_name)
        blank = ''

        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?permset
        FROM oldap:admin
        WHERE {{
            ?permset a oldap:PermissionSet .
            FILTER(?permset = {self.__permset_iri.toRdf})       
        }}
        """

        timestamp = Xsd_dateTime()
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH oldap:admin {{\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}} {self.__permset_iri.toRdf} a oldap:PermissionSet'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        for attr, value in self._attributes.items():
            if attr.value.prefix == 'virtual' or not value:
                continue
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{attr.value.toRdf} {value.toRdf}'
        sparql += f'\n{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(sparql1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'A permission set "{self.__permset_iri}" already exists')

        try:
            self._con.transaction_update(sparql)
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
        cache = CacheSingleton()
        cache.set(self.__permset_iri, self)

    @classmethod
    def read(cls,
             con: IConnection,
             permissionSetId: Xsd_NCName | str,
             definedByProject: Project | Iri | Xsd_NCName | str,
             ignore_cache: bool = False) -> Self:
        """
        Reads a given permission set. The permission set is defined by its ID (which must be unique within
        one project) and the project IRI.
        :param con: A Connection object.
        :type con: IConnection
        :param permissionSetId: The ID of the permission set.
        :type permissionSetId: Xsd_NCName | str
        :param definedByProject: Iri or the shortname of the project
        :type definedByProject: Iri | Xsd_NCName | str
        :return: A PermissionSet instance
        :rtype: OldapPermissionSet
        :raises OldapErrorNot found: If the permission set cannot be found.
        """
        id = Xsd_NCName(permissionSetId)

        if isinstance(definedByProject, Project):
            project = definedByProject
        else:
            project = Project.read(con, definedByProject)
        permset_iri = Iri.fromPrefixFragment(project.projectShortName, permissionSetId, validate=False)
        if not ignore_cache:
            cache = CacheSingleton()
            tmp = cache.get(permset_iri)
            if tmp is not None:
                tmp._con = con
                return tmp
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?permset ?p ?o
        FROM oldap:admin
        WHERE {{
            BIND({permset_iri.toRdf} as ?permset)
            ?permset a oldap:PermissionSet .
            ?permset ?p ?o .
        }}
        """
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OldapErrorNotFound(f'No permission set "{permset_iri}"')

        permset_iri: Iri | None = None
        creator: Iri | None = None
        created: Xsd_dateTime | None = None
        contributor: Iri | None = None
        modified: Xsd_dateTime | None = None
        label: LangString = LangString()
        comment: LangString = LangString()
        givesPermission: DataPermission | None = None
        definedByProject: Iri | None = None
        for r in res:
            if not permset_iri:
                try:
                    permset_iri = r['permset']
                except Exception as e:
                    raise OldapErrorInconsistency(f'Invalid project identifier "{r['o']}".')
            match str(r['p']):
                case 'dcterms:creator':
                    creator = r['o']
                case 'dcterms:created':
                    created = r['o']
                case 'dcterms:contributor':
                    contributor = r['o']
                case 'dcterms:modified':
                    modified = r['o']
                case 'rdfs:label':
                    label.add(r['o'])
                case 'rdfs:comment':
                    comment.add(r['o'])
                case 'oldap:givesPermission':
                    givesPermission = DataPermission.from_string(str(r['o']))
                case 'oldap:definedByProject':
                    definedByProject = r['o']
        cls.__permset_iri = permset_iri
        if comment:
            comment.changeset_clear()
            comment.set_notifier(cls.notifier, Xsd_QName(PermissionSetAttr.LABEL.value))
        if label:
            label.changeset_clear()
            label.set_notifier(cls.notifier, Xsd_QName(PermissionSetAttr.LABEL.value))
        instance = cls(con=con,
                       permissionSetId=permissionSetId,
                       creator=creator,
                       created=created,
                       contributor=contributor,
                       modified=modified,
                       label=label,
                       comment=comment,
                       givesPermission=givesPermission,
                       definedByProject=Iri(definedByProject, validate=False))
        cache = CacheSingleton()
        cache.set(instance.__permset_iri, instance)
        return instance


    @staticmethod
    def search(con: IConnection, *,
               permissionSetId: str | None = None,
               definedByProject: Iri | str | None = None,
               givesPermission: DataPermission | None = None,
               label: Xsd_string | str | None = None) -> list[Iri | Xsd_QName]:
        """
        Search for a permission set. At least one of the search criteria is required. Multiple search criteria are
        combined using a logical AND.
        :param con: A valid Connection object.
        :type con: IConnection
        :param permissionSetId: Search for the given ID. The given string must be _contained_ in the ID (substring)
        :type permissionSetId: str | None
        :param definedByProject: The project which is responsible for the permission set
        :type definedByProject: str | None
        :param givesPermission: The permission that the permission set should grant
        :type givesPermission: str | None
        :param label: The label string. The given string must be within at least one language label.
        :type label: str | None
        :return: A list or permission set Iri's (possibly as Xsd_QName
        :rtype: list[Iri | Xsd_QName]
        """
        if definedByProject:
            definedByProject = Iri(definedByProject)
        label = Xsd_string(label)
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        if definedByProject:
            sparql += 'SELECT DISTINCT ?permsetIri ?namespaceIri ?projectShortName'
            context = Context(name=con.context_name)
        else:
            sparql += 'SELECT DISTINCT ?permsetIri'
        sparql += '\n'
        sparql += 'FROM NAMED oldap:admin\n'
        sparql += 'WHERE {\n'
        sparql += '   GRAPH oldap:admin {\n'
        sparql += '       ?permsetIri rdf:type oldap:PermissionSet .\n'
        if definedByProject:
            sparql += '       ?permsetIri oldap:definedByProject ?definedByProject .\n'
            sparql += '       ?definedByProject oldap:namespaceIri ?namespaceIri .\n'
            sparql += '       ?definedByProject oldap:projectShortName ?projectShortName .\n'
        if givesPermission:
            sparql += '       ?permsetIri oldap:givesPermission ?givesPermission .\n'
        if label:
            sparql += '       ?permsetIri rdfs:label ?label .\n'
        if permissionSetId or definedByProject or givesPermission or label:
            sparql += '       FILTER('
            use_and = False
            if permissionSetId:
                sparql += f'CONTAINS(STR(?permsetIri), "{Xsd_string.escaping(permissionSetId)}")'
                use_and = True
            if definedByProject:
                if use_and:
                    sparql += ' && '
                sparql += f'?definedByProject = {definedByProject.toRdf}'
                use_and = True
            if givesPermission:
                if use_and:
                    sparql += ' && '
                sparql += f'?givesPermission = {givesPermission.toRdf}'
                use_and = True
            if label:
                if use_and:
                    sparql += ' && '
                if label.lang:
                    sparql += f'?label = {label.toRdf}'
                else:
                    sparql += f'CONTAINS(STR(?label), "{Xsd_string.escaping(label.value)}")'
            sparql += ')\n'
        sparql += '    }\n'
        sparql += '}\n'
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        permissionSets: list[Iri] = []
        for r in res:
            if definedByProject:
                #context[r['projectShortName']] = r['namespaceIri']
                psqname = r['permsetIri'].as_qname or context.iri2qname(str(r['permsetIri']), validate=False)
                permissionSets.append(psqname or r['permsetIri'])
            else:
                permissionSets.append(r['permsetIri'])
        return permissionSets

    def update(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Update a changed permission set
        :param indent: Internal use (indent of SPARQL text)
        :type indent: int
        :param indent_inc: Internal use (indent increment of SPARQL text)
        :type indent_inc: int
        :return: None
        :rtype: None
        :raises OldapErrorUpdateFailed: Update failed
        """
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)
        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)
        blank = ''
        sparql_list = []

        for attr, change in self._changeset.items():
            if attr == PermissionSetAttr.LABEL or attr == PermissionSetAttr.COMMENT:
                if change.action == Action.MODIFY:
                    sparql_list.extend(self._attributes[attr].update(graph=Xsd_QName('oldap:admin'),
                                                                     subject=self.__permset_iri,
                                                                     field=attr.value))
                if change.action == Action.DELETE or change.action == Action.REPLACE:
                    sparql = self._changeset[attr].old_value.delete(graph=Xsd_QName('oldap:admin'),
                                                            subject=self.__permset_iri,
                                                            field=attr.value)
                    sparql_list.append(sparql)
                if change.action == Action.CREATE or change.action == Action.REPLACE:
                    sparql = self._attributes[attr].create(graph=Xsd_QName('oldap:admin'),
                                                            subject=self.__permset_iri,
                                                            field=attr.value)
                    sparql_list.append(sparql)
                continue
            sparql = f'{blank:{indent * indent_inc}}# PermissionSet attribute "{attr.value}" with action "{change.action.value}"\n'
            sparql += f'{blank:{indent * indent_inc}}WITH oldap:admin\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?project {attr.value} {change.old_value.toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?project {attr.value} {self._attributes[attr].toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.__permset_iri.toRdf} as ?project)\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?project {attr.value} {change.old_value.toRdf} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        sparql = context.sparql_context
        sparql += " ;\n".join(sparql_list)

        self._con.transaction_start()
        try:
            self._con.transaction_update(sparql)
            self.set_modified_by_iri(Xsd_QName('oldap:admin'), self.__permset_iri, self._modified, timestamp)
            modtime = self.get_modified_by_iri(Xsd_QName('oldap:admin'), self.__permset_iri)
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
        cache = CacheSingleton()
        cache.set(self.__permset_iri, self)


    def delete(self) -> None:
        """
        Delete the given permission set.
        :return: None
        :rtype: None
        """
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        DELETE WHERE {{
            GRAPH oldap:admin {{
                {self.__permset_iri.toRdf} a oldap:PermissionSet .
                {self.__permset_iri.toRdf} ?prop ?val .
            }}
        }} 
        """
        # TODO: use transaction for error handling
        self._con.update_query(sparql)
        cache = CacheSingleton()
        cache.delete(self.__permset_iri)


if __name__ == '__main__':
    context = Context(name="DEFAULT")
    connection = Connection(server='http://localhost:7200',
                                 repo="oldap",
                                 userId="rosenth",
                                 credentials="RioGrande",
                                 context_name="DEFAULT")
    ps = PermissionSet(con=connection,
                       permissionSetId="test4_ps",
                       label=LangString("test4@en", "test4@Perm@de"),
                       comment=LangString("Testing a PermissionSet 4@en", "Test eines PermissionSet 4@Perm@de"),
                       givesPermission=DataPermission.DATA_UPDATE,
                       definedByProject='britnet')
    ps2 = deepcopy(ps)
    print(ps.definedByProject)
    print(ps2.definedByProject)