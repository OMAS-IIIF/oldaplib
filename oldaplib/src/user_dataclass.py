"""
# UserDataclass

This module implements the UserDataclass class which can be used to represent all
information about a user in the oldap universe.

The class internally represents the properties of the given user in a hidden dict.
The properties however can be accessed directly as if the class itself is a dict
or using "virtual" properties which are implemented as dynamically created getter,
setter and deleter methods.

## Use of UserDataclass

1. The UserDataclass is the base class for the `User`-class which is usually the standard
   way to access a OLDAP user. The `User`-class, in contrary to the `UserDataclass`, implements
   the CRUD operations.
2. The UserDataclass is used by the `Connection`-class for checking the authorization of the user.
   During the construction of the `Connection`-instance it must rely on direct access to the triple
   store to retrieve the user's data. The instance of the `UserDataclass` is then serialized in a
   JSON Web token.

## Other classes used by the UserDataclass

- [InProjectClass](/python_docstrings/datatypes#oldap.src.in_project):
  Defines the user's membership to projects and the administrative permission within these projects
- [RdfSet](/python_docstrings/datatypes#oldap.src.dtypes/rdfset):)


## Helper classes

- `UserFieldChange`: Bookkeeping of changes to the fields
- `UserFields`: Enum class of the data fields provided by the `UserDataclass`

"""
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Dict, Self, Set, Tuple, Any

import bcrypt

from oldaplib.src.enums.userdataclassattr import UserAttr
from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.action import Action
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_string import Xsd_string
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.helpers.oldaperror import OldapErrorAlreadyExists, OldapErrorValue, OldapErrorNotFound
from oldaplib.src.enums.permissions import AdminPermission
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.in_project import InProjectClass


UserAttrTypes = Xsd | ObservableSet[Iri] | InProjectClass | str | bool | None


@dataclass
class UserAttrChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: UserAttrTypes
    action: Action


