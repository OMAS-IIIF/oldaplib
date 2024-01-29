"""
Ths class User
"""
import json
import uuid
from datetime import datetime
from pprint import pprint
from typing import List, Optional, Self, Dict

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import AnyIRI, QName, NCName
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.permissions import AdminPermission, DataPermission
from omaslib.src.helpers.tools import lprint
from omaslib.src.model import Model
from omaslib.user_dataclass import UserDataclass


class User(Model, UserDataclass):
    __creator: AnyIRI | None
    __created: datetime | None
    __contributor: AnyIRI | None
    __modified: datetime | None

    __userId: NCName
    __userIri: AnyIRI
    __familyName: str
    __givenName: str
    __credentials: str
    __inProjects: Dict[QName, List[AdminPermission]] | None
    __hasPermissions: List[DataPermission] | None
    __active: bool


    def __init__(self, *,
                 con: Connection | None = None,
                 creator: AnyIRI | None = None,
                 created: datetime | None = None,
                 contributor: AnyIRI | None = None,
                 modified: datetime | None = None,
                 user_iri: AnyIRI | None = None,
                 user_id: NCName,
                 family_name: str,
                 given_name: str,
                 credentials: str | None = None,
                 active: bool,
                 in_projects: Optional[Dict[QName, List[AdminPermission]]] = None,
                 has_permissions: Optional[List[DataPermission]] = None):
        Model.__init__(self, con)
        self.__creator = creator
        self.__created = created
        self.__contributor = contributor
        self.__modified = modified
        self.__userId = user_id
        self.__userIri = user_iri
        self.__familyName = family_name
        self.__givenName = given_name
        self.__credentials = credentials
        self.__active = active
        self.__inProjects = in_projects or {}
        self.__hasPermissions = has_permissions or []


    @classmethod
    def init_from_dataclass(cls, con: Connection, data: UserDataclass) -> Self:
        return cls(con=con,
                   creator=data.creator,
                   created=data.created,
                   contributor=data.contributor,
                   modified=data.modified,
                   user_iri=data.userIri,
                   user_id=data.userId,
                   family_name=data.familyName,
                   given_name=data.givenName,
                   credentials=data.credentials,
                   active=data.active,
                   in_projects=data.inProjects,
                   has_permissions=data.hasPermissions)

    def __str__(self) -> str:
        return UserDataclass.__str__(self) + \
            f'  Creator: {self.__creator}\n' \
            f'  Created at: {self.__created}\n' \
            f'  Modified by: {self.__contributor}\n' \
            f'  Modified at: {self.__modified}\n'


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
    def active(self) -> bool:
        return self.__active

    @property
    def in_project(self) -> Dict[QName, List[AdminPermission]]:
        return self.__inProjects

    @property
    def has_permissions(self) ->List[DataPermission]:
        return self.__hasPermissions

    @property
    def json(self) -> str:
        obj = {
            'userId': self.__userId,
            'userIri': self.__userIri,
            'inProject': self.__inProject,
            'hasPermissions': self.__hasPermissions
        }
        return json.dumps(obj)

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        if self.__userIri is None:
            self.__userIri = AnyIRI(uuid.uuid4().urn)
        context = Context(name=self._con.context_name)
        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?user
        FROM omas:admin
        WHERE {{
            ?user a omas:User .
            ?user omas:userId "{self.__userId}"^^NCName
        }}
        """
        timestamp = datetime.now()
        blank = ''
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH omas:admin {{\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

    @classmethod
    def read(cls, con: Connection, user_id: NCName | str) -> Self:
        if isinstance(user_id, str):
            user_id = NCName(user_id)
        cls._con = con
        context = Context(name=con.context_name)
        jsonobj = con.query(cls.sparql_query(context, user_id))
        res = QueryProcessor(context, jsonobj)
        userdata = super(User, cls).create_from_queryresult(res)
        return cls()
        user.__creator = data['creator']
        user.__created = data['created']
        user.__contributor = data['contributor']
        user.__modified = data['modified']


if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     repo="omas",
                     userid="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")

    user = User.read(con, 'rosenth')
    print(user)
    user = User.read(con, 'anonymous')
    print(user)
