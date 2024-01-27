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
from omaslib.src.helpers.rights import AdminRights
from omaslib.src.helpers.tools import lprint
from omaslib.src.model import Model


class User(Model):
    __creator: AnyIRI | None
    __created: datetime | None
    __contributor: AnyIRI | None
    __modified: datetime | None

    __userId: NCName
    __userIri: AnyIRI
    __familyName: str
    __givenName: str
    __credentials: str
    __inProject: Dict[QName, List[AdminRights]] | None
    __hasPermissions: List[str]
    __active: bool

    def __init__(self, *,
                 con: Connection | None = None,
                 user_iri: AnyIRI | None = None,
                 user_id: NCName,
                 family_name: str,
                 given_name: str,
                 credentials: str | None = None,
                 active: bool,
                 in_projects: Optional[Dict[QName, List[AdminRights]]] = None):
        super().__init__(con)
        self.__userIri = user_iri
        self.__userId = user_id
        self.__familyName = family_name
        self.__givenName = given_name
        self.__credentials = credentials
        self.__active = active
        self.__inProject = in_projects or []
        self.__hasPermissions = []

    def __str__(self) -> str:
        pp = {}
        if self.__inProject:
            for proj, perms in self.__inProject.items():
                pp[str(proj)] = [str(x) for x in perms]
        return f'User: {self.__userId}\n'\
            f'  User IRI: {self.__userIri}\n'\
            f'  UserID: {self.__userId}\n'\
            f'  FamilyName: {self.__familyName}\n'\
            f'  GivenName: {self.__givenName}\n'\
            f'  Credentials: {self.__credentials}\n'\
            f'  Project permissions: {pp}\n'\
            f'  Creator: {self.__creator}\n'\
            f'  Created at: {self.__created}\n'\
            f'  Modified by: {self.__contributor}\n'\
            f'  Modified at: {self.__modified}\n'

    def __repr__(self) -> str:
        pp = {}
        if self.__inProject:
            for proj, perms in self.__inProject.items():
                pp[str(proj)] = [str(x) for x in perms]
        return f'User(user_iri=AnyIRI("{self.__userIri}")'\
               f', user_id=NCName("{self.__userId}")'\
               f', familyName="{self.__familyName}"'\
               f', givenName="{self.__givenName}"'\
               f', credentials="{self.__credentials}"'\
               f', in_projects={pp})'

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
        return self.__credentials

    @property
    def user_id(self) -> AnyIRI:
        return self.__userId

    @property
    def active(self) -> bool:
        return self.__active

    @property
    def in_project(self) -> Dict[QName, AdminRights]:
        return self.__inProject
    
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
                <<?user omas:userInProject ?proj>> omas:hasPermission ?rval .
            }}
        }}
        """
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        user_iri: AnyIRI | None = None
        family_name: str = ""
        given_name: str = ""
        user_credentials: str = ""
        active: bool | None = None
        in_project: Dict[QName, List[AdminRights]] = {}
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
                    user_credentials = r['val']
                case 'omas:isActive':
                    active = r['val']
                case 'omas:inProject':
                    in_project = {r['val']: []}
                case _:
                    if r.get('proj') is not None:
                        if in_project.get(r['proj']) is None:
                            in_project[r['proj']] = []
                        in_project[r['proj']].append(AdminRights(r['rval']))
        return cls(con=con,
                   user_iri=user_iri,
                   user_id=user_id,
                   family_name=family_name,
                   given_name=given_name,
                   credentials=user_credentials,
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
