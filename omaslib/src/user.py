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
from omaslib.src.helpers.permissions import AdminPermission
from omaslib.src.helpers.tools import lprint
from omaslib.src.model import Model
from omaslib.user_dataclass import UserDataclass


class User(Model, UserDataclass):
    __creator: AnyIRI | None
    __created: datetime | None
    __contributor: AnyIRI | None
    __modified: datetime | None


    def __init__(self, *,
                 con: Connection | None = None,
                 user_iri: AnyIRI | None = None,
                 user_id: NCName,
                 family_name: str,
                 given_name: str,
                 credentials: str | None = None,
                 active: bool,
                 in_projects: Optional[Dict[QName, List[AdminPermission]]] = None):
        Model.__init__(self, con)
        UserDataclass.__init__(self,
                               user_iri=user_iri,
                               user_id=user_id,
                               family_name=family_name,
                               given_name=given_name,
                               credentials=credentials,
                               active=active,
                               in_projects=in_projects)
        self.__creator = con.user_iri
        self.__created = datetime.now()
        self.__contributor = con.user_iri
        self.__modified = datetime.now()

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
        jsonobj = con.query(super(User, cls).sparql_query(context, user_id))
        res = QueryProcessor(context, jsonobj)
        user = super(User, cls).create_from_queryresult(res)
        
        user_iri: AnyIRI | None = None
        family_name: str = ""
        given_name: str = ""
        credentials: str = ""
        active: bool | None = None
        in_project: Dict[QName, List[AdminPermission]] = {}
        for r in res:
            match str(r.get('prop')):
                case 'dcterms:creator':
                    cls.__creator = r['val']
                    user_iri = r['user']
                case 'dcterms:created':
                    cls.__created = r['val']
                case 'dcterms:contributor':
                    cls.__contributor = r['val']
                case 'dcterms:modified':
                    cls.__modified = r['val']
                case 'foaf:familyName':
                    family_name = r['val']
                case 'foaf:givenName':
                    given_name = r['val']
                case 'omas:credentials':
                    credentials = r['val']
                case 'omas:isActive':
                    active = r['val']
                case 'omas:inProject':
                    in_project = {r['val']: []}
                case _:
                    if r.get('proj') is not None:
                        if in_project.get(r['proj']) is None:
                            in_project[r['proj']] = []
                        in_project[r['proj']].append(AdminPermission(r['rval']))
        return cls(con=con,
                   user_iri=user_iri,
                   user_id=user_id,
                   family_name=family_name,
                   given_name=given_name,
                   credentials=credentials,
                   active=active,
                   in_projects=in_project)


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
