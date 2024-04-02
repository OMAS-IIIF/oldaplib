"""
# User class

This module implements the Python representation of an OLDAP user. It offers methods to

- create
- read
- search
- update
- delete

a user from the triple store. The User class inherits from
[UserDataclass](/python_docstrings/userdataclass/#omaslib.src.user_dataclass.UserFields). UserDataclass
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

- _userIri_: IRI of the user, cannot be changed (RDF property `omas:userIri`)
- _userId_: User ID as NCName (RDF property `omas:userId`)
- _familyName_: Family name as str (RDF property `foaf:familyName`)
- _givenName_: Given name or first name as str(RDF property `foaf:givenName`)
- _credentials_: Credential (password) (RDF property `omas:credentials`)
- _isActive_: Is the user active as bool? (RDF property `omas:isActive`)
- _inProject_: Membership to projects and administrative permissions for this project (RDF property `omas:inProject)
- _hsPermission_: Permissions for data as sets of QNames (RDF property `omas:hasPermissions`)

These properties can be accessed as normal python class properties or using the dictionary syntax. The keys
are defined in the [UserFields](/python_docstrings/userdataclass/#omaslib.src.user_dataclass.UserFields) Enum class.
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

A user is created using the method [create()](/python_docstrings/user/#omaslib.src.user.User.create) as follows:

```python
user = User(con=self._connection,
            userIri=AnyIRI("https://orcid.org/0000-0002-9991-2055"),
            userId=NCName("edison"),
            family_name="Edison",
            given_name="Thomas A.",
            credentials="Lightbulb&Phonograph",
            inProject={QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                   AdminPermission.ADMIN_RESOURCES,
                                                   AdminPermission.ADMIN_CREATE}},
            hasPermissions={QName('omas:GenericView')})
user.create()
```

- __userIri__ is an optional parameter that allows to give the user a unique IRI. If possible, the
  [ORCID](https://orcid.org) ID should be given. If this parameter is omitted, OLDAP generates a unique IRI from the URN
  namespace for the user.
- __userId__ must be an [NCName](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.NCName)
- __credentials__ is a password that is converted to a bcrypt hash
- __inProject__ is a dictionary with the keys being the projects that the user is a member of. The values are
  sets of administrative privileges as defined in [AdminPermissions](/python_docstrings/permissions#AdminPermissions)
- __hasPermissions__ are links to PermissionSet's that define the access permissions for resources.

Please note that the class constructor does *not* create the user in the triple store. In order to create
the user in the database, `<User>.create()`has to be called.

## Reading a user from the database

In order to read all user data from the triple store, the method [read()](/python_docstrings/user/#omaslib.src.user.User.read) is used as
follows:

```python
user = User.read(con=self._connection, userId="rosenth")
```

The `userId` must be known and passed either as string or NCName.

## Searching for a user in the database

OLDAP allows to search for users within the database. The method [search()](/python_docstrings/user/#omaslib.src.user.User.search)
performs a search. The string given must match in total with the entry in the database. The method accepts also
several arguments which are combined by a logical AND.

```python
users = User.search(con=self._connection,userId="fornaro")

users = User.search(con=self._connection, familyName="Rosenthaler")

users = User.search(con=self._connection, givenName="John")

users = User.search(con=self._connection, inProject=QName("omas:HyperHamlet"))

users = User.search(con=self._connection, inProject=AnyIRI("http://www.salsah.org/version/2.0/SwissBritNet"))

users = User.search(con=self._connection, userId="GAGA")
```

## Updating a User

Several properties of a user can be changed using the [update()](/python_docstrings/user/#omaslib.src.user.User.update) method. In a first step, the properties
of a user instance are changed, then the `update()` method writes the changes to the triple store.

The following example exemplifies the procedure:

```python
    user2 = User.read(con=self._connection, userId="edison")  # read the user from the triple store
    user2.userId = "aedison"  # change the userId
    user2.familyName = "Edison et al."  # change the familyName
    user2.givenName = "Thomas"  # change the givenName
    user2.hasPermissions.add(QName('omas:GenericRestricted'))  # add a permission set
    user2.hasPermissions.add(QName('omas:HyperHamletMember'))  # add a permission set
    user2.hasPermissions.remove(QName('omas:GenericView'))  # remove a permission set
    user2.inProject[QName('omas:SystemProject')] = {AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES}
    user2.inProject[QName('omas:HyperHamlet')].remove(AdminPermission.ADMIN_USERS)
    user2.update()
```

## Deleting a User

The method [delete()](/python_docstrings/user/#omaslib.src.user.User.delete) deletes the given user from
the database:

```python
user3 = User.read(con=self._connection, userId="aedison")
user3.delete()
```
"""

