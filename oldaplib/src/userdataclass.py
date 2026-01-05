import textwrap
from datetime import datetime
from typing import Self, Dict

from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.irincname import IriOrNCName
from oldaplib.src.helpers.observable_dict import ObservableDict
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.serializeableset import SerializeableSet
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.in_project import InProjectClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string


@serializer
class UserData:
    """
    Represents user data, including personal information, roles, and project involvement,
    while adhering to a structured and serializable format.

    The class serves as a model for user-related information in a SPARQL-based system,
    providing methods for querying, constructing, and managing user-related data.

    :ivar creator: The IRI of the user who created this entity.
    :type creator: Iri | None
    :ivar created: The datetime when this entity was created.
    :type created: Xsd_dateTime | datetime | None
    :ivar contributor: The IRI of the user who contributed to this entity.
    :type contributor: Iri | None
    :ivar modified: The datetime when this entity was last modified.
    :type modified: Xsd_dateTime | datetime | None
    :ivar userIri: The unique IRI identifying the user.
    :type userIri: Iri
    :ivar userId: The unique non-colonized identifier (NCName) for the user.
    :type userId: Xsd_NCName
    :ivar familyName: The family name (surname) of the user.
    :type familyName: Xsd_string
    :ivar givenName: The given name (first name) of the user.
    :type givenName: Xsd_string
    :ivar email: The user's email address.
    :type email: Xsd_string
    :ivar credentials: The credentials or authentication key for the user, if provided.
    :type credentials: Xsd_string | None
    :ivar isActive: A boolean indicating whether the user is currently active.
    :type isActive: Xsd_boolean
    :ivar inProject: The project object or relation associated with the user.
    :type inProject: InProjectClass | None
    :ivar hasRole: A serializable set containing the roles or permissions assigned to the user.
    :type hasRole: SerializeableSet[Iri] | None
    """
    _creator: Iri | None
    _created: Xsd_dateTime | datetime | None
    _contributor: Iri | None
    _modified: Xsd_dateTime | datetime | None
    _userIri: Iri
    _userId: Xsd_NCName
    _familyName: Xsd_string
    _givenName: Xsd_string
    _email: Xsd_string
    _credentials: Xsd_string
    _isActive: Xsd_boolean
    _inProject: InProjectClass | None
    _hasRole: ObservableDict | None

    def __init__(self, *,
                 creator: Iri | None = None,
                 created: Xsd_dateTime | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | None = None,
                 userIri: Iri,
                 userId: Xsd_NCName,
                 familyName: Xsd_string,
                 givenName: Xsd_string,
                 email: Xsd_string,
                 credentials: Xsd_string | None = None,
                 isActive: Xsd_boolean,
                 inProject: InProjectClass | None = None,
                 hasRole: ObservableDict | Dict[Xsd_QName, Xsd_QName | None] | Dict[str, str] | None = None,
                 validate: bool = False):
        self._creator = creator
        self._created = created
        self._contributor = contributor
        self._modified = modified
        self._userIri = userIri
        self._userId = userId
        self._familyName = familyName
        self._givenName = givenName
        self._email = email
        self._credentials = credentials
        self._isActive = isActive
        self._inProject = inProject or InProjectClass()
        if isinstance(hasRole, ObservableDict):
            self._hasRole = hasRole
        elif isinstance(hasRole, dict):
            tmp = {Xsd_QName(key, validate=validate): Xsd_QName(val, validate=validate) if val else None for key, val in hasRole.items()}
            self._hasRole = ObservableDict(tmp)
        else:
            self._hasRole = None

    def __str__(self) -> str:
        res = f'userIri: {self._userIri}\n'
        res += f', userId: {self._userId}\n'
        res += f', familyName: {self._familyName}\n'
        res += f', givenName: {self._givenName}\n'
        res += f', email: {self._email}\n'
        res += f', credentials: {self._credentials}\n'
        res += f', isActive: {self._isActive}\n'
        res += f', inProject: {self._inProject}\n'
        res += f', hasRole: {self._hasRole}\n'
        return res

    @property
    def creator(self) -> Iri:
        return self._creator

    @property
    def created(self) -> Xsd_dateTime:
        return self._created

    @property
    def contributor(self) -> Iri:
        return self._contributor

    @property
    def modified(self) -> Xsd_dateTime:
        return self._modified

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
    def email(self) -> Xsd_string:
        return self._email

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
    def hasRole(self) -> Dict[Xsd_QName, Xsd_QName | None] | None:
        return self._hasRole

    @staticmethod
    def sparql_query(context: Context, userId: IriOrNCName, validate: bool = False) -> str:
        """
        Constructs and returns a SPARQL query string to retrieve user information and associated
        permissions from an administrative SPARQL context. The query can be built using either a user ID
        or a user IRI, and includes union statements to accommodate both properties and project-based
        admin permissions. This method is primarily designed to integrate within SPARQL-based systems
        and assumes the provided `Context` and `IriOrNCName` types adhere to expected operational
        contracts.

        :param context: The SPARQL context containing necessary administrative configurations.
        :type context: Context
        :param userId: The identifier or name conforming to the `IriOrNCName` type.
        :type userId: IriOrNCName
        :param validate: A boolean indicating whether the user ID should be validated during processing.
        :type validate: bool
        :return: A SPARQL query string for obtaining the requested administrative user data.
        :rtype: str

        :raises OldapErrorNotFound: If the user cannot be found.
        :raises OldapError: If the query fails for any other reason.
        :raises OldapErrorValue: If the user IRI is invalid and `validate` is set to `True`.
        """
        if not isinstance(userId, IriOrNCName):
            userId = IriOrNCName(userId, validate=validate)
        user_id, user_iri = userId.value()
        sparql = context.sparql_context
        if user_id is not None:
            sparql += textwrap.dedent(f"""
            SELECT ?user ?prop ?val ?proj ?rval ?role ?defdp
            FROM oldap:admin
            WHERE {{
                {{
                    ?user a oldap:User .
                    ?user oldap:userId {user_id.toRdf} .
                    ?user ?prop ?val .
                }} UNION {{
                    ?user a oldap:User .
                    ?user oldap:userId {user_id.toRdf} .
                    <<?user oldap:inProject ?proj>> oldap:hasAdminPermission ?rval
                }} UNION {{
                    ?user a oldap:User .
                    ?user oldap:userId {user_id.toRdf} .
                    <<?user oldap:hasRole ?role>> oldap:hasDefaultDataPermission ?defdp
                }}
            }}
            """)
        elif user_iri is not None:
            sparql += textwrap.dedent(f"""
            SELECT ?user ?prop ?val ?proj ?rval ?role ?defdp
            FROM oldap:admin
            WHERE {{
                BIND({user_iri.toRdf} as ?user)
                {{
                    ?user a oldap:User .
                    ?user ?prop ?val .
                }} UNION {{
                    ?user a oldap:User .
                    <<?user oldap:inProject ?proj>> oldap:hasAdminPermission ?rval
                }} UNION {{
                    ?user a oldap:User .
                    <<?user oldap:hasRole ?role>> oldap:hasDefaultDataPermission ?defdp
                }}
            }}
            """)

        return sparql

    @classmethod
    def from_query(cls, queryresult: QueryProcessor) -> Self:
        """
        Creates an instance of the class by parsing a query result object. The method
        extracts information such as user details, permissions, project involvement,
        and metadata from the query result and constructs a corresponding instance
        of the class.

        :param queryresult: Query result data obtained from a QueryProcessor.
        :type queryresult: QueryProcessor
        :return: An instance of the class with attributes populated based on query
            result data.
        :rtype: Self
        :raises OldapErrorNotFound: If the query result is empty, indicating that the
            user was not found.
        """
        in_project: dict[str, set[AdminPermission]] | None = None
        if len(queryresult) == 0:
            raise OldapErrorNotFound("Given user not found!")
        creator: Iri | None = None
        created: Xsd_dateTime | datetime | None = None
        contributor: Iri | None = None
        modified: Xsd_dateTime | datetime | None = None
        userIri: Iri | None = None
        userId: Xsd_NCName | None = None
        familyName: Xsd_string | None = None
        givenName: Xsd_string | None = None
        email: Xsd_string | None = None
        credentials: Xsd_string | None = None
        isActive: Xsd_boolean | None = None
        inProjectDict: dict[Iri | str, set[AdminPermission]] | None = None
        hasRoleDict: ObservableDict | None = None
        for r in queryresult:
            match str(r.get('prop')):
                case 'dcterms:creator':
                    userIri = r['user']
                    creator = r['val']
                case 'dcterms:created':
                    created = r['val']
                case 'dcterms:contributor':
                    contributor = r['val']
                case 'dcterms:modified':
                    modified = r['val']
                case 'oldap:userId':
                    userId = r['val']
                case 'schema:familyName':
                    familyName = r['val']
                case 'schema:givenName':
                    givenName = r['val']
                case 'schema:email':
                    email = r['val']
                case 'oldap:credentials':
                    credentials = r['val']
                case 'oldap:isActive':
                    isActive = r['val']
                case 'oldap:inProject':
                    if not inProjectDict:
                        inProjectDict = {r['val']: set()}
                    else:
                        inProjectDict[r['val']] = set()
                case 'oldap:hasRole':
                    if not hasRoleDict:
                        hasRoleDict = ObservableDict({r['val']: None})
                    else:
                        hasRoleDict[r['val']] = None
                case _:
                    if r.get('proj') and r.get('rval'):
                        if not inProjectDict:
                            inProjectDict = {r['proj']: set()}
                        if inProjectDict.get(r['proj']) is None:
                            inProjectDict[r['proj']] = set()
                        inProjectDict[r['proj']].add(AdminPermission.from_string(str(r['rval'])))
                    if r.get('role') and r.get('defdp'):
                        if not hasRoleDict:
                            hasRoleDict = {r['role']: None}
                        if hasRoleDict.get(r['role']) is None:
                            hasRoleDict[r['role']] = None
                        hasRoleDict[r['role']] = r['defdp']
        inProject = InProjectClass(inProjectDict) if inProjectDict else InProjectClass()
        return cls(created=created,
                   creator=creator,
                   contributor=contributor,
                   modified=modified,
                   userIri=userIri,
                   userId=userId,
                   familyName=familyName,
                   givenName=givenName,
                   email=email,
                   credentials=credentials,
                   isActive=isActive,
                   inProject=inProject,
                   hasRole=hasRoleDict,
                   validate=False)

    def _as_dict(self) -> dict:
        return {
                'userIri': self._userIri,
                'userId': self._userId,
                'familyName': self._familyName,
                'givenName': self._givenName,
                'email': self._email,
                'isActive': self._isActive,
                'hasRole': self._hasRole,
                'inProject': self._inProject
        }

