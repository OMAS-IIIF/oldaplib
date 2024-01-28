from typing import Dict, List, Optional

from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NCName, AnyIRI, QName
from omaslib.src.helpers.permissions import AdminPermission, DataPermission
from omaslib.src.helpers.query_processor import QueryProcessor


class UserDataclass:
    __userId: NCName
    __userIri: AnyIRI
    __familyName: str
    __givenName: str
    __credentials: str
    __inProjects: Dict[QName, List[AdminPermission]] | None
    __hasPermissions: List[DataPermission] | None
    __active: bool

    def __init__(self, *,
                 user_iri: AnyIRI | None = None,
                 user_id: NCName,
                 family_name: str,
                 given_name: str,
                 credentials: str | None = None,
                 active: bool,
                 in_projects: Optional[Dict[QName, List[AdminPermission]]] = None,
                 has_permissions: Optional[List[DataPermission]] = None) -> None:
        self.__userIri = user_iri
        self.__userId = user_id
        self.__familyName = family_name
        self.__givenName = given_name
        self.__credentials = credentials
        self.__active = active
        self.__inProjects = in_projects or {}
        self.__hasPermissions = has_permissions or []

    def __str__(self) -> str:
        pp = {}
        if self.__inProjects:
            for proj, perms in self.__inProjects.items():
                pp[str(proj)] = [str(x) for x in perms]
        return f'User: {self.__userId}\n'\
            f'  User IRI: {self.__userIri}\n'\
            f'  UserID: {self.__userId}\n'\
            f'  FamilyName: {self.__familyName}\n'\
            f'  GivenName: {self.__givenName}\n'\
            f'  Credentials: {self.__credentials}\n'\
            f'  Admin permissions: {pp}\n'\
            f'  HasPermissions: {[s.name for s in self.__hasPermissions]}'

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
               f', in_projects={pp}'\
               f', has_permissions={[s.name for s in self.__hasPermissions]}'

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

    def sparql_query(self, context: Context, user_id: NCName) -> str:
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
        return sparql

    @classmethod
    def create_from_queryresult(cls, queryresult: QueryProcessor):
        user_id: NCName = NCName('x:y')
        user_iri: AnyIRI | None = None
        family_name: str = ""
        given_name: str = ""
        credentials: str = ""
        active: bool | None = None
        in_project: Dict[QName, List[AdminPermission]] = {}
        for r in queryresult:
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
                case 'omas:userId':
                    user_id = r['val']
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
        return cls(user_iri=user_iri,
                   user_id=user_id,
                   family_name=family_name,
                   given_name=given_name,
                   credentials=credentials,
                   active=active,
                   in_projects=in_project)