import uuid
from datetime import datetime
from typing import List, Self, Dict, Set, Optional

from omaslib.src.helpers.context import Context
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_boolean import Xsd_boolean
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.xsd.xsd_datetime import Xsd_dateTime
from omaslib.src.xsd.xsd_string import Xsd_string
from omaslib.src.helpers.omaserror import OmasError, OmasErrorAlreadyExists, OmasErrorNotFound, OmasErrorUpdateFailed, \
    OmasErrorValue, OmasErrorNoPermission
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.enums.permissions import AdminPermission
from omaslib.src.helpers.tools import str2qname_anyiri, lprint
from omaslib.src.iconnection import IConnection
from omaslib.src.model import Model
from omaslib.src.user_dataclass import UserDataclass


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

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Creates the given user in the triple store. Before the creation, the method checks if a
        user with the given userID or userIri already exists and raises an exception.
        :return: None
        :raises OmasErrorAlreadyExists: User already exists
        :raises OmasValueError: PermissionSet is not existing
        :raises OmasError: Internal error
        :raises  OmasErrorNoPermission: No permission to create user for given project(s)
        """

        if self._con is None:
            raise OmasError("Cannot create: no connection")
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('omas:SystemProject'))
        is_root: bool = False
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            is_root = True
        if not is_root:
            for proj in self.inProject.keys():
                if actor.inProject.get(proj) is None:
                    raise OmasErrorNoPermission(f'No permission to create user in project {proj}.')
                if AdminPermission.ADMIN_USERS not in actor.inProject.get(proj):
                    raise OmasErrorNoPermission(f'No permission to create user in project {proj}.')

        if self.userIri is None:
            self.userIri = Iri()
        context = Context(name=self._con.context_name)
        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?user
        FROM omas:admin
        WHERE {{
            ?user a omas:User .
            ?user omas:userId {self.userId.toRdf} .         
        }}
        """

        sparql2 = context.sparql_context
        sparql2 += f"""
        SELECT ?user
        FROM omas:admin
        WHERE {{
            ?user a omas:User .
            FILTER(?user = {self.userIri.toRdf})
        }}
        """

        projs = [x.toRdf for x in self.inProject.keys()]
        projslist = ", ".join(projs)
        proj_test = context.sparql_context
        proj_test += f"""
        SELECT ?project
        FROM omas:admin
        WHERE {{
            ?project a omas:Project .
            FILTER(?project IN ({projslist}))
        }}
        """

        perms = [x.toRdf for x in self.hasPermissions]
        perms = ", ".join(perms)
        pset_test = context.sparql_context
        pset_test += f"""
        SELECT ?permissionset
        FROM omas:admin
        WHERE {{
            ?permissionset a omas:PermissionSet .
            FILTER(?permissionset IN ({perms}))
        }}
        """

        timestamp = Xsd_dateTime.now()
        blank = ''
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH omas:admin {{\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}}{self.userIri.toRdf} a omas:User'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}omas:userId {self.userId.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}foaf:familyName {self.familyName.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}foaf:givenName {self.givenName.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}omas:credentials {self.credentials.toRdf}'
        activeval = "true" if self.isActive else "false"
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}omas:isActive {activeval}'
        star = ''
        if self.inProject:
            project = [p.toRdf for p in self.inProject.keys()]
            rdfstr = ", ".join(project)
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}omas:inProject {rdfstr}'
            for p in self.inProject.keys():
                for admin_p in self.inProject[p]:  # TODO: May be use .get() instead of [] !!!!!!!!!!!!!!!!!!!!!!!!!
                    star += f'{blank:{(indent + 2) * indent_inc}}<<{self.userIri.toRdf} omas:inProject {p.toRdf}>> omas:hasAdminPermission {admin_p.value} .\n'
        if self.hasPermissions:
            rdfstr = ", ".join([str(x) for x in self.hasPermissions])
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
            jsonobj = self._con.transaction_query(proj_test)
        except OmasError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) != len(projs):
            self._con.transaction_abort()
            raise OmasErrorValue("One of the projects is not existing!")

        try:
            jsonobj = self._con.transaction_query(pset_test)
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
    def read(cls, con: IConnection, userId: Xsd_NCName | str) -> Self:
        """
        Reads a User instance from the data in the triple store
        :param con: IConnection instance
        :type con: IConnection
        :param userId: The userId of the user to be read
        :type userId: Xsd_NCName | str
        :return: Self
        :raises OmasErrorNotFound: Required user does ot exist
        """
        if isinstance(userId, str):
            userId = Xsd_NCName(userId)

        context = Context(name=con.context_name)
        jsonobj = con.query(UserDataclass.sparql_query(context, userId))
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OmasErrorNotFound(f'User "{userId}" not found.')
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
        sparql += 'FROM omas:admin\n'
        sparql += 'WHERE {\n'
        sparql += '   ?user a omas:User .\n'
        if userId is not None:
            sparql += '   ?user omas:userId ?user_id .\n'
            sparql += f'   FILTER(?user_id = {userId.toRdf})\n'
        if familyName is not None:
            sparql += '   ?user foaf:familyName ?family_name .\n'
            sparql += f'   FILTER(STR(?family_name) = {familyName.toRdf})\n'
        if givenName is not None:
            sparql += '   ?user foaf:givenName ?given_name .\n'
            sparql += f'   FILTER(STR(?given_name) = {givenName.toRdf})\n'
        if inProject is not None:
            sparql += '   ?user omas:inProject ?project .\n'
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
        actor = self._con.userdata
        sysperms = actor.inProject.get(Xsd_QName('omas:SystemProject'))
        is_root: bool = False
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            is_root = True
        if not is_root:
            for proj in self.inProject.keys():
                if actor.inProject.get(proj) is None:
                    raise OmasErrorNoPermission(f'No permission to delete user in project {proj}.')
                if AdminPermission.ADMIN_USERS not in actor.inProject.get(proj):
                    raise OmasErrorNoPermission(f'No permission to delete user in project {proj}.')

        #
        # TODO: Test, if the User is referenced as Owner of data etc. If so, raise an error. The User should then
        # be set inactive by setting the flag "isActive" to False!
        #

        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        DELETE {{
            <<?user omas:inProject ?proj>> omas:hasAdminPermission ?rval .    
        }}
        WHERE {{
            ?user a omas:User .
            ?user omas:userId {self.userId.toRdf} .
        }} ;
        DELETE WHERE {{
            ?user a omas:User .
            ?user omas:userId {self.userId.toRdf} .
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
        :raises OmasErrorUpdateFailed: Updating user failed because user has been changed through race condition
        :raises OmasValueError: A PermissionSet is not existing
        :raises OmasError: An internal error occurred
        """

        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(Xsd_QName('omas:SystemProject'))
        is_root: bool = False
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            is_root = True
        if not is_root:
            for proj in self.inProject.keys():
                if actor.inProject.get(proj) is None:
                    raise OmasErrorNoPermission(f'No permission to modify user in project {proj}.')
                if AdminPermission.ADMIN_USERS not in actor.inProject.get(proj):
                    raise OmasErrorNoPermission(f'No permission to modify user in project {proj}.')

        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        ptest, ptest_len, tmpsparql = self._sparql_update()
        sparql += tmpsparql
        self._con.transaction_start()
        try:
            modtime = self.get_modified_by_iri(Xsd_QName('omas:admin'), self.userIri)
        except OmasError:
            self._con.transaction_abort()
            raise
        if modtime != self.modified:
            self._con.transaction_abort()
            raise OmasErrorUpdateFailed(
                f'Modifying user "{self.userId}" failed because of changed modification time: {modtime}')
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
            self.set_modified_by_iri(Xsd_QName('omas:admin'), self.userIri, self.modified, timestamp)
            modtime = self.get_modified_by_iri(Xsd_QName('omas:admin'), self.userIri)
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
    pass
    # con = Connection(server='http://localhost:7200',
    #                  repo="omas",
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
    #              inProject={QName('omas:HyperHamlet'): [AdminPermission.ADMIN_USERS,
    #                                                      AdminPermission.ADMIN_RESOURCES,
    #                                                      AdminPermission.ADMIN_CREATE]},
    #              hasPermissions=[QName('omas:GenericView')])
    # print(user2)
    # user2.create()
    # user3 = User.read(con, 'testuser')
    # print(user3)
    # jsonstr = json.dumps(user2, default=serializer.encoder_default, indent=4)
    # print(jsonstr)
    # user3 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
    # print(user3)
