"""
# User class

This module implements the Python representation of an OLDAP user. It offers methods to

- create
- read
- search
- update
- delete

a user from the triple store. The User class inherits from
[UserDataclass](/python_docstrings/userdataclass/#oldap.src.user_dataclass.UserFields). UserDataclass
provides the inner workings for the User, but without database access. This separation is necessary
for bootstrapping the connection to the triple store. The [Connection](/python_docstrings/connection) class obviously
has not yet an established connection instance. Therefore, it as to connect to the triple store using basic method,
but still must get authorization based on the supplied userId and credentials. Internally it stores the user's
information including all permissions within the access token that is returned by the first connection (aka login).

The UserDataclass class is serializable as JSON as follows (using the @serializer decorator):
```python
jsonstr = json.dumps(userdata, default=serializer.encoder_default)
user = json.loads(jsonstr, object_hook=serializer.decoder_hook)
```

The User class inherits the following properties from the UserDataclass class:

- _userIri_: IRI of the user, cannot be changed (RDF property `oldap:userIri`)
- _userId_: User ID as NCName (RDF property `oldap:userId`)
- _familyName_: Family name as str (RDF property `foaf:familyName`)
- _givenName_: Given name or first name as str(RDF property `foaf:givenName`)
- _credentials_: Credential (password) (RDF property `oldap:credentials`)
- _isActive_: Is the user active as bool? (RDF property `oldap:isActive`)
- _inProject_: Membership to projects and administrative permissions for this project (RDF property `oldap:inProject)
- _hsPermission_: Permissions for data as sets of QNames (RDF property `oldap:hasPermissions`)

These properties can be accessed as normal python class properties or using the dictionary syntax. The keys
are defined in the [UserFields](/python_docstrings/userdataclass/#oldaplib.src.user_dataclass.UserFields) Enum class.
Example for access as property:
```python
user.familyName = 'Rosenthaler'
givenname = user.givenName
del user.givenName
```
Example for access as dictionary:
```python
user[UserFields.FAMILY_NAME] = 'Rosenthaler'
givenname = user[UserFields.GIVEN_NAME]
del user[UserFields.GIVEN_NAME]
```

## Create a user

A user is created using the method [create()](/python_docstrings/user/#oldaplib.src.user.User.create) as follows:

```python
user = User(con=self._connection,
            userIri=AnyIRI("https://orcid.org/0000-0002-9991-2055"),
            userId=NCName("edison"),
            family_name="Edison",
            given_name="Thomas A.",
            credentials="Lightbulb&Phonograph",
            inProject={QName('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                   AdminPermission.ADMIN_RESOURCES,
                                                   AdminPermission.ADMIN_CREATE}},
            hasPermissions={QName('oldap:GenericView')})
user.create()
```

- __userIri__ is an optional parameter that allows to give the user a unique IRI. If possible, the
  [ORCID](https://orcid.org) ID should be given. If this parameter is omitted, OLDAP generates a unique IRI from the URN
  namespace for the user.
- __userId__ must be an [NCName](/python_docstrings/datatypes#oldaplib.src.helpers.datatypes.NCName)
- __credentials__ is a password that is converted to a bcrypt hash
- __inProject__ is a dictionary with the keys being the projects that the user is a member of. The values are
  sets of administrative privileges as defined in [AdminPermissions](/python_docstrings/permissions#AdminPermissions)
- __hasPermissions__ are links to PermissionSet's that define the access permissions for resources.

Please note that the class constructor does *not* create the user in the triple store. In order to create
the user in the database, `<User>.create()`has to be called.

## Reading a user from the database

In order to read all user data from the triple store, the method [read()](/python_docstrings/user/#oldaplib.src.user.User.read) is used as
follows:

```python
user = User.read(con=self._connection, userId="rosenth")
```

The `userId` must be known and passed either as string or NCName.

## Searching for a user in the database

OLDAP allows to search for users within the database. The method [search()](/python_docstrings/user/#oldaplib.src.user.User.search)
performs a search. The string given must match in total with the entry in the database. The method accepts also
several arguments which are combined by a logical AND.

```python
users = User.search(con=self._connection,userId="fornaro")

users = User.search(con=self._connection, familyName="Rosenthaler")

users = User.search(con=self._connection, givenName="John")

users = User.search(con=self._connection, inProject=QName("oldap:HyperHamlet"))

users = User.search(con=self._connection, inProject=AnyIRI("http://www.salsah.org/version/2.0/SwissBritNet"))

users = User.search(con=self._connection, userId="GAGA")
```

## Updating a User

Several properties of a user can be changed using the [update()](/python_docstrings/user/#oldaplib.src.user.User.update) method. In a first step, the properties
of a user instance are changed, then the `update()` method writes the changes to the triple store.

The following example exemplifies the procedure:

```python
    user2 = User.read(con=self._connection, userId="edison")  # read the user from the triple store
    user2.userId = "aedison"  # change the userId
    user2.familyName = "Edison et al."  # change the familyName
    user2.givenName = "Thomas"  # change the givenName
    user2.hasPermissions.add(QName('oldap:GenericRestricted'))  # add a permission set
    user2.hasPermissions.add(QName('oldap:HyperHamletMember'))  # add a permission set
    user2.hasPermissions.remove(QName('oldap:GenericView'))  # remove a permission set
    user2.inProject[QName('oldap:SystemProject')] = {AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES}
    user2.inProject[QName('oldap:HyperHamlet')].remove(AdminPermission.ADMIN_USERS)
    user2.update()
```

## Deleting a User

The method [delete()](/python_docstrings/user/#oldaplib.src.user.User.delete) deletes the given user from
the database:

```python
user3 = User.read(con=self._connection, userId="aedison")
user3.delete()
```
"""

