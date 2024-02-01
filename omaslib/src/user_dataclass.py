from dataclasses import dataclass
from datetime import datetime
from enum import unique, Enum
from functools import partial
from typing import Dict, List, Self, Set, Tuple

import bcrypt

from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NCName, AnyIRI, QName, Action
from omaslib.src.helpers.observable_set import ObservableSet
from omaslib.src.helpers.omaserror import OmasErrorAlreadyExists
from omaslib.src.helpers.permissions import AdminPermission
from omaslib.src.helpers.query_processor import QueryProcessor, StringLiteral
from omaslib.src.helpers.serializer import serializer

InProjectType = Dict[str, List[AdminPermission]]

UserFieldTypes = StringLiteral | AnyIRI | NCName | QName | ObservableSet[QName] | InProjectType | datetime | bool | None


@dataclass
class UserFieldChange:
    old_value: UserFieldTypes
    action: Action

@unique
class UserFields(Enum):
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
    __datatypes = {
        UserFields.USER_IRI: AnyIRI,
        UserFields.USER_ID: NCName,
        UserFields.FAMILY_NAME: str,
        UserFields.GIVEN_NAME: str,
        UserFields.CREDENTIALS: str,
        UserFields.ACTIVE: bool,
        UserFields.IN_PROJECT: InProjectType,
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
                 inProject: Dict[QName, List[AdminPermission]] | None = None,
                 hasPermissions: Set[QName] | None = None):
        self.__fields = {}
        if inProject:
            __inProject = {str(key): val for key, val in inProject.items()}
        else:
            __inProject = {}
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
        self.__fields[UserFields.IN_PROJECT] = __inProject
        self.__fields[UserFields.HAS_PERMISSIONS] = hasPermissions
        self.__change_set = {}
        #
        # here we dynamically generate class properties for the UserFields.
        # This we can access these properties either a Dict or as property
        # for get, set and sel:
        # - user[UserFields.USER_ID]
        # - user.userId
        #
        for field in UserFields:
            prefix, name = field.value.split(':')
            setattr(UserDataclass, name, property(
                partial(self.__get_value, field=field),
                partial(self.__set_value, field=field),
                partial(self.__del_value, field=field)))
        self.clear_changeset()

    def __get_value(self: Self, self2: Self, field: UserFields) -> UserFieldTypes:
        return self.__fields.get(field)

    def __set_value(self: Self, self2: Self, value: UserFieldTypes, field: UserFields) -> None:
        if field == UserFields.CREDENTIALS:
            salt = bcrypt.gensalt()
            value = bcrypt.hashpw(str(value).encode('utf-8'), salt).decode('utf-8')
        if field == UserFields.USER_IRI and self.__fields.get(UserFields.USER_IRI) is not None:
            OmasErrorAlreadyExists(f'A user IRI already has been assigned: "{repr(self.__fields.get(UserFields.USER_IRI))}".')
        self.__change_setter(field, value)

    def __del_value(self: Self, self2: Self, field: UserFields) -> None:
        del self.__fields[field]

    def __str__(self) -> str:
        admin_permissions = {}
        for proj, permissions in self.__fields[UserFields.IN_PROJECT].items():
            admin_permissions[str(proj)] = [str(x.value) for x in permissions]
        return \
        f'Userdata for {repr(self.__fields[UserFields.USER_IRI])}:\n'\
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
        self.__fields[field] = self.__datatypes[field](value)

    def __hasPermission_cb(self, oldset: ObservableSet):
        if self.__change_set.get(UserFields.HAS_PERMISSIONS) is None:
            self.__change_set[UserFields.HAS_PERMISSIONS] = UserFieldChange(oldset, Action.MODIFY)

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

    @property
    def changeset(self) -> Dict[UserFields, UserFieldChange]:
        return self.__change_set

    def clear_changeset(self):
        self.__change_set = {}

    @staticmethod
    def sparql_query(context: Context, userId: NCName) -> str:
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

    def create_from_queryresult(self,
                                queryresult: QueryProcessor):
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
                    self.__fields[UserFields.IN_PROJECT] = {str(r['val']): []}
                case 'omas:hasPermissions':
                    self.__fields[UserFields.HAS_PERMISSIONS].add(r['val'])
                case _:
                    if r.get('proj') and r.get('rval'):
                        if self.__fields[UserFields.IN_PROJECT].get(str(r['proj'])) is None:
                            self.__fields[UserFields.IN_PROJECT][str(r['proj'])] = []
                        self.__fields[UserFields.IN_PROJECT][str(r['proj'])].append(AdminPermission(str(r['rval'])))
        if not isinstance(self.__modified, datetime):
            raise Exception(f"Modified field is {type(self.__modified)} and not datetime!!!!")
        self.clear_changeset()

    def sparql_update(self, indent: int = 0, indent_inc: int = 4) -> Tuple[str | None, int, str]:
        ptest = None
        ptest_len = 0
        blank = ''
        sparql_list = []
        for field, change in self.__change_set.items():
            if field == UserFields.HAS_PERMISSIONS:
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

        return ptest, ptest_len, " ;\n".join(sparql_list)


if __name__ == "__main__":
    user_dataclass = UserDataclass(
        userIri=AnyIRI("https://orcid.org/0000-0002-9991-2055"),
        userId=NCName("edison"),
        family_name="Edison",
        given_name="Thomas A.",
        credentials="Lightbulb&Phonograph",
        inProject={QName('omas:HyperHamlet'): [AdminPermission.ADMIN_USERS,
                                                AdminPermission.ADMIN_RESOURCES,
                                                AdminPermission.ADMIN_CREATE]},
        hasPermissions=[QName('omas:GenericView')])
    print(user_dataclass.userId)
