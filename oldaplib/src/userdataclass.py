from typing import Self, Set, Iterable

from oldaplib.src.enums.permissions import AdminPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.in_project import InProjectClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_string import Xsd_string

@serializer
class SerializeableSet(Set):

    def __init__(self, setitems: Iterable | None = None, *items):
        if setitems:
            super().__init__(setitems)
        else:
            super().__init__(items)

    def _as_dict(self) -> dict:
        return {'setitems': list(self)}


@serializer
class UserData:
    _userIri: Iri
    _userId: Xsd_NCName
    _familyName: Xsd_string
    _givenName: Xsd_string
    _credentials: Xsd_string
    _isActive: Xsd_boolean
    _inProject: InProjectClass

    def __init__(self, *,
                 userIri: Iri,
                 userId: Xsd_NCName,
                 familyName: Xsd_string,
                 givenName: Xsd_string,
                 credentials: Xsd_string | None = None,
                 isActive: Xsd_boolean,
                 inProject: InProjectClass | None = None,
                 hasPermissions: SerializeableSet[Iri] | set[Iri] | None = None):
        self._userIri = userIri
        self._userId = userId
        self._familyName = familyName
        self._givenName = givenName
        self._credentials = credentials
        self._isActive = isActive
        self._inProject = inProject
        self._hasPermissions = hasPermissions if isinstance(hasPermissions, SerializeableSet) else SerializeableSet(hasPermissions)

    def __str__(self) -> str:
        res = f'userIri: {self._userIri}\n'
        res += f', userId: {self._userId}\n'
        res += f', familyName: {self._familyName}\n'
        res += f', givenName: {self._givenName}\n'
        res += f', credentials: {self._credentials}\n'
        res += f', isActive: {self._isActive}\n'
        res += f', inProject: {self._inProject}\n'
        res += f', hasPermissions: {self._hasPermissions}\n'
        return res

    @property
    def userIri(self) -> Iri:
        return self._userIri

    @property
    def userId(self) -> Xsd_NCName:
        return self._userId

    @property
    def familyName(self) -> Xsd_string:
        return self._familyName

    @property
    def givenName(self) -> Xsd_string:
        return self._givenName

    @property
    def credentials(self) -> Xsd_string:
        return self._credentials

    @property
    def isActive(self) -> Xsd_boolean:
        return self._isActive

    @property
    def inProject(self) -> InProjectClass | None:
        return self._inProject

    @property
    def hasPermissions(self) -> SerializeableSet[Iri] | None:
        return self._hasPermissions

    @staticmethod
    def sparql_query(context: Context, userId: Xsd_NCName) -> str:
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?user ?prop ?val ?proj ?rval
        FROM oldap:admin
        WHERE {{
            {{
                ?user a oldap:User .
                ?user oldap:userId {userId.toRdf} .
                ?user ?prop ?val .
            }} UNION {{
                ?user a oldap:User .
                ?user oldap:userId {userId.toRdf} .
                <<?user oldap:inProject ?proj>> oldap:hasAdminPermission ?rval
            }}
        }}
        """
        return sparql

    @classmethod
    def from_query(cls, queryresult: QueryProcessor) -> Self:
        in_project: dict[str, set[AdminPermission]] | None = None
        if len(queryresult) == 0:
            raise OldapErrorNotFound("Given user not found!")
        userIri: Iri | None = None
        userId: Xsd_NCName | None = None
        familyName: Xsd_string | None = None
        givenName: Xsd_string | None = None
        credentials: Xsd_string | None = None
        isActive: Xsd_boolean | None = None
        inProjectDict: dict[Iri | str, set[AdminPermission]] | None = None
        hasPermissions: set[Iri] | None = None
        for r in queryresult:
            match str(r.get('prop')):
                case 'dcterms:creator':
                    userIri = r['user']
                case 'dcterms:created':
                    pass
                case 'dcterms:contributor':
                    pass
                case 'dcterms:modified':
                    pass
                case 'oldap:userId':
                    userId = r['val']
                case 'foaf:familyName':
                    familyName = r['val']
                case 'foaf:givenName':
                    givenName = r['val']
                case 'oldap:credentials':
                    credentials = r['val']
                case 'oldap:isActive':
                    isActive = r['val']
                case 'oldap:inProject':
                    if not inProjectDict:
                        inProjectDict = {r['val']: set()}
                    else:
                        inProjectDict[r['val']] = set()
                case 'oldap:hasPermissions':
                    if not hasPermissions:
                        hasPermissions = set()
                    hasPermissions.add(r['val'])
                case _:
                    if r.get('proj') and r.get('rval'):
                        if not inProjectDict:
                            inProjectDict = {r['proj']: set()}
                        if inProjectDict.get(r['proj']) is None:
                            inProjectDict[r['proj']] = set()
                        inProjectDict[r['proj']].add(AdminPermission(str(r['rval'])))
        inProject = InProjectClass(inProjectDict) if inProjectDict else None
        return cls(userIri=userIri,
                   userId=userId,
                   familyName=familyName,
                   givenName=givenName,
                   credentials=credentials,
                   isActive=isActive,
                   inProject=inProject,
                   hasPermissions=hasPermissions)

    def _as_dict(self) -> dict:
        return {
                'userIri': self._userIri,
                'userId': self._userId,
                'familyName': self._familyName,
                'givenName': self._givenName,
                'isActive': self._isActive,
                'hasPermissions': self._hasPermissions,
                'inProject': self._inProject
        }

