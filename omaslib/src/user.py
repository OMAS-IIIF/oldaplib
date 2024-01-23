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
from omaslib.src.helpers.serializer import serializer
from omaslib.src.helpers.tools import lprint
from omaslib.src.model import Model


@serializer
class User:
    _con: Connection | None
    __creator: AnyIRI | None
    __created: datetime | None
    __contributor: AnyIRI | None
    __modified: datetime | None

    __lastName: str
    __firstName: str
    __userId: AnyIRI
    __userCredentials: str
    __inProject: Dict[str, List[QName]]
    __inGroup: List[str]
    __active: bool

    def __init__(self, *,
                 con: Optional[Connection] = None,
                 last_name: str,
                 first_name: str,
                 user_id: AnyIRI,
                 user_credentials: str,
                 active: bool,
                 in_projects: Optional[Dict[QName, List[QName]]] = None,
                 creator: Optional[AnyIRI] = None,  # Only for serializer
                 created: Optional[datetime] = None,  # Only for serializer
                 contributor: Optional[AnyIRI] = None,  # Only for serializer
                 modified: Optional[datetime] = None):  # Only for serializer
        #super().__init__(con)
        self._con = con
        self.__lastName = last_name
        self.__firstName = first_name
        self.__userId = user_id
        self.__userCredentials = user_credentials
        self.__active = active
        self.__inProject = in_projects or {}
        self.__inGroup = []
        self.__created = created
        self.__creator = creator
        self.__modified = modified
        self.__contributor = contributor


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

    def _as_dict(self) -> Dict:
        return {
            "last_name": self.__lastName,
            "first_name": self.__firstName,
            "user_id": self.__userId,
            "user_credentials": self.__userCredentials,
            "active": self.__active,
            "in_projects": self.__inProject,
            "creator": self.__creator,
            "created": self.__created,
            "modified": self.__modified,
            "contributor": self.__contributor
        }

    def set_con(self, con: Connection):
        self._con = con

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
    def userId(self) -> str:
        return self.__userId

    @property
    def active(self) -> bool:
        return self.__active

    @property
    def in_project(self) -> bool:
        return self.__inProject

    def create(self):
        pass

    @classmethod
    def read(cls, con: Connection, user_id: str) -> Self:
        cls._con = con
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?user ?prop ?val ?proj ?rights
        FROM omas:admin
        WHERE {{
            {{
                ?user a omas:User .
                ?user omas:userId "{user_id}" .
                ?user ?prop ?val .
            }} UNION {{
                <<?user omas:userInProject ?proj>> omas:hasRights ?rights .
            }}
        }}
        """
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        creator: AnyIRI = None
        created: datetime = None
        contributor: AnyIRI = None
        modified: datetime = None
        last_name: str = None
        first_name: str = None
        user_credentials: str = None
        active: bool = None
        in_project: Dict[QName, List[QName]] = {}
        for r in res:
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
                    in_project[str(r['val'])] = []
                case _:
                    if r.get('proj') is not None:
                        if in_project.get(str(r['proj'])) is None:
                            in_project[str(r['proj'])] = []
                        in_project[str(r['proj'])].append(r['rights'])
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
    jsonstr = json.dumps(user, default=serializer.encoder_default)
    print(jsonstr)
    gaga = json.loads(jsonstr, object_hook=serializer.decoder_hook)
    print("=====================================")
    print(gaga)
