"""
# User class

This module implements the Python representation of an OLDAP user. It offers methods to

- create
- read
- update
- delete

a user from the triple store.
"""
import json
import uuid
from datetime import datetime
from typing import List, Self, Dict, Set

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import AnyIRI, QName, NCName
from omaslib.src.helpers.omaserror import OmasError, OmasErrorAlreadyExists, OmasErrorNotFound, OmasErrorUpdateFailed, \
    OmasErrorValue
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.permissions import AdminPermission, DataPermission
from omaslib.src.helpers.serializer import serializer
from omaslib.src.helpers.tools import lprint
from omaslib.src.model import Model
from omaslib.src.user_dataclass import UserDataclass


@serializer
class User(Model, UserDataclass):
    """
    The OLDAP user class is based on the [UserDataclass](/userdataclass#UserDataclass). It implements together with the UserDataclass
    all the methods ot manage OLDAP users.
    """
    def __init__(self, *,
                 con: Connection | None = None,
                 creator: AnyIRI | None = None,
                 created: datetime | None = None,
                 contributor: AnyIRI | None = None,
                 modified: datetime | None = None,
                 userIri: AnyIRI | None = None,
                 userId: NCName | None = None,
                 family_name: str | None = None,
                 given_name: str | None = None,
                 credentials: str | None = None,
                 active: bool | None = None,
                 inProject: Dict[QName, Set[AdminPermission]] | None = None,
                 hasPermissions: Set[QName] | None = None):
        """
        Constructor for the User class
        :param con: Connection instance
        :type con: Connection | None
        :param creator: AnyIRI of the creator
        :type creator: AnyIRI | None
        :param created: DateTime of the creation of the user
        :type created: datetime | None
        :param contributor: AnyIRI of the user that changed the given User instance
        :type contributor: AnyIRI | None
        :param modified: Modification of the User
        :type modified: datetime
        :param userIri: The IRI of the new user (e.g. the ORCID) If omitted, a unique urn: is created
        :type userIri: AnyIRI | None
        :param userId: The UserId that the user types in at login
        :type userId: NCName | None
        :param family_name: The foaf:familyName of the User to be created
        :type family_name: str
        :param given_name: The foaf:givenName of the User to be created
        :type given_name: str
        :param credentials: The initial credentials (password) of the user to be created
        :type credentials: str
        :param active: True if the user is active, False otherwise
        :type active: bool
        :param inProject: Membership and admin permissions the user has in the given projects
        :type inProject: InProjectType
        :param hasPermissions: Connection to permission sets
        :type hasPermissions: PermissionSet
        """
        if userIri is None:
            userIri = AnyIRI(uuid.uuid4().urn)
        Model.__init__(self, connection=con)
        UserDataclass.__init__(self,
                               creator=creator,
                               created=created,
                               contributor=contributor,
                               modified=modified,
                               userIri=userIri,
                               userId=userId,
                               family_name=family_name,
                               given_name=given_name,
                               credentials=credentials,
                               active=active,
                               inProject=inProject,
                               hasPermissions=hasPermissions)

    def create(self) -> None:
        """
        Creates the given user in the triple store. Before the creation, the method checks if a
        user with the given userID or userIri already exists and raises an exception.
        :return: None
        :raises OmasErrorAlreadyExists: User already exists
        :raises OmasValueError: PermissionSet is not existing
        :raises OmasError: Internal error
        """
        indent: int = 0
        indent_inc: int = 4
        if self._con is None:
            raise OmasError("Cannot create: no connection")
        if self.userIri is None:
            self.userIri = AnyIRI(uuid.uuid4().urn)
        context = Context(name=self._con.context_name)
        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?user
        FROM omas:admin
        WHERE {{
            ?user a omas:User .
            ?user omas:userId "{self.userId}"^^xsd:NCName .         
        }}
        """

        sparql2 = context.sparql_context
        sparql2 += f"""
        SELECT ?user
        FROM omas:admin
        WHERE {{
            ?user a omas:User .
            FILTER(?user = <{self.userIri}>)
        }}
        """

        ptest = context.sparql_context
        ptest += f"""
        SELECT ?permissionset
        FROM omas:admin
        WHERE {{
            ?permissionset a omas:PermissionSet .
            FILTER(?permissionset IN ({repr(self.hasPermissions)}))
        }}
        """

        timestamp = datetime.now()
        blank = ''
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH omas:admin {{\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}}<{self.userIri}> a omas:User'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator <{self._con.userIri}>'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created "{timestamp.isoformat()}"^^xsd:dateTime'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor <{self._con.userIri}>'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified "{timestamp.isoformat()}"^^xsd:dateTime'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}omas:userId "{self.userId}"^^xsd:NCName'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}foaf:familyName "{self.familyName}"'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}foaf:givenName "{self.givenName}"'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}omas:credentials "{self.credentials}"'
        star = ''
        if self.inProject:
            project = [str(p) for p in self.inProject.keys()]
            rdfstr = ", ".join(project)
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}omas:inProject {rdfstr}'
            for p in project:
                for admin_p in self.inProject[p]:
                    star += f'{blank:{(indent + 2) * indent_inc}}<<<{self.userIri}> omas:inProject {p}>> omas:hasAdminPermission {admin_p.value} .\n'
        if self.hasPermissions:
            rdfstr = ", ".join([ str(x) for x in self.hasPermissions])
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}omas:hasPermissions {rdfstr}'
        sparql += " .\n\n"
        sparql += star
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(sparql1)
        except OmasError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OmasErrorAlreadyExists(f'A user with a user ID "{self.userId}" already exists')
        
        try:
            jsonobj = self._con.transaction_query(sparql2)
        except OmasError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OmasErrorAlreadyExists(f'A user with a user IRI "{self.userIri}" already exists')

        try:
            jsonobj = self._con.transaction_query(ptest)
        except OmasError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) != len(self.hasPermissions):
            self._con.transaction_abort()
            raise OmasErrorValue("One of the permission sets is not existing!")

        try:
            self._con.transaction_update(sparql)
        except OmasError:
            self._con.transaction_abort()
            raise
        try:
            self._con.transaction_commit()
        except OmasError:
            self._con.transaction_abort()
            raise


    @classmethod
    def read(cls, con: Connection, userId: NCName | str) -> Self:
        """
        Reads a User instance from the data in the triple store
        :param con: Connection instance
        :type con: Connection
        :param userId: The userId of the user to be read
        :type userId: NCName | str
        :return: Self
        :raises OmasErrorNotFound: Required user does ot exist
        """
        if isinstance(userId, str):
            userId = NCName(userId)

        context = Context(name=con.context_name)
        jsonobj = con.query(cls.sparql_query(context, userId))
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OmasErrorNotFound(f'User "{userId}" not found.')
        instance = cls(con=con)
        instance._create_from_queryresult(res)
        return instance

    def delete(self) -> None:
        """
        Delete the given user from the triple store
        :return: None
        """
        context = Context(name=self._con.context_name)
        blank = ''
        sparql = context.sparql_context
        sparql += f"""
        DELETE {{
            <<?user omas:inProject ?proj>> omas:hasAdminPermission ?rval .    
        }}
        WHERE {{
            ?user a omas:User .
            ?user omas:userId "{self.userId}"^^xsd:NCName .
        }} ;
        DELETE WHERE {{
            ?user a omas:User .
            ?user omas:userId "{self.userId}"^^xsd:NCName .
            ?user ?prop ?val .
        }} 
        """
        # TODO: use transaction for error handling
        self._con.update_query(sparql)

    def update(self) -> None:
        """
        Update an existing user from the triple store
        :return: None
        :raises OmasErrorUpdateFailed: Updating user failed because user has been changed through race condition
        :raises OmasValueError: A PermissionSet is not existing
        :raises OmasError: An internal error occurred
        """
        timestamp = datetime.now()
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        ptest, ptest_len, tmpsparql = self._sparql_update()
        sparql += tmpsparql
        self._con.transaction_start()
        try:
            modtime = self.get_modified_by_iri(QName('omas:admin'), self.userIri)
        except OmasError:
            self._con.transaction_abort()
            raise
        if modtime != self.modified:
            self._con.transaction_abort()
            raise OmasErrorUpdateFailed(f'Modifying user "{self.userId}" failed because of changed modification time: {modtime}')
        if ptest and ptest_len > 0:
            ptest_sparql = context.sparql_context
            ptest_sparql += ptest
            jsonobj = self._con.transaction_query(ptest_sparql)
            res = QueryProcessor(context, jsonobj)
            if len(res) != ptest_len:
                self._con.transaction_abort()
                raise OmasErrorValue("One of the permission sets is not existing!")
        try:
            self._con.transaction_update(sparql)
            self.set_modified_by_iri(QName('omas:admin'), self.userIri, self.modified, timestamp)
            modtime = self.get_modified_by_iri(QName('omas:admin'), self.userIri)
        except OmasError:
            self._con.transaction_abort()
            raise
        if timestamp != modtime:
            raise OmasErrorUpdateFailed("Update failed! Timestamp does not match")
        try:
            self._con.transaction_commit()
        except OmasError:
            self._con.transaction_abort()
            raise
        self.modified = timestamp


if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     repo="omas",
                     userId="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")

    user = User.read(con, 'rosenth')
    print(user)
    user2 = User(con=con,
                 userId=NCName("testuser"),
                 family_name="Test",
                 given_name="Test",
                 credentials="Ein@geheimes&Passw0rt",
                 inProject={QName('omas:HyperHamlet'): [AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE]},
                 hasPermissions=[QName('omas:GenericView')])
    print(user2)
    user2.create()
    user3 = User.read(con, 'testuser')
    print(user3)
    #jsonstr = json.dumps(user2, default=serializer.encoder_default, indent=4)
    #print(jsonstr)
    #user3 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
    #print(user3)
