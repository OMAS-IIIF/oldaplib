from dataclasses import dataclass
from datetime import datetime
from enum import unique, Enum
from typing import Dict, List, Optional, Set

from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NCName, AnyIRI, QName, Action
from omaslib.src.helpers.omaserror import OmasErrorAlreadyExists
from omaslib.src.helpers.permissions import AdminPermission, DataPermission
from omaslib.src.helpers.query_processor import QueryProcessor, StringLiteral
from omaslib.src.helpers.serializer import serializer

InProjectType = Dict[str, List[AdminPermission]]

UserFieldTypes = StringLiteral | AnyIRI | NCName | QName | List[QName] | InProjectType | datetime | bool | None

@dataclass
class UserFieldChange:
    old_value: UserFieldTypes
    action: Action

@unique
class UserFields(Enum):
    USER_IRI = "USER_IRI"
    USER_ID = 'omas:userId'
    FAMILY_NAME = 'foaf:familyName'
    GIVEN_NAME = 'foaf:givenName'
    CREDENTIALS = 'omas:credentials'
    ACTIVE = 'omas:active'
    IN_PROJECT = 'omas:inProject'
    HAS_PERMISSIONS = 'omas:hasPermissions'


@serializer
class UserDataclass:
    __creator: AnyIRI | None
    __created: datetime | None
    __contributor: AnyIRI | None
    __modified: datetime | None
    __userIri: AnyIRI | None
    __userId: NCName | None

    __fields: Dict[UserFields, UserFieldTypes]

    #__familyName: StringLiteral | None
    #__givenName: StringLiteral | None
    #__credentials: StringLiteral | None
    #__inProject: Dict[str, List[AdminPermission]] | None
    #__hasPermissions: List[QName] | None
    #__active: bool | None
    __change_set: Dict[UserFields, UserFieldChange]

    def __init__(self, *,
                 creator: AnyIRI | None = None,
                 created: datetime | None = None,
                 contributor: AnyIRI | None = None,
                 modified: datetime | None = None,
                 user_iri: AnyIRI | None = None,
                 user_id: NCName | None = None,
                 family_name: str | StringLiteral | None = None,
                 given_name: str | StringLiteral | None = None,
                 credentials: str | StringLiteral | None = None,
                 active: bool | None = None,
                 in_project: Dict[QName, List[AdminPermission]] | None = None,
                 has_permissions: List[QName] | None = None):
        self.__fields = {}
        if in_project:
            __in_project = {str(key): val for key, val in in_project.items()}
        else:
            __in_project = {}
        self.__creator = creator
        self.__created = created
        self.__contributor = contributor
        self.__modified = modified
        self.__userIri = user_iri
        self.__fields[UserFields.USER_ID] = user_id
        self.__fields[UserFields.FAMILY_NAME] = StringLiteral(family_name)
        self.__fields[UserFields.GIVEN_NAME] = StringLiteral(given_name)
        self.__fields[UserFields.CREDENTIALS] = StringLiteral(credentials)
        self.__fields[UserFields.ACTIVE] = active
        self.__fields[UserFields.IN_PROJECT] = __in_project
        self.__fields[UserFields.HAS_PERMISSIONS] = has_permissions or []
        self.__change_set = {}

    def __str__(self) -> str:
        admin_permissions = {}
        for proj, permissions in self.__fields[UserFields.IN_PROJECT].items():
            admin_permissions[str(proj)] = [str(x.value) for x in permissions]
        return \
        f'Userdata for <{self.__userIri}>:\n'\
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

    def _as_dict(self) -> dict:
        return {
                'user_iri': self.__userIri,
                'user_id': self.__fields[UserFields.USER_ID],
                'active': self.__fields[UserFields.ACTIVE],
                'has_permissions': self.__fields[UserFields.HAS_PERMISSIONS],
                'in_project': self.__fields[UserFields.IN_PROJECT]
        }

    def __change_setter(self, field: UserFields, value: UserFieldTypes) -> None:
        if self.__fields[field] == value:
            return
        if self.__fields[field] is None:
            self.__change_set[field] = UserFieldChange(None, Action.CREATE)
        else:
            if value is None:
                self.__change_set[field] = UserFieldChange(self.__fields[field], Action.DELETE)
            else:
                self.__change_set[field] = UserFieldChange(self.__fields[field], Action.REPLACE)
        self.__fields[field] = value


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

    @property
    def familyName(self) -> StringLiteral:
        return self.__fields[UserFields.FAMILY_NAME]

    @familyName.setter
    def familyName(self, value: str | StringLiteral) -> None:
        self.__change_setter(UserFields.FAMILY_NAME, StringLiteral(value))

    @property
    def givenName(self) -> StringLiteral:
        return self.__fields[UserFields.GIVEN_NAME]

    @givenName.setter
    def givenName(self, value: str | StringLiteral) -> None:
        self.__change_setter(UserFields.GIVEN_NAME, value)

    @property
    def credentials(self) -> StringLiteral:
        return self.__fields[UserFields.CREDENTIALS]

    @credentials.setter
    def credentials(self, value: StringLiteral) -> None:
        self.__change_setter(UserFields.CREDENTIALS, value)

    @property
    def user_id(self) -> NCName:
        return self.__fields[UserFields.USER_ID]

    @user_id.setter
    def user_id(self, value: StringLiteral) -> None:
        self.__change_setter(UserFields.USER_ID, value)

    @property
    def user_iri(self) -> AnyIRI:
        return self.__userIri

    @user_iri.setter
    def user_iri(self, value: AnyIRI) -> None:
        if self.__userIri is None:
            self.__change_setter("userIri", value)
        else:
            OmasErrorAlreadyExists(f'A user IRI already has been assigned: "{self.__userIri}".')

    @property
    def active(self) -> bool:
        return self.__fields[UserFields.ACTIVE]

    @active.setter
    def active(self, value: bool) -> None:
        self.__change_setter(UserFields.ACTIVE, value)

    @property
    def in_project(self) -> Dict[QName, List[AdminPermission]]:
        return {QName(key): val for key, val in self.__fields[UserFields.IN_PROJECT].items()} if self.__fields[UserFields.IN_PROJECT] else {}

    @property
    def has_permissions(self) -> List[QName]:
        return self.__fields[UserFields.HAS_PERMISSIONS]

    @property
    def changeset(self) -> Dict[UserFields, UserFieldChange]:
        return self.__change_set

    @staticmethod
    def sparql_query(context: Context, user_id: NCName) -> str:
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?user ?prop ?val ?proj ?rval
        FROM omas:admin
        WHERE {{
            {{
                ?user a omas:User .
                ?user omas:userId "{user_id}"^^xsd:NCName .
                ?user ?prop ?val .
            }} UNION {{
                ?user a omas:User .
                ?user omas:userId "{user_id}"^^xsd:NCName .
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
                    self.__userIri = r['user']
                case 'dcterms:created':
                    self.__created = r['val']
                case 'dcterms:contributor':
                    self.__contributor = r['val']
                case 'dcterms:modified':
                    self.__modified = r['val']
                case 'omas:userId':
                    self.__fields[UserFields.USER_ID] = StringLiteral(r['val'])
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
                    self.__fields[UserFields.HAS_PERMISSIONS].append(r['val'])
                case _:
                    if r.get('proj') and r.get('rval'):
                        if self.__fields[UserFields.IN_PROJECT].get(str(r['proj'])) is None:
                            self.__fields[UserFields.IN_PROJECT][str(r['proj'])] = []
                        self.__fields[UserFields.IN_PROJECT][str(r['proj'])].append(AdminPermission(str(r['rval'])))

    def sparql_update(self, indent: int = 0, indent_inc: int = 4):
        blank = ''
        sparql_list = []
        for field, change in self.__change_set.items():
            sparql = f'{blank:{indent * indent_inc}}# User field "{field.value} with action {change.action.value}\n'
            sparql += f'{blank:{indent * indent_inc}}WITH omas:admin\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?user {field.value} ?val .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?user {field.value} {repr(self.__fields[field])} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({repr(self.user_iri)} as ?user)\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?user {field.value} {repr(change.old_value)}\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)

        return " ;\n".join(sparql_list)




