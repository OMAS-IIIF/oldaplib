from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NCName, AnyIRI, QName
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
    __inProjects: Dict[str, List[AdminPermission]] | None
    __hasPermissions: List[DataPermission] | None
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
                 in_projects: Optional[Dict[QName, List[AdminPermission]]] = None,
                 has_permissions: Optional[List[DataPermission]] = None):
        if in_projects:
            __in_projects = {str(key): val for key, val in in_projects.items()}
        else:
            __in_projects = {}
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
        self.__inProjects = __in_projects
        self.__hasPermissions = has_permissions or []

    def __str__(self) -> str:
        admin_permissions = {}
        for proj, permissions in self.__inProjects.items():
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
        f'  In projects: {admin_permissions}\n' \
        f'  Has permissions: {self.__hasPermissions}\n'

    def _as_dict(self) -> dict:
        return {
                'user_iri': self.__userIri,
                'user_id': self.__userId,
                'active': self.__active,
                'has_permissions': self.__hasPermissions,
                'in_projects': self.__inProjects
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

    @property
    def active(self) -> bool:
        return self.__active

    @property
    def in_projects(self) -> Dict[QName, List[AdminPermission]]:
        return {QName(key): val for key, val in self.__inProjects.items()} if self.__inProjects else {}

    @property
    def has_permissions(self) -> List[DataPermission]:
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
                    self.__inProjects = {str(r['val']): []}
                case 'omas:hasPermissions':
                    self.__hasPermissions.append(r['val'])
                case _:
                    if r.get('proj') and r.get('rval'):
                        if self.__inProjects.get(str(r['proj'])) is None:
                            self.__inProjects[str(r['proj'])] = []
                        self.__inProjects[str(r['proj'])].append(AdminPermission(str(r['rval'])))

