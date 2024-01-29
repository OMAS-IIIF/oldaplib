from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NCName, AnyIRI, QName
from omaslib.src.helpers.omaserror import OmasErrorAlreadyExists
from omaslib.src.helpers.permissions import AdminPermission, DataPermission
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.serializer import serializer


@serializer
class UserDataclass:
    __creator: AnyIRI | None
    __created: datetime | None
    __contributor: AnyIRI | None
    __modified: datetime | None
    __userId: NCName | None
    __userIri: AnyIRI | None
    __familyName: str | None
    __givenName: str | None
    __credentials: str | None
    __inProject: Dict[str, List[AdminPermission]] | None
    __hasPermissions: List[QName] | None
    __active: bool | None

    def __init__(self, *,
                 creator: AnyIRI | None = None,
                 created: datetime | None = None,
                 contributor: AnyIRI | None = None,
                 modified: datetime | None = None,
                 user_iri: AnyIRI | None = None,
                 user_id: NCName | None = None,
                 family_name: str | None = None,
                 given_name: str | None = None,
                 credentials: str | None = None,
                 active: bool | None = None,
                 in_project: Optional[Dict[QName, List[AdminPermission]]] = None,
                 has_permissions: Optional[List[QName]] = None):
        if in_project:
            __in_project = {str(key): val for key, val in in_project.items()}
        else:
            __in_project = {}
        self.__creator = creator
        self.__created = created
        self.__contributor = contributor
        self.__modified = modified
        self.__userIri = user_iri
        self.__userId = user_id
        self.__familyName = family_name
        self.__givenName = given_name
        self.__credentials = credentials
        self.__active = active
        self.__inProject = __in_project
        self.__hasPermissions = has_permissions or []

    def __str__(self) -> str:
        admin_permissions = {}
        for proj, permissions in self.__inProject.items():
            admin_permissions[str(proj)] = [str(x.value) for x in permissions]
        return \
        f'Userdata for <{self.__userIri}>:\n'\
        f'  Creator: {self.__creator}\n' \
        f'  Created at: {self.__created}\n' \
        f'  Modified by: {self.__contributor}\n' \
        f'  Modified at: {self.__modified}\n' \
        f'  User id: {self.__userId}\n' \
        f'  Family name: {self.__familyName}\n' \
        f'  Given name: {self.__givenName}\n' \
        f'  Active: {self.__active}\n' \
        f'  In project: {admin_permissions}\n' \
        f'  Has permissions: {self.__hasPermissions}\n'

    def _as_dict(self) -> dict:
        return {
                'user_iri': self.__userIri,
                'user_id': self.__userId,
                'active': self.__active,
                'has_permissions': self.__hasPermissions,
                'in_project': self.__inProject
        }

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
    def familyName(self) -> str:
        return self.__familyName

    @property
    def givenName(self) -> str:
        return self.__givenName

    @property
    def credentials(self) -> str:
        return self.__credentials

    @property
    def user_id(self) -> NCName:
        return self.__userId

    @property
    def user_iri(self) -> AnyIRI:
        return self.__userIri

    @user_iri.setter
    def user_iri(self, value: AnyIRI) -> None:
        if self.__userIri is None:
            self.__userIri = value
        else:
            OmasErrorAlreadyExists(f'A user IRI already has been assigned: "{self.__userIri}".')

    @property
    def active(self) -> bool:
        return self.__active

    @property
    def in_project(self) -> Dict[QName, List[AdminPermission]]:
        return {QName(key): val for key, val in self.__inProject.items()} if self.__inProject else {}

    @property
    def has_permissions(self) -> List[QName]:
        return self.__hasPermissions

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
                    self.__creatorcreator = r['val']
                    self.__userIri = r['user']
                case 'dcterms:created':
                    self.__creatod = r['val']
                case 'dcterms:contributor':
                    self.__contributor = r['val']
                case 'dcterms:modified':
                    self.__modified = r['val']
                case 'omas:userId':
                    self.__userId = r['val']
                case 'foaf:familyName':
                    self.__familyName = r['val']
                case 'foaf:givenName':
                    self.__givenName = r['val']
                case 'omas:credentials':
                    self.__credentials = r['val']
                case 'omas:isActive':
                    self.__active = r['val']
                case 'omas:inProject':
                    self.__inProject = {str(r['val']): []}
                case 'omas:hasPermissions':
                    self.__hasPermissions.append(r['val'])
                case _:
                    if r.get('proj') and r.get('rval'):
                        if self.__inProject.get(str(r['proj'])) is None:
                            self.__inProject[str(r['proj'])] = []
                        self.__inProject[str(r['proj'])].append(AdminPermission(str(r['rval'])))

