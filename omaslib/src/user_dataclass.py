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

- `InProjectType`: Defines the user's membership to projects and the administrative permission
   within these projects


## Helper classes

- `UserFieldChange`: Bookkeeping of changes to the fields
- `UserFields`: Enum class of the data fields provided by the `UserDataclass`

"""
from dataclasses import dataclass
from datetime import datetime
from enum import unique, Enum
from typing import Dict, Self, Set, Tuple, Any

import bcrypt

from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NCName, AnyIRI, QName, Action, StringLiteral
from omaslib.src.helpers.observable_set import ObservableSet
from omaslib.src.helpers.omaserror import OmasErrorAlreadyExists, OmasErrorValue
from omaslib.src.helpers.permissions import AdminPermission
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.serializer import serializer
from omaslib.src.in_project import InProjectClass

# InProjectType = Dict[str, ObservableSet[AdminPermission]]


UserFieldTypes = StringLiteral | AnyIRI | NCName | QName | ObservableSet[QName] | InProjectClass | datetime | str | bool | None


@dataclass
class UserFieldChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: UserFieldTypes
    action: Action


@unique
class UserFields(Enum):
    """
    Enumeration that defined the data fields (properties)

    - _UserFields.USER_IRI_ (RDF: 'omas:userIri')
    - _UserFields.USER_ID_ (RDF: 'omas:userId')
    - _UserFields.FAMILY_NAME_ (RDF: 'foaf:familyName=
    - _UserFields.GIVEN_NAME_ (RDF: 'foaf:givenName')
    - _UserFields.CREDENTIALS_ (RDF: 'omas:credentials')
    - _UserFields.ACTIVE_ (RDF: 'omas:active')
    - _UserFields.IN_PROJECT_ (RDF: 'omas:inProject')
    - _UserFields.HAS_PERMISSIONS_ (RDF: 'omas:hasPermissions')

    """
    USER_IRI = 'omas:userIri'
    USER_ID = 'omas:userId'
    FAMILY_NAME = 'foaf:familyName'
    GIVEN_NAME = 'foaf:givenName'
    CREDENTIALS = 'omas:credentials'
    ACTIVE = 'omas:active'
    IN_PROJECT = 'omas:inProject'
    HAS_PERMISSIONS = 'omas:hasPermissions'


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

    - _userIri_: IRI of the user, cannot be changed (RDF property `omas:userIri`)
    - _userId_: User ID as NCName (RDF property `omas:)
    - _familyName_: Family name as str (RDF property `foaf:familyName`)
    - _givenName_: Given name or first name as str(RDF property `foaf:givenName`)
    - _credentials_: Credential (password) (RDF property `omas:credentials`)
    - _active_: Is the user active as bool? (RDF property `omas:active`)
    - _inProject_: Membership to projects and administrative permissions for this project (RDF property `omas:inProject)
    - _hsPermission_: Permissions for data as sets of QNames (RDF property `omas:hasPermissions`)

    These properties can be accessed as normal python class properties or using the dictionary syntax. The keys
    are defined in the [UserFields](/python_docstrings/userdataclass/#omaslib.src.user_dataclass.UserFields) Enum class.
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
        UserFields.USER_IRI: AnyIRI,
        UserFields.USER_ID: NCName,
        UserFields.FAMILY_NAME: str,
        UserFields.GIVEN_NAME: str,
        UserFields.CREDENTIALS: str,
        UserFields.ACTIVE: bool,
        UserFields.IN_PROJECT: dict,
        UserFields.HAS_PERMISSIONS: ObservableSet[QName]
    }

    __creator: AnyIRI | None
    __created: datetime | None
    __contributor: AnyIRI | None
    __modified: datetime | None

    __fields: Dict[UserFields, UserFieldTypes]

    __change_set: Dict[UserFields, UserFieldChange]

    def __init__(self, *,
                 creator: AnyIRI | None = None,
                 created: datetime | None = None,
                 contributor: AnyIRI | None = None,
                 modified: datetime | None = None,
                 userIri: AnyIRI | None = None,
                 userId: NCName | None = None,
                 family_name: str | StringLiteral | None = None,
                 given_name: str | StringLiteral | None = None,
                 credentials: str | StringLiteral | None = None,
                 active: bool | None = None,
                 inProject: Dict[QName | AnyIRI, Set[AdminPermission]] | None = None,
                 hasPermissions: Set[QName] | None = None):
        """
        Constructs a new UserDataclass
        :param creator: AnyIRI of the creator of this UserDataclass
        :param created: datetime of the creation of this UserDataclass
        :param contributor: AnyIRI of the contributor of this UserDataclass
        :param modified: datetime of the modification of this UserDataclass
        :param userIri: AnyIRI of the User to be used for this UserDataclass
        :param userId: A unique identifier for the user (NCName, must be unique)
        :param family_name: The foaf:family name of the User
        :param given_name: The foaf:givenname of the User
        :param credentials: The password
        :param active: A boolean indicating if the user is active
        :param inProject: an InProjectType instance for the project permissions of the user
        :param hasPermissions: Set of Administrative Permissions for the user
        """
        self.__fields = {}
        if inProject:
            inProjectTmp = InProjectClass(inProject, self.__inProject_cb)
        else:
            inProjectTmp = InProjectClass()
        if not isinstance(hasPermissions, ObservableSet):
            hasPermissions = ObservableSet(hasPermissions, on_change=self.__hasPermission_cb)
        if credentials is not None:
            salt = bcrypt.gensalt()
            credentials = bcrypt.hashpw(str(credentials).encode('utf-8'), salt).decode('utf-8')

        self.__creator = creator
        self.__created = created
        self.__contributor = contributor
        self.__modified = modified
        self.__fields[UserFields.USER_IRI] = AnyIRI(userIri) if userIri else None
        self.__fields[UserFields.USER_ID] = NCName(userId) if userId else None
        self.__fields[UserFields.FAMILY_NAME] = StringLiteral(family_name)
        self.__fields[UserFields.GIVEN_NAME] = StringLiteral(given_name)
        self.__fields[UserFields.CREDENTIALS] = StringLiteral(credentials)
        self.__fields[UserFields.ACTIVE] = bool(active)
        self.__fields[UserFields.IN_PROJECT] = inProjectTmp
        self.__fields[UserFields.HAS_PERMISSIONS] = hasPermissions
        self.__change_set = {}
        #
        # here we dynamically generate class properties for the UserFields.
        # This we can access these properties either a Dict or as property
        # for get, set and sel:
        # - user[UserFields.USER_ID]
        # - user.userId
        #
        # for field in UserFields:
        #     prefix, name = field.value.split(':')
        #     setattr(UserDataclass, name, property(
        #         partial(self.__get_value, field=field),
        #         partial(self.__set_value, field=field),
        #         partial(self.__del_value, field=field)))
        self.clear_changeset()


    #
    # these are the methods for the getter, setter and deleter
    #
    def __get_value(self, field: UserFields) -> UserFieldTypes | None:
        return self.__fields.get(field)

    def __set_value(self: Self, value: UserFieldTypes, field: UserFields) -> None:
        if field == UserFields.CREDENTIALS:
            salt = bcrypt.gensalt()
            value = bcrypt.hashpw(str(value).encode('utf-8'), salt).decode('utf-8')
        if field == UserFields.USER_IRI and self.__fields.get(UserFields.USER_IRI) is not None:
            OmasErrorAlreadyExists(f'A user IRI already has been assigned: "{repr(self.__fields.get(UserFields.USER_IRI))}".')
        self.__change_setter(field, value)

    def __del_value(self: Self, field: UserFields) -> None:
        del self.__fields[field]

    @property
    def userIri(self) -> AnyIRI:
        return self.__get_value(UserFields.USER_IRI)

    @userIri.setter
    def userIri(self, value: AnyIRI) -> None:
        self.__set_value(value, UserFields.USER_IRI)

    @userIri.deleter
    def userIri(self) -> None:
        self.__del_value(UserFields.USER_IRI)

    @property
    def userId(self) -> NCName:
        return self.__get_value(UserFields.USER_ID)

    @userId.setter
    def userId(self, value: NCName) -> None:
        self.__set_value(value, UserFields.USER_ID)

    @userId.deleter
    def userId(self) -> None:
        self.__del_value(UserFields.USER_ID)

    @property
    def familyName(self) -> str:
        return self.__get_value(UserFields.FAMILY_NAME)

    @familyName.setter
    def familyName(self, value: str) -> None:
        self.__set_value(value, UserFields.FAMILY_NAME)

    @familyName.deleter
    def familyName(self) -> None:
        self.__del_value(UserFields.FAMILY_NAME)

    @property
    def givenName(self) -> str:
        return self.__get_value(UserFields.GIVEN_NAME)

    @givenName.setter
    def givenName(self, value: str) -> None:
        self.__set_value(value, UserFields.GIVEN_NAME)

    @givenName.deleter
    def givenName(self) -> None:
        self.__del_value(UserFields.GIVEN_NAME)

    @property
    def credentials(self) -> str:
        return self.__get_value(UserFields.CREDENTIALS)

    @credentials.setter
    def credentials(self, value: str) -> None:
        self.__set_value(value, UserFields.CREDENTIALS)

    @credentials.deleter
    def credentials(self) -> None:
        self.__del_value(UserFields.CREDENTIALS)

    @property
    def active(self) -> bool:
        return self.__get_value(UserFields.ACTIVE)

    @active.setter
    def active(self, value: bool) -> None:
        self.__set_value(value, UserFields.ACTIVE)

    @active.deleter
    def active(self) -> None:
        self.__del_value(UserFields.ACTIVE)

    @property
    def inProject(self) -> InProjectClass:
        return self.__get_value(UserFields.IN_PROJECT)

    @inProject.setter
    def inProject(self, value: InProjectClass) -> None:
        self.__set_value(value, UserFields.IN_PROJECT)

    @property
    def hasPermissions(self) -> ObservableSet[QName]:
        return self.__get_value(UserFields.HAS_PERMISSIONS)

    @hasPermissions.setter
    def hasPermissions(self, value: ObservableSet[QName]) -> None:
        self.__set_value(value, UserFields.HAS_PERMISSIONS)

    @hasPermissions.deleter
    def hasPermissions(self) -> None:
        self.__del_value(UserFields.HAS_PERMISSIONS)

    def __str__(self) -> str:
        """
        Create a string representation for the human reader
        :return: Multiline string
        """
        admin_permissions = {}
        for proj, permissions in self.__fields[UserFields.IN_PROJECT].items():
            admin_permissions[str(proj)] = [str(x.value) for x in permissions]
        return \
            f'Userdata for {repr(self.__fields[UserFields.USER_IRI])}:\n' \
            f'  Creator: {self.__creator}\n' \
            f'  Created at: {self.__created}\n' \
            f'  Modified by: {self.__contributor}\n' \
            f'  Modified at: {self.__modified}\n' \
            f'  User id: {self.__fields[UserFields.USER_ID]}\n' \
            f'  Family name: {self.__fields[UserFields.FAMILY_NAME]}\n' \
            f'  Given name: {self.__fields[UserFields.GIVEN_NAME]}\n' \
            f'  Active: {self.__fields[UserFields.ACTIVE]}\n' \
            f'  In project: {admin_permissions}\n' \
            f'  Has permissions: {self.__fields[UserFields.HAS_PERMISSIONS]}\n'

    #
    # The fields of the class can either be accessed using the dict-semantic or as
    # named properties. Here we implement the dict semantic
    #
    def __getitem__(self, item: UserFields) -> UserFieldTypes:
        return self.__fields.get(item)

    def __setitem__(self, field: UserFields, value: UserFieldTypes) -> None:
        if field == UserFields.CREDENTIALS:
            salt = bcrypt.gensalt()
            value = bcrypt.hashpw(str(value).encode('utf-8'), salt).decode('utf-8')
        if field == UserFields.USER_IRI and self.__fields.get(UserFields.USER_IRI) is not None:
            OmasErrorAlreadyExists(f'A user IRI already has been assigned: "{repr(self.__fields.get(UserFields.USER_IRI))}".')
        self.__change_setter(field, value)

    def _as_dict(self) -> dict:
        return {
            'userIri': repr(self.__fields.get(UserFields.USER_IRI)),
            'userId': self.__fields[UserFields.USER_ID],
            'active': self.__fields[UserFields.ACTIVE],
            'hasPermissions': self.__fields[UserFields.HAS_PERMISSIONS],
            'inProject': self.__fields[UserFields.IN_PROJECT]
        }

    #
    # this private method handles the setting of a field. Whenever a field is being
    # set or modified, this method is called. It also puts the original value and the
    # action into the changeset.
    #
    def __change_setter(self, field: UserFields, value: UserFieldTypes) -> None:
        if self.__fields[field] == value:
            return
        if self.__fields[field] is None:
            if self.__change_set.get(field) is None:
                self.__change_set[field] = UserFieldChange(None, Action.CREATE)
        else:
            if value is None:
                if self.__change_set.get(field) is None:
                    self.__change_set[field] = UserFieldChange(self.__fields[field], Action.DELETE)
            else:
                if self.__change_set.get(field) is None:
                    self.__change_set[field] = UserFieldChange(self.__fields[field], Action.REPLACE)
        if value is None:
            del self.__fields[field]
            if field == UserFields.IN_PROJECT:
                self.__fields[field] = InProjectClass(on_change=self.__inProject_cb)
            elif field == UserFields.HAS_PERMISSIONS:
                self.__fields[field] = ObservableSet(on_change=self.__hasPermission_cb)
        else:
            if field == UserFields.IN_PROJECT:
                self.__fields[field] = InProjectClass(value, on_change=self.__inProject_cb)
            elif field == UserFields.HAS_PERMISSIONS:
                self.__fields[field] = ObservableSet(value, on_change=self.__hasPermission_cb)
            else:
                self.__fields[field] = self.__datatypes[field](value)

    #
    # Callbacks for the `ObservableSet`class. This is used whenever the `hasPermission`or
    # `inProject`properties are being modified
    #
    def __hasPermission_cb(self, oldset: ObservableSet, data: Any = None) -> None:
        if self.__change_set.get(UserFields.HAS_PERMISSIONS) is None:
            self.__change_set[UserFields.HAS_PERMISSIONS] = UserFieldChange(oldset, Action.MODIFY)

    def __inProject_cb(self, key: QName | AnyIRI, old: ObservableSet[AdminPermission] | None = None) -> None:
        if self.__change_set.get(UserFields.IN_PROJECT) is None:
            old = self.__fields[UserFields.IN_PROJECT].copy()
            self.__change_set[UserFields.IN_PROJECT] = UserFieldChange(old, Action.MODIFY)

    @property
    def creator(self) -> AnyIRI | None:
        return self.__creator

    @property
    def created(self) -> datetime | None:
        return self.__created

    @property
    def contributor(self) -> AnyIRI | None:
        return self.__contributor

    @property
    def modified(self) -> datetime | None:
        return self.__modified

    @modified.setter
    def modified(self, value: datetime) -> None:
        self.__modified = value

    def add_project_permission(self, project: QName | AnyIRI | str, permission: AdminPermission | None) -> None:
        """
        Adds a new administraive permission to the user. If the user is not yet member of the project, he
        will automatically become a member.

        :param project: Name of the project to add the permission
        :type project: QName
        :param permission: The admin permission to be added
        :type permission: AdminPermission | None
        :return: None
        """
        if self.__fields[UserFields.IN_PROJECT].get(project) is None:
            if self.__change_set.get(UserFields.IN_PROJECT) is None:
                self.__change_set[UserFields.IN_PROJECT] = UserFieldChange(self.__fields[UserFields.IN_PROJECT], Action.CREATE)
            self.__fields[UserFields.IN_PROJECT][project] = ObservableSet({permission})
        else:
            if self.__change_set.get(UserFields.IN_PROJECT) is None:
                self.__change_set[UserFields.IN_PROJECT] = UserFieldChange(self.__fields[UserFields.IN_PROJECT], Action.MODIFY)
            self.__fields[UserFields.IN_PROJECT][project].add(permission)

    def remove_project_permission(self, project: QName | AnyIRI | str, permission: AdminPermission | None) -> None:
        """
        Remove the given Permission from the user (for the given project)

        :param project: Name of the project
        :type project: QName
        :param permission: The permission to be removed
        :type permission: AdminPermission | None
        :return:
        """
        if self.__fields[UserFields.IN_PROJECT].get(str(project)) is None:
            raise OmasErrorValue(f"Project '{project}' does not exist")
        if self.__change_set.get(UserFields.IN_PROJECT) is None:
            self.__change_set[UserFields.IN_PROJECT] = UserFieldChange(self.__fields[UserFields.IN_PROJECT], Action.MODIFY)
        self.__fields[UserFields.IN_PROJECT][project].remove(permission)

    @property
    def changeset(self) -> Dict[UserFields, UserFieldChange]:
        """
        Return the changeset, that is dicst with information about all properties that have benn changed.
        :return: A dictionary of all changes
        """
        return self.__change_set

    def clear_changeset(self):
        """
        Clear the changeset.
        :return:
        """
        self.__change_set = {}

    @staticmethod
    def sparql_query(context: Context, userId: NCName) -> str:
        """
        Return the SPARQL query that retrieves the given user from the triple store
        :param context: A `Context` instance
        :type context: Context
        :param userId: The user if
        :type userId: NCName
        :return: SPARQL query
        """
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?user ?prop ?val ?proj ?rval
        FROM omas:admin
        WHERE {{
            {{
                ?user a omas:User .
                ?user omas:userId "{userId}"^^xsd:NCName .
                ?user ?prop ?val .
            }} UNION {{
                ?user a omas:User .
                ?user omas:userId "{userId}"^^xsd:NCName .
                <<?user omas:inProject ?proj>> omas:hasAdminPermission ?rval
            }}
        }}
        """
        return sparql

    def _create_from_queryresult(self,
                                 queryresult: QueryProcessor) -> None:
        """
        Create a user from a queryresult created by the method
        :param queryresult:
        :type queryresult: QueryProcessor
        :return: None
        """
        in_project: Dict[str, Set[AdminPermission]] | None = None
        for r in queryresult:
            match str(r.get('prop')):
                case 'dcterms:creator':
                    self.__creator = r['val']
                    self.__fields[UserFields.USER_IRI] = r['user']
                case 'dcterms:created':
                    self.__created = r['val']
                case 'dcterms:contributor':
                    self.__contributor = r['val']
                case 'dcterms:modified':
                    self.__modified = r['val']
                case 'omas:userId':
                    self.__fields[UserFields.USER_ID] = NCName(r['val'])
                case 'foaf:familyName':
                    self.__fields[UserFields.FAMILY_NAME] = StringLiteral(r['val'])
                case 'foaf:givenName':
                    self.__fields[UserFields.GIVEN_NAME] = StringLiteral(r['val'])
                case 'omas:credentials':
                    self.__fields[UserFields.CREDENTIALS] = StringLiteral(r['val'])
                case 'omas:isActive':
                    self.__fields[UserFields.ACTIVE] = r['val']
                case 'omas:inProject':
                    in_project = {r['val']: set()}
                    # self.__fields[UserFields.IN_PROJECT] = {str(r['val']): ObservableSet()}
                case 'omas:hasPermissions':
                    self.__fields[UserFields.HAS_PERMISSIONS].add(r['val'])
                case _:
                    if r.get('proj') and r.get('rval'):
                        if in_project.get(r['proj']) is None:
                            in_project[r['proj']] = set()
                        in_project[r['proj']].add(AdminPermission(str(r['rval'])))
                        # if self.__fields[UserFields.IN_PROJECT].get(str(r['proj'])) is None:
                        #    self.__fields[UserFields.IN_PROJECT][str(r['proj'])] = ObservableSet()
                        # self.__fields[UserFields.IN_PROJECT][str(r['proj'])].add(AdminPermission(str(r['rval'])))
        if in_project:
            self.__fields[UserFields.IN_PROJECT] = InProjectClass(in_project, on_change=self.__inProject_cb)
        if not isinstance(self.__modified, datetime):
            raise Exception(f"Modified field is {type(self.__modified)} and not datetime!!!!")
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
        for field, change in self.__change_set.items():
            if field == UserFields.HAS_PERMISSIONS or field == UserFields.IN_PROJECT:
                continue
            sparql = f'{blank:{indent * indent_inc}}# User field "{field.value}" with action "{change.action.value}"\n'
            sparql += f'{blank:{indent * indent_inc}}WITH omas:admin\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?user {field.value} {repr(change.old_value)} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?user {field.value} {repr(self.__fields[field])} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({repr(self.userIri)} as ?user)\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?user {field.value} {repr(change.old_value)} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        if UserFields.HAS_PERMISSIONS in self.__change_set:
            new_set = self.__fields[UserFields.HAS_PERMISSIONS]
            old_set = self.__change_set[UserFields.HAS_PERMISSIONS].old_value
            added = new_set - old_set
            removed = old_set - new_set
            sparql = f'{blank:{indent * indent_inc}}# User field "hasPermission"\n'
            sparql += f'{blank:{indent * indent_inc}}WITH omas:admin\n'
            if removed:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                for perm in removed:
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?user omas:hasPermissions {perm} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if added:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                for perm in added:
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?user omas:hasPermissions {perm} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({repr(self.userIri)} as ?user)\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?user a omas:User .\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)

            #
            # check if existing :PermissionSet's have been given!
            #
            if added:
                ptest = f"""
                SELECT ?permissionset
                FROM omas:admin
                WHERE {{
                    ?permissionset a omas:PermissionSet .
                    FILTER(?permissionset IN ({repr(added)}))
                }}
                """
                ptest_len = len(added) if added else 0

        if UserFields.IN_PROJECT in self.__change_set:
            # first get all keys that must be added, that is that are in NEW but not in OLD:
            addedprojs = self.__fields[UserFields.IN_PROJECT].keys() - self.__change_set[UserFields.IN_PROJECT].old_value.keys()
            deletedprojs = self.__change_set[UserFields.IN_PROJECT].old_value.keys() - self.__fields[UserFields.IN_PROJECT].keys()
            changedprojs = self.__fields[UserFields.IN_PROJECT].keys() & self.__change_set[UserFields.IN_PROJECT].old_value.keys()

            # add projects
            if addedprojs:
                sparql = f"{blank:{indent * indent_inc}}INSERT DATA {{\n"
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH omas:admin {{\n'
                for proj in addedprojs:
                    sparql += f'{blank:{(indent + 2) * indent_inc}}{repr(self.userIri)} omas:inProject {proj} .\n'
                    for perm in self.__fields[UserFields.IN_PROJECT][proj]:
                        sparql += f'{blank:{(indent + 2) * indent_inc}}<<<{self.userIri}> omas:inProject {proj}>> omas:hasAdminPermission {perm.value} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql_list.append(sparql)

            # delete projects
            if deletedprojs:
                sparql = f"{blank:{indent * indent_inc}}DELETE DATA {{\n"
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH omas:admin {{\n'
                for proj in deletedprojs:
                    sparql += f'{blank:{(indent + 2) * indent_inc}}{repr(self.userIri)} omas:inProject {proj} .\n'
                    for perm in self.__change_set[UserFields.IN_PROJECT].old_value[proj]:
                        sparql += f'{blank:{(indent + 2) * indent_inc}}<<<{self.userIri}> omas:inProject {proj}>> omas:hasAdminPermission {perm.value} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql_list.append(sparql)

            if changedprojs:
                doit = False
                sparql = f"{blank:{indent * indent_inc}}INSERT DATA {{\n"
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH omas:admin {{\n'
                for proj in changedprojs:
                    perms = self.__fields[UserFields.IN_PROJECT][proj] - self.__change_set[UserFields.IN_PROJECT].old_value[proj]
                    for perm in perms:
                        sparql += f'{blank:{(indent + 2) * indent_inc}}<<<{self.userIri}> omas:inProject {proj}>> omas:hasAdminPermission {perm.value} .\n'
                        doit = True
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
                if doit:
                    sparql_list.append(sparql)

                doit = False
                sparql = f"{blank:{indent * indent_inc}}DELETE DATA {{\n"
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH omas:admin {{\n'
                for proj in changedprojs:
                    perms = self.__change_set[UserFields.IN_PROJECT].old_value[proj] - self.__fields[UserFields.IN_PROJECT][proj]
                    for perm in perms:
                        sparql += f'{blank:{(indent + 2) * indent_inc}}<<<{self.userIri}> omas:inProject {proj}>> omas:hasAdminPermission {perm.value} .\n'
                        doit = True
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
                if doit:
                    sparql_list.append(sparql)

            # print("\nUPDATING IN_PROJECT...... Not Yet Implemented")
            # print("OLD: ", self.__change_set[UserFields.IN_PROJECT].old_value)
            # print("NEW: ", self.__fields[UserFields.IN_PROJECT])

        return ptest, ptest_len, " ;\n".join(sparql_list)


if __name__ == "__main__":
    user_dataclass = UserDataclass(
        userIri=AnyIRI("https://orcid.org/0000-0002-9991-2055"),
        userId=NCName("edison"),
        family_name="Edison",
        given_name="Thomas A.",
        credentials="Lightbulb&Phonograph",
        inProject={QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                               AdminPermission.ADMIN_RESOURCES,
                                               AdminPermission.ADMIN_CREATE}},
        hasPermissions={QName('omas:GenericView')})
    print(user_dataclass.userId)
