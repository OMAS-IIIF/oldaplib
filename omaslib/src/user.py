"""
Ths class User
"""
import json
from datetime import datetime
from pprint import pprint
from typing import List, Optional, Self, Dict

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import AnyIRI, QName
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.rights import AdminRights
from omaslib.src.helpers.tools import lprint
from omaslib.src.model import Model


class User(Model):
    __creator: AnyIRI | None
    __created: datetime | None
    __contributor: AnyIRI | None
    __modified: datetime | None

    __lastName: str
    __firstName: str
    __userId: AnyIRI
    __userCredentials: str
    __inProject: Dict[QName, AdminRights | None] | None
    __inGroup: List[str]
    __active: bool

    def __init__(self, *,
                 con: Optional[Connection] = None,
                 last_name: str,
                 first_name: str,
                 user_id: AnyIRI,
                 user_credentials: str,
                 active: bool,
                 in_projects: Optional[Dict[QName, AdminRights | None]] = None):
        super().__init__(con)
        self.__lastName = last_name
        self.__firstName = first_name
        self.__userId = user_id
        self.__userCredentials = user_credentials
        self.__active = active
        self.__inProject = in_projects
        self.__inGroup = []

    def __str__(self) -> str:
        return f'User: {self.__userId}\n'\
            f'  LastName: {self.__lastName}\n'\
            f'  FirstName: {self.__firstName}\n'\
            f'  UserID: {self.__userId}\n'\
            f'  Credentials: {self.__userCredentials}\n'\
            f'  Project rights: {self.__inProject}\n'\
            f'  Creator: {self.__creator}\n'\
            f'  Created at: {self.__created}\n'\
            f'  Modified by: {self.__contributor}\n'\
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
    def lastName(self) -> str:
        return self.__lastName

    @property
    def firstName(self) -> str:
        return self.__firstName

    @property
    def credentials(self) -> str:
        return self.__userCredentials

    @property
    def user_id(self) -> AnyIRI:
        return self.__userId

    @property
    def active(self) -> bool:
        return self.__active

    @property
    def in_project(self) -> Dict[QName, AdminRights]:
        return self.__inProject

    def create(self):
        pass

    @classmethod
    def read(cls, con: Connection, user_id: str) -> Self:
        cls._con = con
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?user ?prop ?val ?proj ?rval
        FROM omas:admin
        WHERE {{
            {{
                ?user a omas:User .
                ?user omas:userId "{user_id}" .
                ?user ?prop ?val .
            }} UNION {{
                <<?user omas:userInProject ?proj>> omas:hasRights ?rights .
                ?rights omas:value ?rval
            }}
        }}
        """
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        last_name: str = None
        first_name: str = None
        user_credentials: str = None
        active: bool = None
        in_project: Dict[QName, List[QName]] = {}
        for r in res:
            print("==>", r)
            match str(r.get('prop')):
                case 'dcterms:creator':
                    cls.__creator = r['val']
                case 'dcterms:created':
                    cls.__created = r['val']
                case 'dcterms:contributor':
                    cls.__contributor = r['val']
                case 'dcterms:modified':
                    cls.__modified = r['val']
                case 'omas:personLastName':
                    last_name = r['val']
                case 'omas:personFirstName':
                    first_name = r['val']
                case 'omas:userCredentials':
                    user_credentials = r['val']
                case 'omas:userIsActive':
                    active = r['val']
                case 'omas:userInProject':
                    in_project = {r['val']: None}
                case _:
                    if r.get('proj') is not None:
                        in_project[r['proj']] = AdminRights(r['rval'])
        return cls(con=con,
                   user_id=user_id,
                   last_name=last_name,
                   first_name=first_name,
                   user_credentials=user_credentials,
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
