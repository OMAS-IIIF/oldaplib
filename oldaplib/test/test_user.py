import unittest
from copy import deepcopy
from pathlib import Path
from time import sleep

from oldaplib.src.connection import Connection
from oldaplib.src.enums.userattr import UserAttr
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.helpers.tools import str2qname_anyiri
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapErrorAlreadyExists, OldapErrorValue, OldapErrorNoPermission, OldapError
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.user import User
from oldaplib.src.in_project import InProjectClass
from oldaplib.src.xsd.xsd_string import Xsd_string

def find_project_root(current_path):
    # Climb up the directory hierarchy and check for a marker file
    path = Path(current_path).absolute()
    while not (path / 'pyproject.toml').exists():
        if path.parent == path:
            # Root of the filesystem, file not found
            raise RuntimeError('Project root not found')
        path = path.parent
    return path


class TestUser(unittest.TestCase):
    _context: Context
    _connection: Connection
    _unpriv: Connection

    @classmethod
    def setUp(cls):
        super().setUpClass()
        project_root = find_project_root(__file__)

        cls._context = Context(name="DEFAULT")

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="oldap",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._unpriv = Connection(server='http://localhost:7200',
                                 repo="oldap",
                                 userId="fornaro",
                                 credentials="RioGrande",
                                 context_name="DEFAULT")

        # user = User(con=cls._connection, userId=NCName("coyote"))
        # user.delete()
        cls._connection.clear_graph(Xsd_QName('oldap:admin'))

        file = project_root / 'oldaplib' / 'ontologies' / 'admin.trig'
        cls._connection.upload_turtle(file)
        sleep(1)  # upload may take a while...

    def tearDown(self):
        pass

    #  @unittest.skip('Work in progress')
    def test_constructor(self):
        user = User(con=self._connection,
                    userId=Xsd_NCName("testuser_without"),
                    familyName="TestWithout",
                    givenName="TestWithout",
                    credentials="Ein@geheimes&Passw0rt")

        user = User(con=self._connection,
                    userId=Xsd_NCName("testuser_empty"),
                    familyName="TestEmpty",
                    givenName="TestEmpty",
                    credentials="Ein@geheimes&Passw0rt",
                    inProject={})

        user = User(con=self._connection,
                    userId=Xsd_NCName("testuser_empty"),
                    familyName="TestEmpty",
                    givenName="TestEmpty",
                    credentials="Ein@geheimes&Passw0rt",
                    inProject={Iri('oldap:HyperHamlet'): {}},
                    hasPermissions={})


        user = User(con=self._connection,
                    userId=Xsd_NCName("testuser"),
                    familyName="Test",
                    givenName="Test",
                    credentials="Ein@geheimes&Passw0rt",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Xsd_QName('oldap:GenericView')})

        self.assertEqual(user.userId, Xsd_NCName("testuser"))
        self.assertEqual(user.familyName, "Test")
        self.assertEqual(user.givenName, "Test")
        self.assertEqual(user.inProject, InProjectClass({Iri("oldap:HyperHamlet"): {
            AdminPermission.ADMIN_USERS,
            AdminPermission.ADMIN_RESOURCES,
            AdminPermission.ADMIN_CREATE
        }}))
        self.assertEqual(user.hasPermissions, {Xsd_QName('oldap:GenericView')})

    def test_user_deepcopy(self):
        user = User(con=self._connection,
                    userId=Xsd_NCName("testuser"),
                    familyName="Test",
                    givenName="Test",
                    credentials="Ein@geheimes&Passw0rt",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Xsd_QName('oldap:GenericView')})
        user2 = deepcopy(user)
        self.assertFalse(user is user2)
        self.assertEqual(user.userId, user2.userId)
        self.assertEqual(user.userIri, user2.userIri)
        self.assertEqual(user.familyName, user2.familyName)
        self.assertEqual(user.credentials, user2.credentials)
        self.assertEqual(user.inProject[Iri('oldap:HyperHamlet')], user2.inProject[Iri('oldap:HyperHamlet')])
        self.assertEqual(user.hasPermissions, user2.hasPermissions)

    # @unittest.skip('Work in progress')
    def test_read_user_from_id(self):
        user = User.read(con=self._connection, userId="rosenth", ignore_cache=True)
        self.assertEqual(user.userId, Xsd_NCName("rosenth"))
        self.assertEqual(user.userIri, Iri("https://orcid.org/0000-0003-1681-4036"))
        self.assertEqual(user.familyName, Xsd_string("Rosenthaler"))
        self.assertEqual(user.givenName, Xsd_string("Lukas"))
        self.assertEqual(user.inProject, InProjectClass({
            Iri("oldap:SystemProject"): {AdminPermission.ADMIN_OLDAP},
            Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_RESOURCES}
        }))
        self.assertEqual(user.hasPermissions, {Iri("oldap:GenericRestricted"), Iri('oldap:GenericView')})

    def test_read_user_from_iri(self):
        user = User.read(con=self._connection, userId=Iri("https://orcid.org/0000-0003-1681-4036"), ignore_cache=True)
        self.assertEqual(user.userId, Xsd_NCName("rosenth"))
        self.assertEqual(user.userIri, Iri("https://orcid.org/0000-0003-1681-4036"))
        self.assertEqual(user.familyName, Xsd_string("Rosenthaler"))
        self.assertEqual(user.givenName, Xsd_string("Lukas"))
        self.assertEqual(user.inProject, InProjectClass({
            Iri("oldap:SystemProject"): {AdminPermission.ADMIN_OLDAP},
            Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_RESOURCES}
        }))
        self.assertEqual(user.hasPermissions, {Iri("oldap:GenericRestricted"), Iri('oldap:GenericView')})

    #  #unittest.skip('Work in progress')
    def test_read_unknown_user(self):
        with self.assertRaises(OldapErrorNotFound) as ex:
            user = User.read(con=self._connection, userId="nosuchuser", ignore_cache=True)
        self.assertEqual(str(ex.exception), 'User "nosuchuser" not found.')

    def test_read_user_with_cache(self):
        user = User.read(con=self._connection, userId="rosenth", ignore_cache=True)
        user2 = User.read(con=self._connection, userId="rosenth", ignore_cache=True)
        self.assertFalse(user2 is user)

        self.assertEqual(user2.userId, Xsd_NCName("rosenth"))
        self.assertEqual(user.userId, user2.userId)
        self.assertFalse(user.userId is user2.userId)

        self.assertEqual(user2.userIri, Iri("https://orcid.org/0000-0003-1681-4036"))
        self.assertEqual(user.userIri, user2.userIri)
        self.assertFalse(user.userIri is user2.userIri)

        self.assertEqual(user2.familyName, Xsd_string("Rosenthaler"))
        self.assertEqual(user.familyName, user2.familyName)
        self.assertFalse(user.familyName is user2.familyName)

        self.assertEqual(user2.givenName, Xsd_string("Lukas"))
        self.assertEqual(user.givenName, user2.givenName)
        self.assertFalse(user.givenName is user2.givenName)

        self.assertEqual(user2.inProject, InProjectClass({
            Iri("oldap:SystemProject"): {AdminPermission.ADMIN_OLDAP},
            Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_RESOURCES}
        }))
        self.assertEqual(user.inProject, user2.inProject)
        self.assertFalse(user.inProject is user2.inProject)

        self.assertEqual(user2.hasPermissions, {Iri("oldap:GenericRestricted"), Iri('oldap:GenericView')})
        self.assertEqual(user.hasPermissions, user2.hasPermissions)
        self.assertFalse(user.hasPermissions is user2.hasPermissions)

        user3 = User.read(con=self._connection, userId=Iri("https://orcid.org/0000-0003-1681-4036"))
        self.assertFalse(user3 is user)

        self.assertEqual(user3.userId, Xsd_NCName("rosenth"))
        self.assertEqual(user.userId, user3.userId)
        self.assertFalse(user.userId is user3.userId)

        self.assertEqual(user3.userIri, Iri("https://orcid.org/0000-0003-1681-4036"))
        self.assertEqual(user.userIri, user3.userIri)
        self.assertFalse(user.userIri is user3.userIri)

        self.assertEqual(user3.familyName, Xsd_string("Rosenthaler"))
        self.assertEqual(user.familyName, user3.familyName)
        self.assertFalse(user.familyName is user3.familyName)

        self.assertEqual(user3.givenName, Xsd_string("Lukas"))
        self.assertEqual(user.givenName, user3.givenName)
        self.assertFalse(user.givenName is user3.givenName)

        self.assertEqual(user3.inProject, InProjectClass({
            Iri("oldap:SystemProject"): {AdminPermission.ADMIN_OLDAP},
            Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_RESOURCES}
        }))
        self.assertEqual(user.inProject, user3.inProject)
        self.assertFalse(user.inProject is user3.inProject)

        self.assertEqual(user3.hasPermissions, {Iri("oldap:GenericRestricted"), Iri('oldap:GenericView')})
        self.assertEqual(user.hasPermissions, user3.hasPermissions)
        self.assertFalse(user.hasPermissions is user3.hasPermissions)


    #  #unittest.skip('Work in progress')
    def test_search_user(self):
        users = User.search(con=self._connection, userId="fornaro")
        self.assertEqual([Iri("https://orcid.org/0000-0003-1485-4923")], users)

        users = User.search(con=self._connection, familyName="Rosenthaler")
        self.assertEqual([Iri("https://orcid.org/0000-0003-1681-4036")], users)

        users = User.search(con=self._connection, givenName="John")
        self.assertEqual([Iri("urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b")], users)

        users = User.search(con=self._connection, inProject=Xsd_QName("oldap:HyperHamlet"))
        self.assertEqual([Iri("https://orcid.org/0000-0003-1681-4036"),
                          Iri("https://orcid.org/0000-0003-1485-4923"),
                          Iri("https://orcid.org/0000-0001-9277-3921")], users)

        users = User.search(con=self._connection, inProject=Iri("http://www.salsah.org/version/2.0/SwissBritNet"))
        self.assertEqual([Iri("https://orcid.org/0000-0002-7403-9595")], users)

        users = User.search(con=self._connection, userId="GAGA")
        self.assertEqual([], users)

    #  #unittest.skip('Work in progress')
    def test_search_user_injection(self):
        with self.assertRaises(OldapErrorValue) as ex:
            users = User.search(con=self._connection, userId="fornaro\".}\nSELECT * WHERE {?s ?p ?s})#")
        self.assertEqual(str(ex.exception), 'Invalid string "fornaro".}\nSELECT * WHERE {?s ?p ?s})#" for NCName')

        users = User.search(con=self._connection, familyName="Rosenthaler\".}\nSELECT * WHERE{?s ?p ?s})#")
        self.assertEqual(len(users), 0)
        users = User.search(con=self._connection, givenName="John\".}\nSELECT * WHERE{?s ?p ?s})#")
        self.assertEqual(len(users), 0)

        with self.assertRaises(OldapErrorValue) as ex:
            users = User.search(con=self._connection, inProject="oldap:HyperHamlet\".}\nSELECT * WHERE{?s ?p ?s})#")
        self.assertEqual(str(ex.exception), 'Invalid string for IRI: "oldap:HyperHamlet".}\nSELECT * WHERE{?s ?p ?s})#"')

    #  #unittest.skip('Work in progress')
    def test_create_user(self):
        """Test if the creation of a new user works a intended"""
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0003-3478-9313"),
                    userId=Xsd_NCName("coyote"),
                    familyName="Coyote",
                    givenName="Wiley E.",
                    credentials="Super-Genius",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                               AdminPermission.ADMIN_RESOURCES,
                                                               AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')},
                    isActive=True)
        user.create()
        self.assertIsNotNone(user.created)
        self.assertIsNotNone(user.creator)
        self.assertIsNotNone(user.modified)
        self.assertIsNotNone(user.contributor)
        user2 = User.read(con=self._connection, userId="coyote", ignore_cache=True)
        self.assertEqual(user2.userId, user.userId)
        self.assertEqual(user2.userIri, user.userIri)
        self.assertEqual(user2.familyName, user.familyName)
        self.assertEqual(user2.givenName, user.givenName)
        self.assertEqual(user2.inProject, user.inProject)
        self.assertEqual(user2.hasPermissions, user.hasPermissions)
        self.assertTrue(user2.isActive)

    #  #unittest.skip('Work in progress')
    def test_create_user_no_admin_perms(self):
        """Create a user which belongs to oldap:HyperHamlet without admin permissions"""
        user = User(con=self._connection,
                    userId=Xsd_NCName("birdy"),
                    familyName="Birdy",
                    givenName="Tweetie",
                    credentials="Sylvester",
                    inProject={Iri('oldap:HyperHamlet'): set()},
                    hasPermissions={Iri('oldap:GenericView')},
                    isActive=True)
        user.create()
        del user
        user = User.read(con=self._connection, userId=Xsd_NCName("birdy"), ignore_cache=True)
        self.assertEqual(user.familyName, "Birdy")

    #  #unittest.skip('Work in progress')
    def test_create_user_no_in_project(self):
        """Create a user which is not associated with a project"""
        user = User(con=self._connection,
                    userId=Xsd_NCName("yogi"),
                    familyName="Baer",
                    givenName="Yogi",
                    credentials="BuBu",
                    hasPermissions={Iri('oldap:GenericView')},
                    isActive=True)
        user.create()
        del user
        user = User.read(con=self._connection, userId=Xsd_NCName("yogi"), ignore_cache=True)
        self.assertEqual(user.familyName, "Baer")

    #  #unittest.skip('Work in progress')
    def test_create_user_no_permset(self):
        """Create a user that is associated with oldap:HyperHmalet, but is not linked a PermissionSet"""
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0003-3478-9313"),
                    userId=Xsd_NCName("speedy"),
                    familyName="Ganzales",
                    givenName="Speedy",
                    credentials="fasterthanlight",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                               AdminPermission.ADMIN_RESOURCES,
                                                               AdminPermission.ADMIN_CREATE}},
                    isActive=True)
        user.create()
        del user
        user = User.read(con=self._connection, userId=Xsd_NCName("speedy"), ignore_cache=True)
        self.assertEqual(user.familyName, "Ganzales")


    #  #unittest.skip('Work in progress')
    def test_create_user_no_useriri(self):
        """We create a user without giving an userIri. It should recieve a URN as userIRI"""
        user = User(con=self._connection,
                    userId=Xsd_NCName("sylvester"),
                    familyName="Sylvester",
                    givenName="Cat",
                    credentials="Birdy",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                               AdminPermission.ADMIN_RESOURCES,
                                                               AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')},
                    isActive=False)
        user.create()
        del user
        user = User.read(con=self._connection, userId=Xsd_NCName("sylvester"), ignore_cache=True)
        self.assertTrue(str(user.userIri).startswith("urn:uuid:"))
        self.assertFalse(user.isActive)

    #  #unittest.skip('Work in progress')
    def test_create_user_duplicate_userid(self):
        """Test that we cannot create a duplicate userId (here "fornaro")"""
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0003-3478-9314"),
                    userId=Xsd_NCName("fornaro"),
                    familyName="di Fornaro",
                    givenName="Petri",
                    credentials="Genius",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                               AdminPermission.ADMIN_RESOURCES,
                                                               AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        with self.assertRaises(OldapErrorAlreadyExists) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'A user with a user ID "fornaro" already exists')

    #  #unittest.skip('Work in progress')
    def test_create_user_duplicate_useriri(self):
        """Test that we cannot create a duplicate userIri"""
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0003-1681-4036"),
                    userId=Xsd_NCName("brown"),
                    familyName="Brown",
                    givenName="Emmett",
                    credentials="Time-Machine@1985",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                               AdminPermission.ADMIN_RESOURCES,
                                                               AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        with self.assertRaises(OldapErrorAlreadyExists) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'A user with a user IRI "https://orcid.org/0000-0003-1681-4036" already exists')

    #  #unittest.skip('Work in progress')
    def test_create_user_invalid_project(self):
        """Test that user creation will fail if we give an invalid project"""
        user = User(con=self._connection,
                    userId=Xsd_NCName("donald"),
                    familyName="Duck",
                    givenName="Donald",
                    credentials="Entenhausen@for&Ever",
                    inProject={Iri('oldap:NotExistingproject'): {AdminPermission.ADMIN_USERS,
                                                                AdminPermission.ADMIN_RESOURCES,
                                                                AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        with self.assertRaises(OldapErrorValue) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'One of the projects is not existing!')

    #  #unittest.skip('Work in progress')
    def test_create_user_invalid_permset(self):
        """Test that user creation will fail if we give an invalid permission set"""
        user = User(con=self._connection,
                    userId=Xsd_NCName("donald"),
                    familyName="Duck",
                    givenName="Donald",
                    credentials="Entenhausen@for&Ever",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView'), Xsd_QName('oldap:Gaga')})
        with self.assertRaises(OldapErrorValue) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'One of the permission sets is not existing!')

    #  #unittest.skip('Work in progress')
    def test_create_user_no_privilege(self):
        """Test that user creation will fail if we do not have the permission for the given project to create users"""
        user = User(con=self._unpriv,
                    userId=Xsd_NCName("donald"),
                    familyName="Duck",
                    givenName="Donald",
                    credentials="Entenhausen@for&Ever",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        with self.assertRaises(OldapErrorNoPermission) as ex:
            user.create()
        self.assertEqual('Actor has no ADMIN_USERS permission for project oldap:HyperHamlet', str(ex.exception), )

    #  #unittest.skip('Work in progress')
    def test_delete_user(self):
        """Test that user deletion does work"""
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2055"),
                    userId=Xsd_NCName("edison"),
                    familyName="Edison",
                    givenName="Thomas A.",
                    credentials="Lightbulb&Phonograph",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        user2 = User.read(con=self._connection, userId="edison", ignore_cache=True)
        self.assertEqual(user2.userIri, user.userIri)
        user2.delete()
        with self.assertRaises(OldapErrorNotFound) as ex:
            user = User.read(con=self._connection, userId="edison", ignore_cache=True)
        self.assertEqual(str(ex.exception), 'User "edison" not found.')

    #  #unittest.skip('Work in progress')
    def test_delete_user_unpriv(self):
        """Delete a user without having the permission should fail"""
        user = User.read(con=self._unpriv, userId="bugsbunny", ignore_cache=True)
        with self.assertRaises(OldapErrorNoPermission) as ex:
            user.delete()
        self.assertEqual('Actor has no ADMIN_USERS permission for project oldap:HyperHamlet', str(ex.exception))

    def test_update_user_permission_create(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2055"),
                    userId=Xsd_NCName("ampere"),
                    familyName="Ampère",
                    givenName="André-Marie",
                    credentials="Current",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE}})
        user.create()
        user = User.read(con=self._connection, userId="ampere", ignore_cache=True)
        user.hasPermissions = {Iri('oldap:GenericRestricted'), Iri('oldap:GenericView')}
        user.update()
        user = User.read(con=self._connection, userId="ampere", ignore_cache=True)
        self.assertEqual(user.hasPermissions, {Iri('oldap:GenericRestricted'), Iri('oldap:GenericView')})

    def test_update_user_permission_delete(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2055"),
                    userId=Xsd_NCName("ampere"),
                    familyName="Ampère",
                    givenName="André-Marie",
                    credentials="Current",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        user = User.read(con=self._connection, userId="ampere", ignore_cache=True)
        del user.hasPermissions
        user.update()
        user = User.read(con=self._connection, userId="ampere", ignore_cache=True)
        self.assertIsNone(user.hasPermissions)

    def test_update_user_permission_set_empty(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2055"),
                    userId=Xsd_NCName("ampere"),
                    familyName="Ampère",
                    givenName="André-Marie",
                    credentials="Current",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        user = User.read(con=self._connection, userId="ampere", ignore_cache=True)
        user.hasPermissions = []
        user.update()
        user = User.read(con=self._connection, userId="ampere", ignore_cache=True)
        self.assertIsNone(user.hasPermissions)

    def test_update_user_permission_set_None(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2055"),
                    userId=Xsd_NCName("ampere"),
                    familyName="Ampère",
                    givenName="André-Marie",
                    credentials="Current",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        user = User.read(con=self._connection, userId="ampere", ignore_cache=True)
        user.hasPermissions = None
        user.update()
        user = User.read(con=self._connection, userId="ampere", ignore_cache=True)
        self.assertIsNone(user.hasPermissions)

    def test_update_user_permissions_update_A(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2055"),
                    userId=Xsd_NCName("faraday"),
                    familyName="Faraday",
                    givenName="Michael",
                    credentials="electromagnetism",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        user = User.read(con=self._connection, userId="faraday", ignore_cache=True)
        user.hasPermissions.add(Iri('oldap:GenericRestricted'))
        user.update()
        user = User.read(con=self._connection, userId="faraday", ignore_cache=True)
        self.assertEqual(user.hasPermissions, {Iri('oldap:GenericRestricted'), Iri('oldap:GenericView')})

    def test_update_user_permissions_update_B(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2055"),
                    userId=Xsd_NCName("fourier"),
                    familyName="Fourier",
                    givenName="Joseph",
                    credentials="FrequencyAnalysis",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericRestricted'), Iri('oldap:GenericView')})
        user.create()
        user = User.read(con=self._connection, userId="fourier", ignore_cache=True)
        user.hasPermissions.remove(Iri('oldap:GenericRestricted'))
        user.update()
        user = User.read(con=self._connection, userId="fourier", ignore_cache=True)
        self.assertEqual(user.hasPermissions, {Iri('oldap:GenericView')})

    #  #unittest.skip('Work in progress')
    def test_update_user(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2055"),
                    userId=Xsd_NCName("edison"),
                    familyName="Edison",
                    givenName="Thomas A.",
                    credentials="Lightbulb&Phonograph",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        user2 = User.read(con=self._connection, userId="edison", ignore_cache=True)
        user2.userId = "aedison"
        user2.familyName = "Edison et al."
        user2.givenName = "Thomas"

        user2.hasPermissions.add(Iri('oldap:GenericRestricted'))
        user2.hasPermissions.add(Iri('hyha:HyperHamletMember'))
        user2.hasPermissions.remove(Iri('oldap:GenericView'))
        user2.inProject[Iri('oldap:SystemProject')] = {AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES}
        user2.inProject[Iri('oldap:HyperHamlet')].remove(AdminPermission.ADMIN_USERS)
        user2.inProject[Iri('oldap:HyperHamlet')].add(AdminPermission.ADMIN_LISTS)
        user2.update()
        user3 = User.read(con=self._connection, userId="aedison", ignore_cache=True)
        self.assertEqual({Iri('oldap:GenericRestricted'), Iri('hyha:HyperHamletMember')}, user3.hasPermissions)
        user3.hasPermissions.add(Iri('oldap:DoesNotExist'))
        with self.assertRaises(OldapErrorValue) as ex:
            user3.update()
            self.assertEqual(str(ex.exception), 'One of the permission sets is not existing!')

        self.assertEqual(user3.inProject[Iri('oldap:HyperHamlet')], {AdminPermission.ADMIN_RESOURCES,
                                                                     AdminPermission.ADMIN_CREATE,
                                                                     AdminPermission.ADMIN_LISTS})
        self.assertEqual(user3.inProject[Iri('oldap:SystemProject')], {AdminPermission.ADMIN_USERS,
                                                                       AdminPermission.ADMIN_RESOURCES})
        self.assertEqual(InProjectClass({Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_RESOURCES,
                                                                    AdminPermission.ADMIN_CREATE,
                                                                    AdminPermission.ADMIN_LISTS},
                                         Iri('oldap:SystemProject'): {AdminPermission.ADMIN_USERS,
                                                                           AdminPermission.ADMIN_RESOURCES}}), user3.inProject)
        del user3
        user4 = User.read(con=self._connection, userId="aedison", ignore_cache=True)
        user4.inProject = InProjectClass({Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS}})
        user4.update()
        del user4

    def test_update_user_in_project_set(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2066"),
                    userId=Xsd_NCName("tesla"),
                    familyName="Tesla",
                    givenName="Nikolai",
                    credentials="Alternative current",
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        user = User.read(con=self._connection, userId="tesla", ignore_cache=True)
        user.inProject = InProjectClass({Iri('http://www.salsah.org/version/2.0/SwissBritNet'): ObservableSet({AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE})})
        user.update()
        user = User.read(con=self._connection, userId="tesla", ignore_cache=True)
        self.assertEqual(user.inProject[Iri('http://www.salsah.org/version/2.0/SwissBritNet')], {AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE})

    def test_update_user_in_project_delete(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2066"),
                    userId=Xsd_NCName("tesla"),
                    familyName="Tesla",
                    givenName="Nikolai",
                    credentials="Alternative current",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                          AdminPermission.ADMIN_RESOURCES}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        user = User.read(con=self._connection, userId="tesla", ignore_cache=True)
        del user.inProject
        user.update()
        user = User.read(con=self._connection, userId="tesla", ignore_cache=True)
        self.assertIsNone(user.inProject)

    def test_update_user_in_project_modify_A(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2066"),
                    userId=Xsd_NCName("tesla"),
                    familyName="Tesla",
                    givenName="Nikolai",
                    credentials="Alternative current",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                          AdminPermission.ADMIN_RESOURCES}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        user = User.read(con=self._connection, userId="tesla", ignore_cache=True)
        user.inProject[Iri('http://www.salsah.org/version/2.0/SwissBritNet')] = {AdminPermission.ADMIN_RESOURCES}
        user.update()
        user = User.read(con=self._connection, userId="tesla", ignore_cache=True)
        self.assertEqual(user.inProject[Iri('oldap:HyperHamlet')], {AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES})
        self.assertEqual(user.inProject[Iri('http://www.salsah.org/version/2.0/SwissBritNet')], {AdminPermission.ADMIN_RESOURCES})

    def test_update_user_in_project_modify_B(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2067"),
                    userId=Xsd_NCName("volta"),
                    familyName="Volta",
                    givenName="Alessandro",
                    credentials="ElectricTension",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                          AdminPermission.ADMIN_RESOURCES},
                               Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {AdminPermission.ADMIN_MODEL}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        user = User.read(con=self._connection, userId="volta", ignore_cache=True)
        user.inProject[Iri('http://www.salsah.org/version/2.0/SwissBritNet')].add(AdminPermission.ADMIN_LISTS)
        user.update()
        user = User.read(con=self._connection, userId="volta", ignore_cache=True)
        self.assertEqual(user.inProject[Iri('oldap:HyperHamlet')], {AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES})
        self.assertEqual(user.inProject[Iri('http://www.salsah.org/version/2.0/SwissBritNet')], {AdminPermission.ADMIN_MODEL, AdminPermission.ADMIN_LISTS})

    def test_update_user_in_project_modify_C(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2067"),
                    userId=Xsd_NCName("voltaB"),
                    familyName="VoltaB",
                    givenName="AlessandroB",
                    credentials="ElectricTensionB",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                          AdminPermission.ADMIN_RESOURCES},
                               Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {AdminPermission.ADMIN_MODEL}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        user = User.read(con=self._connection, userId="voltaB", ignore_cache=True)
        user.inProject[Iri('http://www.salsah.org/version/2.0/SwissBritNet')] = {AdminPermission.ADMIN_LISTS}
        user.update()
        user = User.read(con=self._connection, userId="voltaB", ignore_cache=True)
        self.assertEqual(user.inProject[Iri('oldap:HyperHamlet')], {AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES})
        self.assertEqual(user.inProject[Iri('http://www.salsah.org/version/2.0/SwissBritNet')], {AdminPermission.ADMIN_LISTS})

    def test_update_user_in_project_modify_D(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2067"),
                    userId=Xsd_NCName("curie"),
                    familyName="Curie",
                    givenName="Marie",
                    credentials="Radiation",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                          AdminPermission.ADMIN_RESOURCES},
                               Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {AdminPermission.ADMIN_MODEL}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        user = User.read(con=self._connection, userId="curie", ignore_cache=True)
        user.inProject[Iri('oldap:HyperHamlet')].discard(AdminPermission.ADMIN_RESOURCES)
        user.update()
        user = User.read(con=self._connection, userId="curie", ignore_cache=True)
        self.assertEqual(user.inProject[Iri('oldap:HyperHamlet')], {AdminPermission.ADMIN_USERS})
        self.assertEqual(user.inProject[Iri('http://www.salsah.org/version/2.0/SwissBritNet')], {AdminPermission.ADMIN_MODEL})

    def test_update_user_permissions_C(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2066"),
                    userId=Xsd_NCName("tesla"),
                    familyName="Tesla",
                    givenName="Nikolai",
                    credentials="Alternative current",
                    inProject={Iri('oldap:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                          AdminPermission.ADMIN_RESOURCES}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        user = User.read(con=self._connection, userId="tesla", ignore_cache=True)
        user.inProject[Iri('oldap:HyperHamlet')].add(AdminPermission.ADMIN_CREATE)
        user.update()
        user = User.read(con=self._connection, userId="tesla", ignore_cache=True)
        self.assertEqual(user.inProject[Iri('oldap:HyperHamlet')], {AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE})


    #  #unittest.skip('Work in progress')
    def test_update_user_unpriv(self):
        user = User.read(con=self._unpriv, userId="bugsbunny", ignore_cache=True)
        user.credentials = "ChangedPassword"
        with self.assertRaises(OldapErrorNoPermission) as ex:
            user.update()
        self.assertEqual('Actor has no ADMIN_USERS permission for project oldap:HyperHamlet', str(ex.exception))

    #  #unittest.skip('Work in progress')
    def test_update_user_change_in_project(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0001-5925-2956"),
                    userId=Xsd_NCName("chiquet"),
                    familyName="Chiquet",
                    givenName="Vera",
                    credentials="Photography",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                        AdminPermission.ADMIN_USERS,
                        AdminPermission.ADMIN_RESOURCES,
                        AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        user.inProject = InProjectClass({Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {AdminPermission.ADMIN_OLDAP}})
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        self.assertEqual(user.inProject, InProjectClass({Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {AdminPermission.ADMIN_OLDAP}}))

    #  #unittest.skip('Work in progress')
    def test_update_user_empty_in_project(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-2553-8814"),
                    userId=Xsd_NCName("bsimpson"),
                    familyName="Simpson",
                    givenName="Bart",
                    credentials="AtomicPower",
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="bsimpson", ignore_cache=True)
        user.inProject = InProjectClass({Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
            AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES
        }})
        user.update()
        del user
        user = User.read(con=self._connection, userId="bsimpson", ignore_cache=True)
        self.assertEqual(user.inProject, InProjectClass({Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
            AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES
        }}))

    #  #unittest.skip('Work in progress')
    def test_update_user_rm_in_project(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0001-5925-2956"),
                    userId=Xsd_NCName("chiquet"),
                    familyName="Chiquet",
                    givenName="Vera",
                    credentials="Photography",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                        AdminPermission.ADMIN_USERS,
                        AdminPermission.ADMIN_RESOURCES,
                        AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        user.inProject = None
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        self.assertFalse(user.inProject)

    #  #unittest.skip('Work in progress')
    def test_update_user_del_in_project(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0001-5925-2956"),
                    userId=Xsd_NCName("chiquet"),
                    familyName="Chiquet",
                    givenName="Vera",
                    credentials="Photography",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                        AdminPermission.ADMIN_USERS,
                        AdminPermission.ADMIN_RESOURCES,
                        AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        del user.inProject
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        self.assertFalse(user.inProject)

    #  #unittest.skip('Work in progress')
    def test_update_user_add_to_project(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-2553-8814"),
                    userId=Xsd_NCName("bsimpson"),
                    familyName="Simpson",
                    givenName="Bart",
                    credentials="AtomicPower",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                        AdminPermission.ADMIN_USERS,
                        AdminPermission.ADMIN_RESOURCES,
                        AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="bsimpson", ignore_cache=True)
        user.inProject[Iri('oldap:HyperHamlet')] = {AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE}
        user.update()
        del user
        user = User.read(con=self._connection, userId="bsimpson", ignore_cache=True)
        self.assertEqual(user.inProject, InProjectClass(
            {
                Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                    AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE
                },
                Iri('oldap:HyperHamlet'): {
                    AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE
                }
            }
        ))

    #@unittest.skip('Work in progress')
    def test_update_user_rm_from_project(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-2553-8814"),
                    userId=Xsd_NCName("bsimpson"),
                    familyName="Simpson",
                    givenName="Bart",
                    credentials="AtomicPower",
                    inProject={
                        Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                            AdminPermission.ADMIN_USERS,
                            AdminPermission.ADMIN_RESOURCES,
                            AdminPermission.ADMIN_CREATE
                        },
                        Iri('oldap:HyperHamlet'): {
                            AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE
                        }
                    },
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        user = User.read(con=self._connection, userId="bsimpson", ignore_cache=True)
        user.inProject[Iri('oldap:HyperHamlet')] = None
        user.update()
        user = User.read(con=self._connection, userId="bsimpson", ignore_cache=True)
        self.assertEqual(user.inProject.get(Iri('oldap:HyperHamlet')), {})
        self.assertEqual(user.inProject[Iri('http://www.salsah.org/version/2.0/SwissBritNet')], {
                    AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE
            }
        )

    #  #unittest.skip('Work in progress')
    def test_update_user_del_from_project(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-2553-8814"),
                    userId=Xsd_NCName("bsimpson"),
                    familyName="Simpson",
                    givenName="Bart",
                    credentials="AtomicPower",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                        AdminPermission.ADMIN_USERS,
                        AdminPermission.ADMIN_RESOURCES,
                        AdminPermission.ADMIN_CREATE},
                        Iri('oldap:HyperHamlet'): {
                            AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE
                        }
                    },
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="bsimpson", ignore_cache=True)
        del user.inProject[Iri('oldap:HyperHamlet')]
        user.update()
        del user
        user = User.read(con=self._connection, userId="bsimpson", ignore_cache=True)
        self.assertEqual(user.inProject, InProjectClass(
            {
                Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                    AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE
                }
            }
        ))

    #  #unittest.skip('Work in progress')
    def test_update_user_del_has_permissions(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0001-5925-2956"),
                    userId=Xsd_NCName("chiquet"),
                    familyName="Chiquet",
                    givenName="Vera",
                    credentials="Photography",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                        AdminPermission.ADMIN_USERS,
                        AdminPermission.ADMIN_RESOURCES,
                        AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        del user.hasPermissions
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        self.assertFalse(user.hasPermissions)

    #  #unittest.skip('Work in progress')
    def test_update_user_add_has_permissions(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0001-5925-2956"),
                    userId=Xsd_NCName("chiquet"),
                    familyName="Chiquet",
                    givenName="Vera",
                    credentials="Photography",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                        AdminPermission.ADMIN_USERS,
                        AdminPermission.ADMIN_RESOURCES,
                        AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        user.hasPermissions.add(Iri('hyha:HyperHamletMember'))
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        self.assertEqual(user.hasPermissions, {Iri('oldap:GenericView'), Iri('hyha:HyperHamletMember')})

    #  #unittest.skip('Work in progress')
    def test_update_user_add_has_permissions(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0001-5925-2956"),
                    userId=Xsd_NCName("chiquet"),
                    familyName="Chiquet",
                    givenName="Vera",
                    credentials="Photography",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                        AdminPermission.ADMIN_USERS,
                        AdminPermission.ADMIN_RESOURCES,
                        AdminPermission.ADMIN_CREATE}})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        user.hasPermissions = {Iri('oldap:GenericView'), Iri('hyha:HyperHamletMember')}
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        self.assertEqual(user.hasPermissions, {Iri('oldap:GenericView'), Iri('hyha:HyperHamletMember')})

    #  #unittest.skip('Work in progress')
    def test_update_user_add_bad_has_permissions(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0001-5925-2956"),
                    userId=Xsd_NCName("chiquet"),
                    familyName="Chiquet",
                    givenName="Vera",
                    credentials="Photography",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                        AdminPermission.ADMIN_USERS,
                        AdminPermission.ADMIN_RESOURCES,
                        AdminPermission.ADMIN_CREATE}})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        user.hasPermissions = {Iri('oldap:GAGA'), Iri('hyha:HyperHamletMember')}
        with self.assertRaises(OldapErrorValue) as err:
            user.update()

    #  #unittest.skip('Work in progress')
    def test_update_user_rm_has_permissions(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0001-5925-2956"),
                    userId=Xsd_NCName("chiquet"),
                    familyName="Chiquet",
                    givenName="Vera",
                    credentials="Photography",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                        AdminPermission.ADMIN_USERS,
                        AdminPermission.ADMIN_RESOURCES,
                        AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView'), Iri('hyha:HyperHamletMember')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        user.hasPermissions.discard(Iri('hyha:HyperHamletMember'))
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        self.assertEqual(user.hasPermissions, {Iri('oldap:GenericView')})

    #  unittest.skip('Work in progress')
    def test_update_user_unexisting_has_permissions(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0001-5925-2956"),
                    userId=Xsd_NCName("chiquet"),
                    familyName="Chiquet",
                    givenName="Vera",
                    credentials="Photography",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                        AdminPermission.ADMIN_USERS,
                        AdminPermission.ADMIN_RESOURCES,
                        AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView'), Iri('hyha:HyperHamletMember')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        user.hasPermissions.discard(Iri('oldap:GenericRestricted'))
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet", ignore_cache=True)
        self.assertEqual(user.hasPermissions, {Iri('oldap:GenericView'), Iri('hyha:HyperHamletMember')})

    def test_user_update_active(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0003-4545-3559"),
                    userId=Xsd_NCName("jrosenthal"),
                    familyName="Rosenthal",
                    givenName="Joachim",
                    credentials="CryptoGraphy0*0@",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                        AdminPermission.ADMIN_USERS,
                        AdminPermission.ADMIN_RESOURCES,
                        AdminPermission.ADMIN_CREATE}},
                    isActive=False,
                    hasPermissions={Iri('oldap:GenericView'), Iri('hyha:HyperHamletMember')})
        user.create()
        self.assertFalse(user.isActive)
        del user
        user = User.read(con=self._connection, userId="jrosenthal", ignore_cache=True)
        self.assertFalse(user.isActive)
        user.isActive = True
        self.assertIsInstance(user.isActive, Xsd_boolean)
        user.update()
        del user
        user = User.read(con=self._connection, userId="jrosenthal", ignore_cache=True)
        self.assertTrue(user.isActive)
        self.assertIsInstance(user.isActive, Xsd_boolean)

        user.isActive = False
        self.assertIsInstance(user.isActive, Xsd_boolean)
        user.update()
        del user
        user = User.read(con=self._connection, userId="jrosenthal", ignore_cache=True)
        self.assertFalse(user.isActive)
        self.assertIsInstance(user.isActive, Xsd_boolean)

    def test_user_password_change(self):
        user = User(con=self._connection,
                    userId=Xsd_NCName("speedy"),
                    familyName="Gonzales",
                    givenName="Speedy",
                    credentials="FastestMouseInMexico",
                    isActive=True)
        user.create()
        mycon = Connection(server='http://localhost:7200',
                           repo="oldap",
                           userId="speedy",
                           credentials="FastestMouseInMexico",
                           context_name="DEFAULT")
        user = User.read(con=mycon, userId="speedy", ignore_cache=True)
        user.credentials = "ElRatónMásRápidoDeMéxico"
        user.update()
        with self.assertRaises(OldapError) as err:
            mycon = Connection(server='http://localhost:7200',
                               repo="oldap",
                               userId="speedy",
                               credentials="FastestMouseInMexico",
                               context_name="DEFAULT")
        mycon = Connection(server='http://localhost:7200',
                           repo="oldap",
                           userId="speedy",
                           credentials="ElRatónMásRápidoDeMéxico",
                           context_name="DEFAULT")
        user = User.read(con=mycon, userId="speedy", ignore_cache=True)
        user.isActive = False
        with self.assertRaises(OldapErrorNoPermission) as err:
            user.update()

    def test_user_authorizations(self):
        user = User(con=self._unpriv,
                    userIri=Iri("https://orcid.org/0000-0001-9421-3434"),
                    userId=Xsd_NCName("niederer"),
                    familyName="Niedererer",
                    givenName="Markus",
                    credentials="DendroChronologie",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                        AdminPermission.ADMIN_USERS,
                        AdminPermission.ADMIN_RESOURCES,
                        AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView'), Iri('hyha:HyperHamletMember')})
        with self.assertRaises(OldapErrorNoPermission) as ex:
            user.create()

        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0001-9421-3434"),
                    userId=Xsd_NCName("niederer"),
                    familyName="Niedererer",
                    givenName="Markus",
                    credentials="DendroChronologie",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                        AdminPermission.ADMIN_USERS,
                        AdminPermission.ADMIN_RESOURCES,
                        AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('oldap:GenericView'), Iri('hyha:HyperHamletMember')})
        user.create()
        user = User.read(con=self._unpriv, userId="niederer", ignore_cache=True)
        user.familyName = "Niederer"
        user.inProject[Iri('http://www.salsah.org/version')] = {AdminPermission.ADMIN_CREATE}
        with self.assertRaises(OldapErrorNoPermission) as ex:
            user.update()
        with self.assertRaises(OldapErrorNoPermission) as ex:
            user.delete()


if __name__ == '__main__':
    unittest.main()