@serializer
class UserDataclass:
    """
    The UserDataclass class implements the main handling of the user data of an oldap user. The
    UserDataclass class is the base class for the User class which implements the CRUD operations
    with the RDF store. Therefore, the UserDataclass class does not inherit from model since it
    does not need the connection instance. The class internally represents the properties of the
    given user in a hidden dict. The properties however can be accessed directly as if the class
    itself is a dict or using "virtual" properties which are implemented as dynamically created
    getter, setter and deleter methods.

    The User class inherits the following properties from the UserDataclass class:

    - `userIri: Iri` [mandatory]: IRI of the user, cannot be changed (RDF property `oldap:userIri`).
      If available, the [ORCID](https://orcid.org) should be used as Iri.
    - `userId_: Xsd_NCname | str` [mandatory]: User ID as NCName (RDF property `oldap:). Must be unique!
    - `familyName: Xsd_string | str` [mandatory]: Family name as str (RDF property `foaf:familyName`)
    - `givenName: Xsd_string | str` [mandatory]: Given name or first name as str(RDF property `foaf:givenName`)
    - `credentials: Xsd_string | str` [mandatory]: Credential (password) (RDF property `oldap:credentials`)
    - `active: Xsd_boolean | bool | None` [optional]: Is the user isActive as bool? (RDF property `oldap:isActive`)
    - `inProject: Dict[Iri | str, Set[AdminPermission]] | None `: Membership to projects and administrative permissions for this project (RDF property `oldap:inProject)
    - _hsPermission_: Permissions for data as sets of QNames (RDF property `oldap:hasPermissions`)

    These properties can be accessed as normal python class properties or using the dictionary syntax. The keys
    are defined in the [UserFields](/python_docstrings/userdataclass/#oldap.src.user_dataclass.UserFields) Enum class.
    Example for access as property:
    ```python
    user.familyName = 'Rosenthaler'
    givenname = user.givenName
    del user.givenName
    ```
    Example for access as dictionary:
    ```python
    user[UserFields.FAMILY_NAME] = 'Rosenthaler'
    givenname = user[UserFields.GIVEN_NAME]
    del user[UserFields.GIVEN_NAME]
    ```
    The class implements the following methods:

    - *UserDataclass(...)*: Constructor method for the class
    - *str()*: String representation of the class for printing
    - *add_project_permission(...)*: If the project does already exists, adds the given permission.
      If the project does not exist, it also adds the project.
    - *remove_project_permission(...)*: Removes the given permission
    """
    __datatypes = {
        UserAttr.USER_IRI: Iri,
        UserAttr.USER_ID: Xsd_NCName,
        UserAttr.FAMILY_NAME: Xsd_string,
        UserAttr.GIVEN_NAME: Xsd_string,
        UserAttr.CREDENTIALS: Xsd_string,
        UserAttr.ACTIVE: Xsd_boolean,
        UserAttr.IN_PROJECT: dict,
        UserAttr.HAS_PERMISSIONS: ObservableSet[Iri]
    }

    _creator: Iri | None
    _created: Xsd_dateTime | None
    _contributor: Iri | None
    _modified: Xsd_dateTime | None

    __attr: Dict[UserAttr, UserAttrTypes]

    __changeset: Dict[UserAttr, UserAttrChange]

    def __init__(self, *,
                 creator: Iri | str | None = None,
                 created: Xsd_dateTime | datetime | str | None = None,
                 contributor: Iri | str | None = None,
                 modified: Xsd_dateTime | datetime | str | None = None,
                 userIri: Iri | str | None = None,
                 userId: Xsd_NCName | str | None = None,
                 familyName: Xsd_string | str | None = None,
                 givenName: Xsd_string | str | None = None,
                 credentials: Xsd_string | str | None = None,
                 isActive: Xsd_boolean | bool | None = None,
                 inProject: Dict[Iri | str, Set[AdminPermission]] | None = None,
                 hasPermissions: Set[Iri] | None = None):
        """
        Constructs a new UserDataclass
        :param creator: AnyIRI of the creator of this UserDataclass
        :param created: datetime of the creation of this UserDataclass
        :param contributor: AnyIRI of the contributor of this UserDataclass
        :param modified: datetime of the modification of this UserDataclass
        :param userIri: AnyIRI of the User to be used for this UserDataclass
        :param userId: A unique identifier for the user (NCName, must be unique)
        :param familyName: The foaf:family name of the User
        :param givenName: The foaf:givenname of the User
        :param credentials: The password
        :param isActive: A boolean indicating if the user is active
        :param inProject: an InProjectType instance for the project permissions of the user
        :param hasPermissions: Set of Administrative Permissions for the user
        """
        self.__attr = {}
        self.__changeset = {}
        if inProject:
            inProjectTmp = InProjectClass(inProject, self.__inProject_cb)
        else:
            inProjectTmp = InProjectClass()
        if not isinstance(hasPermissions, ObservableSet):
            hasPermissions = ObservableSet(hasPermissions, on_change=self.__hasPermission_cb)
        if credentials is not None:
            salt = bcrypt.gensalt()
            credentials = Xsd_string(bcrypt.hashpw(str(credentials).encode('utf-8'), salt).decode('utf-8'))

        self._creator = Iri(creator) if creator else None
        self._created = Xsd_dateTime(created) if created is not None else None
        self._contributor = Iri(contributor) if contributor else None
        self._modified = Xsd_dateTime(modified) if modified else None
        self.__attr[UserAttr.USER_IRI] = Iri(userIri) if userIri else None
        self.__attr[UserAttr.USER_ID] = Xsd_NCName(userId) if userId else None
        self.__attr[UserAttr.FAMILY_NAME] = Xsd_string(familyName) if familyName else None
        self.__attr[UserAttr.GIVEN_NAME] = Xsd_string(givenName) if givenName else None
        self.__attr[UserAttr.CREDENTIALS] = Xsd_string(credentials) if credentials else None
        self.__attr[UserAttr.ACTIVE] = Xsd_boolean(isActive) if isActive is not None else None
        self.__attr[UserAttr.IN_PROJECT] = inProjectTmp if inProjectTmp is not None else None
        self.__attr[UserAttr.HAS_PERMISSIONS] = hasPermissions if hasPermissions is not None else None
        #
        # here we dynamically generate class properties for the UserFields.
        # This we can access these properties either a Dict or as property
        # for get, set and sel:
        # - user[UserFields.USER_ID]
        # - user.userId
        #
        for field in UserAttr:
            prefix, name = field.value.split(':')
            setattr(UserDataclass, name, property(
                partial(UserDataclass.__get_value, field=field),
                partial(UserDataclass.__set_value, field=field),
                partial(UserDataclass.__del_value, field=field)))
        self.clear_changeset()
    #
    # these are the methods for the getter, setter and deleter
    #
    def __get_value(self: Self, field: UserAttr) -> UserAttrTypes | None:
        return self.__attr.get(field)

    def __set_value(self: Self, value: UserAttrTypes, field: UserAttr) -> None:
        if field == UserAttr.CREDENTIALS:
            salt = bcrypt.gensalt()
            value = bcrypt.hashpw(str(value).encode('utf-8'), salt).decode('utf-8')
        if field == UserAttr.USER_IRI and self.__attr.get(UserAttr.USER_IRI) is not None:
            OldapErrorAlreadyExists(f'A user IRI already has been assigned: "{self.__attr.get(UserAttr.USER_IRI)}".')
        self.__change_setter(field, value)

    def __del_value(self: Self, field: UserAttr) -> None:
        if self.__changeset.get(field) is None:
            self.__changeset[field] = UserAttrChange(self.__attr[field], Action.DELETE)
        del self.__attr[field]
        if field == UserAttr.IN_PROJECT:
            self.__attr[field] = InProjectClass(on_change=self.__inProject_cb)
        elif field == UserAttr.HAS_PERMISSIONS:
            self.__attr[field] = ObservableSet(on_change=self.__hasPermission_cb)

    def __str__(self) -> str:
        """
        Create a string representation for the human reader
        :return: Multiline string
        """
        admin_permissions = {}
        for proj, permissions in self.__attr[UserAttr.IN_PROJECT].items():
            admin_permissions[str(proj)] = [str(x.value) for x in permissions]
        return \
            f'Userdata for {self.__attr[UserAttr.USER_IRI]}:\n' \
            f'  Creator: {self._creator}\n' \
            f'  Created at: {self._created}\n' \
            f'  Modified by: {self._contributor}\n' \
            f'  Modified at: {self._modified}\n' \
            f'  User id: {self.__attr[UserAttr.USER_ID]}\n' \
            f'  Family name: {str(self.__attr[UserAttr.FAMILY_NAME])}\n' \
            f'  Given name: {str(self.__attr[UserAttr.GIVEN_NAME])}\n' \
            f'  Active: {self.__attr[UserAttr.ACTIVE]}\n' \
            f'  In project: {admin_permissions}\n' \
            f'  Has permissions: {self.__attr[UserAttr.HAS_PERMISSIONS]}\n'

    #
    # The fields of the class can either be accessed using the dict-semantic or as
    # named properties. Here we implement the dict semantic
    #
    def __getitem__(self, item: UserAttr) -> UserAttrTypes:
        if isinstance(self.__attr.get(item), Xsd_string):
            return str(self.__attr[item])
        return self.__attr.get(item)

    def __setitem__(self, field: UserAttr, value: UserAttrTypes) -> None:
        if field == UserAttr.CREDENTIALS:
            salt = bcrypt.gensalt()
            value = bcrypt.hashpw(str(value).encode('utf-8'), salt).decode('utf-8')
        if field == UserAttr.USER_IRI and self.__attr.get(UserAttr.USER_IRI) is not None:
            OldapErrorAlreadyExists(f'A user IRI already has been assigned: "{self.__attr.get(UserAttr.USER_IRI)}".')
        self.__change_setter(field, value)

    def _as_dict(self) -> dict:
        return {
                'userIri': self.__attr.get(UserAttr.USER_IRI),
                'userId': self.__attr[UserAttr.USER_ID],
                'familyName': self.__attr[UserAttr.FAMILY_NAME],
                'givenName': self.__attr[UserAttr.GIVEN_NAME],
                'isActive': self.__attr[UserAttr.ACTIVE],
                'hasPermissions': self.__attr[UserAttr.HAS_PERMISSIONS],
                'inProject': self.__attr[UserAttr.IN_PROJECT]
        }

    #
    # this private method handles the setting of a field. Whenever a field is being
    # set or modified, this method is called. It also puts the original value and the
    # action into the changeset.
    #
    def __change_setter(self, field: UserAttr, value: UserAttrTypes) -> None:
        if self.__attr[field] == value:
            return
        if self.__attr[field] is None:
            if self.__changeset.get(field) is None:
                self.__changeset[field] = UserAttrChange(None, Action.CREATE)
        else:
            if value is None:
                if self.__changeset.get(field) is None:
                    self.__changeset[field] = UserAttrChange(self.__attr[field], Action.DELETE)
            else:
                if self.__changeset.get(field) is None:
                    self.__changeset[field] = UserAttrChange(self.__attr[field], Action.REPLACE)
        if value is None:
            del self.__attr[field]
            if field == UserAttr.IN_PROJECT:
                self.__attr[field] = InProjectClass(on_change=self.__inProject_cb)
            elif field == UserAttr.HAS_PERMISSIONS:
                self.__attr[field] = ObservableSet(on_change=self.__hasPermission_cb)
        else:
            if field == UserAttr.IN_PROJECT:
                self.__attr[field] = InProjectClass(value, on_change=self.__inProject_cb)
            elif field == UserAttr.HAS_PERMISSIONS:
                self.__attr[field] = ObservableSet(value, on_change=self.__hasPermission_cb)
            else:
                self.__attr[field] = self.__datatypes[field](value)

    #
    # Callbacks for the `ObservableSet`class. This is used whenever the `hasPermission`or
    # `inProject`properties are being modified
    #
    def __hasPermission_cb(self, oldset: ObservableSet, data: Any = None) -> None:
        if self.__changeset.get(UserAttr.HAS_PERMISSIONS) is None:
            self.__changeset[UserAttr.HAS_PERMISSIONS] = UserAttrChange(oldset, Action.MODIFY)

    def __inProject_cb(self, key: Iri, old: ObservableSet[AdminPermission] | None = None) -> None:
        if self.__changeset.get(UserAttr.IN_PROJECT) is None:
            old = None
            if self.__attr.get(UserAttr.IN_PROJECT) is not None:
                old = self.__attr[UserAttr.IN_PROJECT].copy()
            self.__changeset[UserAttr.IN_PROJECT] = UserAttrChange(old, Action.MODIFY)

    @property
    def creator(self) -> Iri | None:
        return self._creator

    @property
    def created(self) -> Xsd_dateTime | None:
        return self._created

    @property
    def contributor(self) -> Iri | None:
        return self._contributor

    @property
    def modified(self) -> Xsd_dateTime | None:
        return self._modified

    @modified.setter
    def modified(self, value: Xsd_dateTime) -> None:
        self._modified = value

    def add_project_permission(self, project: Iri | str, permission: AdminPermission | None) -> None:
        """
        Adds a new administraive permission to the user. If the user is not yet member of the project, he
        will automatically become a member.

        :param project: Name of the project to add the permission
        :type project: Xsd_QName
        :param permission: The admin permission to be added
        :type permission: AdminPermission | None
        :return: None
        """
        if self.__attr[UserAttr.IN_PROJECT].get(project) is None:
            if self.__changeset.get(UserAttr.IN_PROJECT) is None:
                self.__changeset[UserAttr.IN_PROJECT] = UserAttrChange(self.__attr[UserAttr.IN_PROJECT], Action.CREATE)
            self.__attr[UserAttr.IN_PROJECT][project] = ObservableSet({permission})
        else:
            if self.__changeset.get(UserAttr.IN_PROJECT) is None:
                self.__changeset[UserAttr.IN_PROJECT] = UserAttrChange(self.__attr[UserAttr.IN_PROJECT], Action.MODIFY)
            self.__attr[UserAttr.IN_PROJECT][project].add(permission)

    def remove_project_permission(self, project: Iri | str, permission: AdminPermission | None) -> None:
        """
        Remove the given Permission from the user (for the given project)

        :param project: Name of the project
        :type project: Xsd_QName
        :param permission: The permission to be removed
        :type permission: AdminPermission | None
        :return:
        """
        if not isinstance(project, Iri):
            project = Iri(project)
        if self.__attr[UserAttr.IN_PROJECT].get(project) is None:
            raise OldapErrorValue(f"Project '{project}' does not exist")
        if self.__changeset.get(UserAttr.IN_PROJECT) is None:
            self.__changeset[UserAttr.IN_PROJECT] = UserAttrChange(self.__attr[UserAttr.IN_PROJECT], Action.MODIFY)
        self.__attr[UserAttr.IN_PROJECT][project].remove(permission)

    @property
    def changeset(self) -> Dict[UserAttr, UserAttrChange]:
        """
        Return the changeset, that is dict with information about all properties that have benn changed.
        :return: A dictionary of all changes
        """
        return self.__changeset

    def clear_changeset(self):
        """
        Clear the changeset.
        :return:
        """
        self.__changeset = {}

    @staticmethod
    def sparql_query(context: Context, userId: Xsd_NCName) -> str:
        """
        Return the SPARQL query that retrieves the given user from the triple store
        :param context: A `Context` instance
        :type context: Context
        :param userId: The user if
        :type userId: Xsd_NCName
        :return: SPARQL query
        """
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?user ?prop ?val ?proj ?rval
        FROM oldap:admin
        WHERE {{
            {{
                ?user a oldap:User .
                ?user oldap:userId {userId.toRdf} .
                ?user ?prop ?val .
            }} UNION {{
                ?user a oldap:User .
                ?user oldap:userId {userId.toRdf} .
                <<?user oldap:inProject ?proj>> oldap:hasAdminPermission ?rval
            }}
        }}
        """
        return sparql

    def _create_from_queryresult(self, queryresult: QueryProcessor) -> None:
        """
        Create a user from a queryresult created by the method
        :param queryresult:
        :type queryresult: QueryProcessor
        :return: None
        :raises OldapErrorNotFound: Given user not found!
        """
        in_project: Dict[str, Set[AdminPermission]] | None = None
        if len(queryresult) == 0:
            raise OldapErrorNotFound("Given user not found!")
        for r in queryresult:
            match str(r.get('prop')):
                case 'dcterms:creator':
                    self._creator = r['val']
                    self.__attr[UserAttr.USER_IRI] = r['user']
                case 'dcterms:created':
                    self._created = r['val']
                case 'dcterms:contributor':
                    self._contributor = r['val']
                case 'dcterms:modified':
                    self._modified = r['val']
                case 'oldap:userId':
                    self.__attr[UserAttr.USER_ID] = r['val']
                case 'foaf:familyName':
                    self.__attr[UserAttr.FAMILY_NAME] = r['val']
                case 'foaf:givenName':
                    self.__attr[UserAttr.GIVEN_NAME] = r['val']
                case 'oldap:credentials':
                    self.__attr[UserAttr.CREDENTIALS] = r['val']
                case 'oldap:isActive':
                    self.__attr[UserAttr.ACTIVE] = r['val']
                case 'oldap:inProject':
                    in_project = {r['val']: set()}
                    # self.__fields[UserFields.IN_PROJECT] = {str(r['val']): ObservableSet()}
                case 'oldap:hasPermissions':
                    self.__attr[UserAttr.HAS_PERMISSIONS].add(r['val'])
                case _:
                    if r.get('proj') and r.get('rval'):
                        if in_project.get(r['proj']) is None:
                            in_project[r['proj']] = set()
                        in_project[r['proj']].add(AdminPermission(str(r['rval'])))
                        # if self.__fields[UserFields.IN_PROJECT].get(str(r['proj'])) is None:
                        #    self.__fields[UserFields.IN_PROJECT][str(r['proj'])] = ObservableSet()
                        # self.__fields[UserFields.IN_PROJECT][str(r['proj'])].add(AdminPermission(str(r['rval'])))
        if in_project:
            self.__attr[UserAttr.IN_PROJECT] = InProjectClass(in_project, on_change=self.__inProject_cb)
        if not isinstance(self._modified, Xsd_dateTime):
            raise OldapErrorValue(f"Modified field is {type(self._modified)} and not datetime!!!!")
        self.clear_changeset()

    def _sparql_update(self, indent: int = 0, indent_inc: int = 4) -> Tuple[str | None, int, str]:
        """
        return the sparql that performs a sparql query to update all the changes
        :param indent: SPARQL formatting indentation step
        :param indent_inc: SPARQL formatting indentation step size
        :return: A Tuple with three elements:
                 1. SPARQL query to test if the given permission set exists
                 2. The expected length of the result of ptest
                 3. The SPARQL to update the instance
        """
        ptest = None
        ptest_len = 0
        blank = ''
        sparql_list = []
        for field, change in self.__changeset.items():
            if field == UserAttr.HAS_PERMISSIONS or field == UserAttr.IN_PROJECT:
                continue
            sparql = f'{blank:{indent * indent_inc}}# User field "{field.value}" with action "{change.action.value}"\n'
            sparql += f'{blank:{indent * indent_inc}}WITH oldap:admin\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?user {field.value} {change.old_value.toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?user {field.value} {self.__attr[field].toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.userIri.toRdf} as ?user)\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?user {field.value} {change.old_value.toRdf} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        if UserAttr.HAS_PERMISSIONS in self.__changeset:
            new_set = self.__attr[UserAttr.HAS_PERMISSIONS]
            old_set = self.__changeset[UserAttr.HAS_PERMISSIONS].old_value
            added = new_set - old_set
            removed = old_set - new_set
            sparql = f'{blank:{indent * indent_inc}}# User field "hasPermission"\n'
            sparql += f'{blank:{indent * indent_inc}}WITH oldap:admin\n'
            if removed:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                for perm in removed:
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?user oldap:hasPermissions {perm} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if added:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                for perm in added:
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?user oldap:hasPermissions {perm} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.userIri.toRdf} as ?user)\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?user a oldap:User .\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            if removed or added:
                sparql_list.append(sparql)

            #
            # check if existing :PermissionSet's have been given!
            #
            if added:
                ptest = f"""
                SELECT ?permissionset
                FROM oldap:admin
                WHERE {{
                    ?permissionset a oldap:PermissionSet .
                    FILTER(?permissionset IN ({added.toRdf}))
                }}
                """
                ptest_len = len(added) if added else 0

        if UserAttr.IN_PROJECT in self.__changeset:
            # first get all keys that must be added, that is that are in NEW but not in OLD:
            addedprojs = self.__attr[UserAttr.IN_PROJECT].keys() - self.__changeset[UserAttr.IN_PROJECT].old_value.keys()
            deletedprojs = self.__changeset[UserAttr.IN_PROJECT].old_value.keys() - self.__attr[UserAttr.IN_PROJECT].keys()
            changedprojs = self.__attr[UserAttr.IN_PROJECT].keys() & self.__changeset[UserAttr.IN_PROJECT].old_value.keys()

            # add projects
            if addedprojs:
                sparql = f"{blank:{indent * indent_inc}}INSERT DATA {{\n"
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH oldap:admin {{\n'
                for proj in addedprojs:
                    sparql += f'{blank:{(indent + 2) * indent_inc}}{self.userIri.toRdf} oldap:inProject {proj.toRdf} .\n'
                    for perm in self.__attr[UserAttr.IN_PROJECT][proj]:
                        sparql += f'{blank:{(indent + 2) * indent_inc}}<<{self.userIri.toRdf} oldap:inProject {proj.toRdf}>> oldap:hasAdminPermission {perm.value} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql_list.append(sparql)

            # delete projects
            if deletedprojs:
                sparql = f"{blank:{indent * indent_inc}}DELETE DATA {{\n"
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH oldap:admin {{\n'
                for proj in deletedprojs:
                    sparql += f'{blank:{(indent + 2) * indent_inc}}{self.userIri.toRdf} oldap:inProject {proj.toRdf} .\n'
                    for perm in self.__changeset[UserAttr.IN_PROJECT].old_value[proj]:
                        sparql += f'{blank:{(indent + 2) * indent_inc}}<<{self.userIri.toRdf} oldap:inProject {proj.toRdf}>> oldap:hasAdminPermission {perm.value} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql_list.append(sparql)

            if changedprojs:
                doit = False
                sparql = f"{blank:{indent * indent_inc}}INSERT DATA {{\n"
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH oldap:admin {{\n'
                for proj in changedprojs:
                    perms = self.__attr[UserAttr.IN_PROJECT][proj] - self.__changeset[UserAttr.IN_PROJECT].old_value[proj]
                    for perm in perms:
                        sparql += f'{blank:{(indent + 2) * indent_inc}}<<{self.userIri.toRdf} oldap:inProject {proj.toRdf}>> oldap:hasAdminPermission {perm.value} .\n'
                        doit = True
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
                if doit:
                    sparql_list.append(sparql)

                doit = False
                sparql = f"{blank:{indent * indent_inc}}DELETE DATA {{\n"
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH oldap:admin {{\n'
                for proj in changedprojs:
                    perms = self.__changeset[UserAttr.IN_PROJECT].old_value[proj] - self.__attr[UserAttr.IN_PROJECT][proj]
                    for perm in perms:
                        sparql += f'{blank:{(indent + 2) * indent_inc}}<<{self.userIri.toRdf} oldap:inProject {proj.toRdf}>> oldap:hasAdminPermission {perm.value} .\n'
                        doit = True
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
                if doit:
                    sparql_list.append(sparql)
        return ptest, ptest_len, " ;\n".join(sparql_list)


if __name__ == "__main__":
    gaga = UserDataclass()
    user_dataclass = UserDataclass(
        userIri=Iri("https://orcid.org/0000-0002-9991-2055"),
        userId=Xsd_NCName("edison"),
        familyName="Edison",
        givenName="Tholdap A.",
        credentials="Lightbulb&Phonograph",
        inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                   AdminPermission.ADMIN_RESOURCES,
                                                   AdminPermission.ADMIN_CREATE}},
        hasPermissions={Xsd_QName('oldap:GenericView')})
    print(user_dataclass.userId)