import uuid
from datetime import datetime
from typing import List, Self, Dict, Set, Optional

from oldaplib.src.enums.userdataclassattr import UserAttr
from oldaplib.src.helpers.context import Context
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_string import Xsd_string
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorAlreadyExists, OldapErrorNotFound, OldapErrorUpdateFailed, \
    OldapErrorValue, OldapErrorNoPermission
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.enums.permissions import AdminPermission
from oldaplib.src.helpers.tools import str2qname_anyiri, lprint
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.user_dataclass import UserDataclass


# @serializer
class User(Model, UserDataclass):
    """
    The OLDAP user class is based on the [UserDataclass](/python_docstrings/userdataclass#UserDataclass). It implements together with the UserDataclass
    all the methods ot manage OLDAP users. I also uses the [InProject](/python_docstrings/in_project) class.
    """

    def __init__(self, *,
                 con: IConnection | None = None,
                 creator: Iri | str | None = None,
                 created: Xsd_dateTime | str | str | None = None,
                 contributor: Iri | str | None = None,
                 modified: Xsd_dateTime | str | None = None,
                 userIri: Iri | str | None = None,
                 userId: Xsd_NCName | str | None = None,
                 familyName: Xsd_string | str | None = None,
                 givenName: Xsd_string | str | None = None,
                 credentials: Xsd_string | str | str | None = None,
                 isActive: Xsd_boolean | bool | None = None,
                 inProject: Dict[Iri, Set[AdminPermission]] | None = None,
                 hasPermissions: Set[Iri] | None = None):
        """
        Constructor for the User class
        :param con: IConnection instance
        :type con: IConnection | None
        :param creator: AnyIRI of the creator
        :type creator: Xsd_anyURI | None
        :param created: DateTime of the creation of the user
        :type created: datetime | None
        :param contributor: AnyIRI of the user that changed the given User instance
        :type contributor: AnyIRI | None
        :param modified: Modification of the User
        :type modified: datetime
        :param userIri: The IRI of the new user (e.g. the ORCID) If omitted, a unique urn: is created
        :type userIri: AnyIRI | None
        :param userId: The UserId that the user types in at login
        :type userId: Xsd_NCName | None
        :param familyName: The foaf:familyName of the User to be created
        :type familyName: str
        :param givenName: The foaf:givenName of the User to be created
        :type givenName: str
        :param credentials: The initial credentials (password) of the user to be created
        :type credentials: str
        :param isActive: True if the user is active, False otherwise
        :type isActive: bool
        :param inProject: Membership and admin permissions the user has in the given projects
        :type inProject: InProjectType
        :param hasPermissions: IConnection to permission sets
        :type hasPermissions: PermissionSet
        """
        if userIri is None:
            userIri = Iri()
        Model.__init__(self, connection=con)
        UserDataclass.__init__(self,
                               creator=creator,
                               created=created,
                               contributor=contributor,
                               modified=modified,
                               userIri=userIri,
                               userId=userId,
                               familyName=familyName,
                               givenName=givenName,
                               credentials=credentials,
                               isActive=isActive,
                               inProject=inProject,
                               hasPermissions=hasPermissions)

    def check_for_permissions(self) -> (bool, str):
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('oldap:SystemProject'))
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            #
            # user has root privileges!
            #
            return True, "OK – IS ROOT"
        else:
            if len(self.inProject) == 0:
                return False, f'Actor has no ADMIN_USERS permission for user {self.userId}.'
            allowed: list[Iri] = []
            for proj in self.inProject.keys():
                if actor.inProject.get(proj) is None:
                    return False, f'Actor has no ADMIN_USERS permission for project {proj}'
                else:
                    if AdminPermission.ADMIN_USERS not in actor.inProject.get(proj):
                        return False, f'Actor has no ADMIN_USERS permission for project {proj}'
            return True, "OK..."

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Creates the given user in the triple store. Before the creation, the method checks if a
        user with the given userID or userIri already exists and raises an exception.
        :return: None
        :raises OldapErrorAlreadyExists: User already exists
        :raises OldapValueError: PermissionSet is not existing
        :raises OldapError: Internal error
        :raises  OldapErrorNoPermission: No permission to create user for given project(s)
        """

        if self._con is None:
            raise OldapError("Cannot create: no connection")

        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        if self.userIri is None:
            self.userIri = Iri()
        context = Context(name=self._con.context_name)
        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?user
        FROM oldap:admin
        WHERE {{
            ?user a oldap:User .
            ?user oldap:userId {self.userId.toRdf} .         
        }}
        """

        sparql2 = context.sparql_context
        sparql2 += f"""
        SELECT ?user
        FROM oldap:admin
        WHERE {{
            ?user a oldap:User .
            FILTER(?user = {self.userIri.toRdf})
        }}
        """

        projs = [x.toRdf for x in self.inProject.keys()]
        projslist = ", ".join(projs)
        proj_test = context.sparql_context
        proj_test += f"""
        SELECT ?project
        FROM oldap:admin
        WHERE {{
            ?project a oldap:Project .
            FILTER(?project IN ({projslist}))
        }}
        """

        perms = [x.toRdf for x in self.hasPermissions]
        perms = ", ".join(perms)
        pset_test = context.sparql_context
        pset_test += f"""
        SELECT ?permissionset
        FROM oldap:admin
        WHERE {{
            ?permissionset a oldap:PermissionSet .
            FILTER(?permissionset IN ({perms}))
        }}
        """

        timestamp = Xsd_dateTime.now()
        blank = ''
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH oldap:admin {{\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}}{self.userIri.toRdf} a oldap:User'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:userId {self.userId.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}foaf:familyName {self.familyName.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}foaf:givenName {self.givenName.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:credentials {self.credentials.toRdf}'
        activeval = "true" if self.isActive else "false"
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:isActive {activeval}'
        star = ''
        if self.inProject:
            project = [p.toRdf for p in self.inProject.keys()]
            rdfstr = ", ".join(project)
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:inProject {rdfstr}'
            for p in self.inProject.keys():
                for admin_p in self.inProject[p]:  # TODO: May be use .get() instead of [] !!!!!!!!!!!!!!!!!!!!!!!!!
                    star += f'{blank:{(indent + 2) * indent_inc}}<<{self.userIri.toRdf} oldap:inProject {p.toRdf}>> oldap:hasAdminPermission {admin_p.value} .\n'
        if self.hasPermissions:
            rdfstr = ", ".join([str(x) for x in self.hasPermissions])
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:hasPermissions {rdfstr}'
        sparql += " .\n\n"
        sparql += star
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(sparql1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'A user with a user ID "{self.userId}" already exists')

        try:
            jsonobj = self._con.transaction_query(sparql2)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'A user with a user IRI "{self.userIri}" already exists')

        try:
            jsonobj = self._con.transaction_query(proj_test)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) != len(projs):
            self._con.transaction_abort()
            raise OldapErrorValue("One of the projects is not existing!")

        try:
            jsonobj = self._con.transaction_query(pset_test)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) != len(self.hasPermissions):
            self._con.transaction_abort()
            raise OldapErrorValue("One of the permission sets is not existing!")

        try:
            self._con.transaction_update(sparql)
        except OldapError:
            self._con.transaction_abort()
            raise
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        self._creator = self._con.userIri
        self._created = timestamp
        self._contributor = self._con.userIri
        self._modified = timestamp

    @classmethod
    def read(cls, con: IConnection, userId: Xsd_NCName | str) -> Self:
        """
        Reads a User instance from the data in the triple store
        :param con: IConnection instance
        :type con: IConnection
        :param userId: The userId of the user to be read
        :type userId: Xsd_NCName | str
        :return: Self
        :raises OldapErrorNotFound: Required user does ot exist
        """
        if isinstance(userId, str):
            userId = Xsd_NCName(userId)

        context = Context(name=con.context_name)
        jsonobj = con.query(UserDataclass.sparql_query(context, userId))
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OldapErrorNotFound(f'User "{userId}" not found.')
        instance = cls(con=con)
        instance._create_from_queryresult(res)
        return instance

    @staticmethod
    def search(*, con: IConnection,
               userId: Optional[Xsd_NCName | str] = None,
               familyName: Optional[str | Xsd_string] = None,
               givenName: Optional[str | Xsd_string] = None,
               inProject: Optional[Iri | str] = None) -> List[Xsd_anyURI]:
        """
        Search for a user in the database. The user can be found by the

        - userId
        - familyName
        - givenName
        - inProject

        In each case, the full string is compared. If more than one parameter is given, they are
        combined by a logical AND operation. That is, all parameters have to fit.
        :param con: IConnection instance
        :type con: IConnection
        :param userId: The userId of the user to be searched for in the database
        :type userId: Xsd_NCName | str
        :param familyName: The family name of the user to be searched for in the database
        :type familyName: str
        :param givenName: The givenname of the user to be searched for in the database
        :type givenName: str
        :param inProject: The project the user is member of
        :type inProject: Xsd_anyURI | Xsd_QName | str
        :return: List of users
        :rtype: List[AnyIRI]
        """
        if userId and not isinstance(userId, Xsd_NCName):
            userId = Xsd_NCName(userId)
        familyName = Xsd_string(familyName) if familyName else None
        givenName = Xsd_string(givenName) if givenName else None
        if not isinstance(inProject, Iri):
            inProject = Iri(inProject) if inProject else None
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += 'SELECT DISTINCT ?user\n'
        sparql += 'FROM oldap:admin\n'
        sparql += 'WHERE {\n'
        sparql += '   ?user a oldap:User .\n'
        if userId is not None:
            sparql += '   ?user oldap:userId ?user_id .\n'
            sparql += f'   FILTER(?user_id = {userId.toRdf})\n'
        if familyName is not None:
            sparql += '   ?user foaf:familyName ?family_name .\n'
            sparql += f'   FILTER(STR(?family_name) = {familyName.toRdf})\n'
        if givenName is not None:
            sparql += '   ?user foaf:givenName ?given_name .\n'
            sparql += f'   FILTER(STR(?given_name) = {givenName.toRdf})\n'
        if inProject is not None:
            sparql += '   ?user oldap:inProject ?project .\n'
            sparql += f'   FILTER(?project = {inProject.toRdf})\n'
        sparql += '}\n'
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        users = []
        for r in res:
            users.append(r['user'])
        return users

    def delete(self) -> None:
        """
        Delete the given user from the triple store
        :return: None
        """
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        #
        # TODO: Test, if the User is referenced as Owner of data etc. If so, raise an error. The User should then
        # be set inactive by setting the flag "isActive" to False!
        #

        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        DELETE {{
            <<?user oldap:inProject ?proj>> oldap:hasAdminPermission ?rval .    
        }}
        WHERE {{
            ?user a oldap:User .
            ?user oldap:userId {self.userId.toRdf} .
        }} ;
        DELETE WHERE {{
            ?user a oldap:User .
            ?user oldap:userId {self.userId.toRdf} .
            ?user ?prop ?val .
        }} 
        """
        # TODO: use transaction for error handling
        self._con.update_query(sparql)

    def update(self) -> None:
        """
        Update an existing user in the triple store. This method writes all changes that have made to the
        user instance to the database.
        :return: None
        :raises OldapErrorUpdateFailed: Updating user failed because user has been changed through race condition
        :raises OldapValueError: A PermissionSet is not existing
        :raises OldapError: An internal error occurred
        """
        if self._con is None:
            raise OldapError("Cannot create: no connection")

        result, message = self.check_for_permissions()
        #
        # Special case: The user should be able to change its own password!
        #
        actor = self._con.userdata
        if actor.userIri == self.userIri and len(self.changeset) == 1 and self.changeset.get(UserAttr.CREDENTIALS):
            result = True
        if not result:
            raise OldapErrorNoPermission(message)

        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        ptest, ptest_len, tmpsparql = self._sparql_update()
        sparql += tmpsparql
        self._con.transaction_start()
        try:
            modtime = self.get_modified_by_iri(Xsd_QName('oldap:admin'), self.userIri)
        except OldapError:
            self._con.transaction_abort()
            raise
        if modtime != self.modified:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed(
                f'Modifying user "{self.userId}" failed because of changed modification time: {modtime}')
        if ptest and ptest_len > 0:
            ptest_sparql = context.sparql_context
            ptest_sparql += ptest
            jsonobj = self._con.transaction_query(ptest_sparql)
            res = QueryProcessor(context, jsonobj)
            if len(res) != ptest_len:
                self._con.transaction_abort()
                raise OldapErrorValue("One of the permission sets is not existing!")
        try:
            self._con.transaction_update(sparql)
            self.set_modified_by_iri(Xsd_QName('oldap:admin'), self.userIri, self.modified, timestamp)
            modtime = self.get_modified_by_iri(Xsd_QName('oldap:admin'), self.userIri)
        except OldapError:
            self._con.transaction_abort()
            raise
        if timestamp != modtime:
            raise OldapErrorUpdateFailed("Update failed! Timestamp does not match")
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        self.modified = timestamp


if __name__ == '__main__':
    pass
    # con = Connection(server='http://localhost:7200',
    #                  repo="oldap",
    #                  userId="rosenth",
    #                  credentials="RioGrande",
    #                  context_name="DEFAULT")
    #
    # user = User.read(con, 'rosenth')
    # print(user)
    # user2 = User(con=con,
    #              userId=NCName("testuser"),
    #              family_name="Test",
    #              given_name="Test",
    #              credentials="Ein@geheimes&Passw0rt",
    #              inProject={QName('oldap:HyperHamlet'): [AdminPermission.ADMIN_USERS,
    #                                                      AdminPermission.ADMIN_RESOURCES,
    #                                                      AdminPermission.ADMIN_CREATE]},
    #              hasPermissions=[QName('oldap:GenericView')])
    # print(user2)
    # user2.create()
    # user3 = User.read(con, 'testuser')
    # print(user3)
    # jsonstr = json.dumps(user2, default=serializer.encoder_default, indent=4)
    # print(jsonstr)
    # user3 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
    # print(user3)
