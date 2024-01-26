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

    __familyName: str
    __givenName: str
    __userId: AnyIRI
    __userCredentials: str
    __inProject: Dict[QName, List[AdminRights]] | None
    __inGroup: List[str]
    __active: bool

    def __init__(self, *,
                 con: Optional[Connection] = None,
                 family_name: str,
                 given_name: str,
                 user_id: AnyIRI,
                 user_credentials: str,
                 active: bool,
                 in_projects: Optional[Dict[QName, List[AdminRights]]] = None):
        super().__init__(con)
        self.__familyName = family_name
        self.__givenName = given_name
        self.__userId = user_id
        self.__userCredentials = user_credentials
        self.__active = active
        self.__inProject = in_projects or []
        self.__inGroup = []

    def __str__(self) -> str:
        pp = {}
        for proj, perms in self.__inProject.items():
            pp[str(proj)] = [str(x) for x in perms]
        return f'User: {self.__userId}\n'\
            f'  FamilyName: {self.__familyName}\n'\
            f'  GivenName: {self.__givenName}\n'\
            f'  UserID: {self.__userId}\n'\
            f'  Credentials: {self.__userCredentials}\n'\
            f'  Project permissions: {pp}\n'\
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
    def familyName(self) -> str:
        return self.__lastName

    @property
    def givenName(self) -> str:
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
                <<?user omas:userInProject ?proj>> omas:hasPermission ?rval .
            }}
        }}
        """
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        family_name: str = ""
        given_name: str = ""
        user_credentials: str = ""
        active: bool = None
        in_project: Dict[QName, List[AdminRights]] = {}
        for r in res:
            #print("==>", r)
            match str(r.get('prop')):
                case 'dcterms:creator':
                    cls.__creator = r['val']
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
                case 'omas:userCredentials':
                    user_credentials = r['val']
                case 'omas:userIsActive':
                    active = r['val']
                case 'omas:userInProject':
                    in_project = {r['val']: []}
                case _:
                    if r.get('proj') is not None:
                        if in_project.get(r['proj']) is None:
                            in_project[r['proj']] = []
                        in_project[r['proj']].append(AdminRights(r['rval']))
        return cls(con=con,
                   user_id=user_id,
                   family_name=family_name,
                   given_name=given_name,
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
