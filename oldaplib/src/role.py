from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Dict, Self, Any

from typing import Dict, Self, Any
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from functools import partial

from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.connection import Connection
from oldaplib.src.enums.roleattr import RoleAttr
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.enums.roleattr import RoleAttr
from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.action import Action
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.helpers.tools import lprint
from oldaplib.src.project import Project
from oldaplib.src.enums.projectattr import ProjectAttr
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorAlreadyExists, OldapErrorNoPermission, \
    OldapError, \
    OldapErrorInconsistency, OldapErrorUpdateFailed, OldapErrorImmutable, OldapErrorNotFound, OldapErrorInUse
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.xsd.xsd_string import Xsd_string


#@strict
@serializer
class Role(Model):
    """
    Represents a Role, typically for use in a semantic knowledge-based system.

    This class provides methods to define, manage, and manipulate Roles, which specify
    data access permissions within a project. It includes methods for creating permissions in
    a triple store, validating consistency, and managing notifications for changes to attributes.

    Roles are uniquely identified by their association with a project and their ID.
    The class ensures that operations are consistent within a defined project context and
    permissions are compliant with system access controls.

    :ivar iri: The unique IRI of the role, derived from the project and permission set ID.
    :type iri: Iri
    """

    __role_iri: Xsd_QName | None
    __project: Project | None

    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | str |None = None,
                 created: Xsd_dateTime | datetime | str | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | datetime | str | None = None,
                 validate: bool = False,
                 **kwargs):
        """
        This constructor initializes a permission set instance.

        A permission set represents a defined set of permissions belonging to a specific
        project. It combines information such as label, comments, permissions granted,
        and the defining project. The initialization process ensures that provided data
        is consistent according to the constraints defined by the project and assigns
        correct IRIs to the permission set.

        :param con: Connection to manage the data within the permission set.
        :type con: IConnection
        :param creator: Creator of the permission set (internal use).
        :type creator: Iri | str | None
        :param created: Timestamp indicating when the permission set was created
            (internal use).
        :type created: Xsd_dateTime | datetime | str | None
        :param contributor: Contributor associated with the permission set (internal use).
        :type contributor: Iri | None
        :param modified: Timestamp indicating the last modification of the permission set
            (internal use).
        :type modified: Xsd_dateTime | datetime | str | None
        :param validate: Flag indicating whether to validate values upon initialization.
        :type validate: bool
        :param kwargs: Additional arguments for dynamic attributes.
        :type kwargs: Any
        :raises OldapErrorNoFound: Raised if the project defined by the identifier does
            not exist.
        """
        super().__init__(connection=con,
                         creator=creator,
                         created=created,
                         contributor=contributor,
                         modified=modified,
                         validate=validate)
        self.__project = None
        self.set_attributes(kwargs, RoleAttr)
        #
        # Consistency checks
        #
        if self._attributes.get(RoleAttr.DEFINED_BY_PROJECT):
            self.check_consistency(RoleAttr.DEFINED_BY_PROJECT, self._attributes[RoleAttr.DEFINED_BY_PROJECT])

        #
        # The IRI of the permission set is a QName consisting of the prefix of the project (aka projectShortname)
        # and the permissionSetId. Thus, the same permission set ID could be used in different projects...
        #
        self.__role_iri = Xsd_QName(self.__project.projectShortName, self._attributes[RoleAttr.ROLE_ID])
        #self.__permset_iri = Iri.fromPrefixFragment(self.__project.projectShortName, self._attributes[PermissionSetAttr.PERMISSION_SET_ID], validate=False)

        for attr in RoleAttr:
            setattr(Role, attr.value.fragment, property(
                partial(Role._get_value, attr=attr),
                partial(Role._set_value, attr=attr),
                partial(Role._del_value, attr=attr)))
        self._changeset = {}

    def update_notifier(self):
        for attr, value in self._attributes.items():
            if getattr(value, 'set_notifier', None) is not None:
                value.set_notifier(self.notifier, attr)

    def _as_dict(self):
        return {x.fragment: y for x, y in self._attributes.items()} | super()._as_dict()

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
        instance.__role_iri = deepcopy(self.__role_iri, memo)
        instance.__project = deepcopy(self.__project, memo)
        return instance

    def check_consistency(self, attr: RoleAttr, value: Any) -> None:
        if attr == RoleAttr.DEFINED_BY_PROJECT:
            if not isinstance(value, Project):
                self.__project = Project.read(self._con, value)
                self._attributes[attr] = self.__project.projectIri

    def check_for_permissions(self) -> (bool, str):
        """
        Internal method to check if a user may modify role.
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
                return False, f'Actor has no ADMIN_ROLES permission for project {self.definedByProject}'
            else:
                if AdminPermission.ADMIN_ROLES not in actor.inProject.get(self.definedByProject):
                    return False, f'Actor has no ADMIN_ROLES permission for project {self.definedByProject}'
            return True, "OK"

    def notifier(self, what: RoleAttr, value: Any = None) -> None:
        self._changeset[what] = AttributeChange(None, Action.MODIFY)

    @property
    def iri(self) -> Xsd_QName:
        return self.__role_iri

    @property
    def qname(self) -> Xsd_QName:
        return self.__role_iri

    def trig_to_str(self, created: Xsd_dateTime, modified: Xsd_dateTime, indent: int = 0, indent_inc: int = 4):
        blank = ''
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}} {self.__role_iri.toRdf} a oldap:Role'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:created {created.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:modified {modified.toRdf}'
        for attr, value in self._attributes.items():
            if attr.value.prefix == 'virtual' or not value:
                continue
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}{attr.value.toRdf} {value.toRdf}'
        return sparql


    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Creates and stores a role in the triple store.

        The method handles creating SPARQL queries to insert data related to
        the given role. The data includes metadata such as creator,
        creation timestamp, contributors, and other attributes defined in the
        role. It also ensures that no duplicate roles exists
        before attempting insertion. The changes are managed as a transaction,
        and the cache is updated upon successful persistence.

        :param indent: Indentation for the SPARQL text.
        :param indent_inc: Increment value for indentation in SPARQL text.
        :return: None
        :raises OldapError: If no connection is present.
        :raises OldapErrorNoPermission: If the user does not have the required
            permissions to create the permission set.
        :raises OldapErrorAlreadyExists: If a permission set with the given IRI
            already exists.
        :raises OldapError: If an error occurs during transaction operations.
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
        SELECT ?role
        FROM oldap:admin
        WHERE {{
            ?role a oldap:Role .
            FILTER(?role = {self.__role_iri.toRdf})       
        }}
        """

        timestamp = Xsd_dateTime()
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH oldap:admin {{\n'

        sparql += self.trig_to_str(created=timestamp, modified=timestamp, indent=indent + 2, indent_inc=indent_inc)
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
            raise OldapErrorAlreadyExists(f'A role "{self.__role_iri}" already exists')

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
        cache = CacheSingletonRedis()
        cache.set(self.__role_iri, self)

    @classmethod
    def read(cls, *,
             con: IConnection,
             qname: Xsd_QName | str | None = None,
             roleId: Xsd_NCName | str | None = None,
             definedByProject: Project | Iri | Xsd_NCName | str | None = None,
             ignore_cache: bool = False) -> Self:
        """
        Reads a specific permission set from the system using its unique identifier within the
        context of a project or using its Internationalized Resource Identifier (IRI). Returns
        an instance of the permission set if found.

        :param con: The connection object used to interact with the system.
        :param qname: The Internationalized Resource Identifier of the permission set. If provided,
                    it will be used to read the permission set.
        :param roleId: The unique identifier of the permission set within a project.
                                Required if `iri` is not provided.
        :param definedByProject: The project either as an object, its IRI, or its short name
                                 which defines the namespace of the permission set. This is
                                 required alongside `permissionSetId` if `iri` is not provided.
        :param ignore_cache: If set to True, the method bypasses the cache and reads fresh data
                             directly from the source.

        :return: An instance of the requested permission set.

        :raises OldapErrorNotFound: Raised if the permission set cannot be found in the system.
        :raises OldapErrorValue: Raised if both `iri` and the combination of `permissionSetId`
                                 and `definedByProject` are missing.
        :raises OldapErrorInconsistency: Raised if the permission set contains inconsistencies
                                         in its data during retrieval.
        """
        context = Context(name=con.context_name)
        if qname:
            role_iri = Xsd_QName(qname, validate=True)
        elif roleId and definedByProject:
            id = Xsd_NCName(roleId, validate=True)

            if isinstance(definedByProject, Project):
                project = definedByProject
            else:
                project = Project.read(con, definedByProject)
            role_iri = Xsd_QName(project.projectShortName, roleId)
        else:
            raise OldapErrorValue('Either the parameter "iri" of both "roleId" and "definedByProject" must be provided.')
        if not ignore_cache:
            cache = CacheSingletonRedis()
            tmp = cache.get(role_iri, connection=con)
            if tmp is not None:
                tmp.update_notifier()
                return tmp
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?role ?p ?o
        FROM oldap:admin
        WHERE {{
            BIND({role_iri.toRdf} as ?role)
            ?role a oldap:Role .
            ?role ?p ?o .
        }}
        """
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OldapErrorNotFound(f'No permission set "{role_iri}"')

        role_iri: Xsd_QName | None = None
        creator: Iri | None = None
        created: Xsd_dateTime | None = None
        contributor: Iri | None = None
        modified: Xsd_dateTime | None = None
        label: LangString = LangString()
        comment: LangString = LangString()
        _roleId: Xsd_NCName | None = None
        _definedByProject: Iri | None = None
        for r in res:
            if not role_iri:
                try:
                    permset_iri = r['role']
                except Exception as e:
                    raise OldapErrorInconsistency(f'Invalid project identifier "{r['o']}".')
                if not permset_iri.is_qname:
                    raise OldapErrorInconsistency(f'Invalid project identifier "{r['o']}".')
                _roleId = permset_iri.fragment
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
                case 'oldap:definedByProject':
                    _definedByProject = r['o']
        cls.__role_iri = role_iri
        if comment:
            comment.clear_changeset()
            comment.set_notifier(cls.notifier, Xsd_QName(RoleAttr.LABEL.value))
        if label:
            label.clear_changeset()
            label.set_notifier(cls.notifier, Xsd_QName(RoleAttr.LABEL.value))
        instance = cls(con=con,
                       roleId=Xsd_NCName(_roleId, validate=False),
                       creator=creator,
                       created=created,
                       contributor=contributor,
                       modified=modified,
                       label=label,
                       comment=comment,
                       definedByProject=Iri(_definedByProject, validate=False))
        cache = CacheSingletonRedis()
        cache.set(instance.__role_iri, instance)
        return instance

    @staticmethod
    def search(con: IConnection, *,
               roleId: str | None = None,
               definedByProject: Iri | str | None = None,
               label: Xsd_string | str | None = None) -> list[Iri | Xsd_QName]:
        """
        Search for a permission set. At least one of the search criteria is required. Multiple search criteria are
        combined using a logical AND.

        :param con: A valid Connection object.
        :type con: IConnection
        :param roleId: Search for the given ID. The given string must be _contained_ in the ID (substring).
        :type roleId: str | None
        :param definedByProject: The project which is responsible for the permission set.
        :type definedByProject: Iri | str | None
        :param label: The label string. The given string must be within at least one language label.
        :type label: Xsd_string | str | None
        :return: A list of permission set IRIs (possibly as Xsd_QName).
        :rtype: list[Iri | Xsd_QName]

        :raises OldapError: If the connection is not valid or another non-specified error occurs.
        :raises OldapErrorValue: If the search criteria are not valid.
        """
        if definedByProject:
            definedByProject = Iri(definedByProject, validate=True)
        label = Xsd_string(label, validate=True)
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        if definedByProject:
            sparql += 'SELECT DISTINCT ?roleIri ?namespaceIri ?projectShortName'
            context = Context(name=con.context_name)
        else:
            sparql += 'SELECT DISTINCT ?roleIri'
        sparql += '\n'
        sparql += 'FROM NAMED oldap:admin\n'
        sparql += 'WHERE {\n'
        sparql += '   GRAPH oldap:admin {\n'
        sparql += '       ?roleIri rdf:type oldap:Role .\n'
        if definedByProject:
            sparql += '       ?roleIri oldap:definedByProject ?definedByProject .\n'
            sparql += '       ?definedByProject oldap:namespaceIri ?namespaceIri .\n'
            sparql += '       ?definedByProject oldap:projectShortName ?projectShortName .\n'
        if label:
            sparql += '       ?roleIri rdfs:label ?label .\n'
        if roleId or definedByProject or label:
            sparql += '       FILTER('
            use_and = False
            if roleId:
                sparql += f'CONTAINS(STR(?roleIri), "{Xsd_string.escaping(roleId)}")'
                use_and = True
            if definedByProject:
                if use_and:
                    sparql += ' && '
                sparql += f'?definedByProject = {definedByProject.toRdf}'
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
        roles: list[Xsd_QName] = []
        for r in res:
            if definedByProject:
                #context[r['projectShortName']] = r['namespaceIri']
                psqname = r['roleIri'].as_qname or context.iri2qname(str(r['roleIri']), validate=False)
                roles.append(psqname or r['roleIri'])
            else:
                roles.append(r['roleIri'])
        return roles

    def update(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Update a changed permission set.

        This method is responsible for preparing and executing updates to
        the permission set based on the tracked changes. It interacts with
        a SPARQL database to apply changes atomically and ensure data
        consistency.

        :param indent: Internal use (indent of SPARQL text)
        :type indent: int
        :param indent_inc: Internal use (indent increment of SPARQL text)
        :type indent_inc: int
        :return: None
        :rtype: None
        :raises OldapErrorUpdateFailed: Update failed
        :raises OldapErrorNoPermission: Insufficient permissions to perform the update
        """
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)
        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)
        blank = ''
        sparql_list = []

        for attr, change in self._changeset.items():
            if attr == RoleAttr.LABEL or attr == RoleAttr.COMMENT:
                if change.action == Action.MODIFY:
                    sparql_list.extend(self._attributes[attr].update(graph=Xsd_QName('oldap:admin'),
                                                                     subject=self.__role_iri,
                                                                     field=attr.value))
                if change.action == Action.DELETE or change.action == Action.REPLACE:
                    sparql = self._changeset[attr].old_value.delete(graph=Xsd_QName('oldap:admin'),
                                                                    subject=self.__role_iri,
                                                                    field=attr.value)
                    sparql_list.append(sparql)
                if change.action == Action.CREATE or change.action == Action.REPLACE:
                    sparql = self._attributes[attr].create(graph=Xsd_QName('oldap:admin'),
                                                           subject=self.__role_iri,
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
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.__role_iri.toRdf} as ?project)\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?project {attr.value} {change.old_value.toRdf} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        sparql = context.sparql_context
        sparql += " ;\n".join(sparql_list)

        self._con.transaction_start()
        try:
            self._con.transaction_update(sparql)
            self.set_modified_by_iri(Xsd_QName('oldap:admin'), self.__role_iri, self._modified, timestamp)
            modtime = self.get_modified_by_iri(Xsd_QName('oldap:admin'), self.__role_iri)
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
        cache = CacheSingletonRedis()
        cache.set(self.__role_iri, self)


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
        # first check if the permission set is assigned to a user
        #
        query1 = context.sparql_context
        query1 += f"""
        ASK FROM oldap:admin
        WHERE {{
            ?user a oldap:User ;
            oldap:hasRole {self.__role_iri.toRdf} .
        }}
        """

        #
        # now check if the permission set is used by a data object (resource)
        #
        query2 = context.sparql_context
        query2 += f"""
        ASK {{
            GRAPH ?graph {{
                ?instance oldap:attachedToRole {self.__role_iri.toRdf} .
            }}
        }}
        """

        return query1, query2

    def in_use(self) -> bool:
        """
        Checks if the current object is in use by executing a series
        of database queries within a transaction. If any of the queries
        return a boolean value indicating 'True', the object is considered
        to be in use, and the transaction is aborted. Otherwise, the
        transaction is committed.

        :return: True if the object is in use, otherwise False
        :rtype: bool
        """
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
        Deletes a specific permission set by identifying its associated RDF resource
        and removing it from the context graph. The method verifies if the permission
        set is in use by checking relevant queries against users and data objects. If
        the permission set is assigned to users or data objects, deletion is aborted,
        and an error is raised. The method also performs transactional operations to
        handle any modifications or failures during the deletion process. After
        successful deletion, the associated cache entry is removed.

        :raises OldapErrorNoPermission: If the current user lacks permissions to
            delete the permission set.
        :raises OldapErrorInUse: If the permission set is assigned to either users
            or data objects.
        :raises OldapError: For any general error encountered during the operation.
        :return: None
        :rtype: None

        :raises OldapErrorNoPermission: Insufficient permissions to perform the update
        :raises OldapErrorInUse: Role is still in use
        :raises OldapError: For any general error encountered during the operation.
        """
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        query1, query2 = self.in_use_queries()
        context = Context(name=self._con.context_name)
        #
        # Now delete the permission set
        #
        sparql = context.sparql_context
        sparql += f"""
        DELETE WHERE {{
            GRAPH oldap:admin {{
                {self.__role_iri.toRdf} ?prop ?val .
            }}
        }} 
        """

        self._con.transaction_start()
        try:
            result1 = self._con.query(query1)
            if result1['boolean']:
                raise OldapErrorInUse(f"Permission set is still assigned to some users")
            result2 = self._con.query(query2)
            if result2['boolean']:
                raise OldapErrorInUse("Permission set is still assigned to some data objects")
            self._con.transaction_update(sparql)
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        cache = CacheSingletonRedis()
        cache.delete(self.__role_iri)

