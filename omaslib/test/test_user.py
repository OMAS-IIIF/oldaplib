import unittest
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.tools import str2qname_anyiri
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.helpers.omaserror import OmasErrorNotFound, OmasErrorAlreadyExists, OmasErrorValue, OmasErrorNoPermission, OmasError
from omaslib.src.enums.permissions import AdminPermission
from omaslib.src.user import User
from omaslib.src.in_project import InProjectClass
from omaslib.src.xsd.xsd_string import Xsd_string


class TestUser(unittest.TestCase):
    _context: Context
    _connection: Connection
    _unpriv: Connection

    @classmethod
    def setUp(cls):
        cls._context = Context(name="DEFAULT")

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._unpriv = Connection(server='http://localhost:7200',
                                 repo="omas",
                                 userId="fornaro",
                                 credentials="RioGrande",
                                 context_name="DEFAULT")

        # user = User(con=cls._connection, userId=NCName("coyote"))
        # user.delete()
        cls._connection.clear_graph(Xsd_QName('omas:admin'))
        cls._connection.upload_turtle("omaslib/ontologies/admin.trig")
        sleep(1)  # upload may take a while...

    def tearDown(self):
        pass

    #  @unittest.skip('Work in progress')
    def test_constructor(self):
        user = User(con=self._connection,
                    userId=Xsd_NCName("testuser"),
                    familyName="Test",
                    givenName="Test",
                    credentials="Ein@geheimes&Passw0rt",
                    inProject={Iri('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Xsd_QName('omas:GenericView')})

        self.assertEqual(user.userId, Xsd_NCName("testuser"))
        self.assertEqual(user.familyName, "Test")
        self.assertEqual(user.givenName, "Test")
        self.assertEqual(user.inProject, InProjectClass({Iri("omas:HyperHamlet"): {
            AdminPermission.ADMIN_USERS,
            AdminPermission.ADMIN_RESOURCES,
            AdminPermission.ADMIN_CREATE
        }}))
        self.assertEqual(user.hasPermissions, {Xsd_QName('omas:GenericView')})

    # @unittest.skip('Work in progress')
    def test_read_user(self):
        user = User.read(con=self._connection, userId="rosenth")
        self.assertEqual(user.userId, Xsd_NCName("rosenth"))
        self.assertEqual(user.userIri, Iri("https://orcid.org/0000-0003-1681-4036"))
        self.assertEqual(user.familyName, Xsd_string("Rosenthaler"))
        self.assertEqual(user.givenName, Xsd_string("Lukas"))
        self.assertEqual(user.inProject, InProjectClass({
            Iri("omas:SystemProject"): {AdminPermission.ADMIN_OLDAP},
            Iri('omas:HyperHamlet'): {AdminPermission.ADMIN_RESOURCES}
        }))
        self.assertEqual(user.hasPermissions, {Iri("omas:GenericRestricted"), Iri('omas:GenericView')})

    #  #unittest.skip('Work in progress')
    def test_read_unknown_user(self):
        with self.assertRaises(OmasErrorNotFound) as ex:
            user = User.read(con=self._connection, userId="nosuchuser")
        self.assertEqual(str(ex.exception), 'User "nosuchuser" not found.')

    #  #unittest.skip('Work in progress')
    def test_search_user(self):
        users = User.search(con=self._connection, userId="fornaro")
        self.assertEqual([Iri("https://orcid.org/0000-0003-1485-4923")], users)

        users = User.search(con=self._connection, familyName="Rosenthaler")
        self.assertEqual([Iri("https://orcid.org/0000-0003-1681-4036")], users)

        users = User.search(con=self._connection, givenName="John")
        self.assertEqual([Iri("urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b")], users)

        users = User.search(con=self._connection, inProject=Xsd_QName("omas:HyperHamlet"))
        self.assertEqual([Iri("https://orcid.org/0000-0003-1681-4036"),
                          Iri("https://orcid.org/0000-0003-1485-4923"),
                          Iri("https://orcid.org/0000-0001-9277-3921")], users)

        users = User.search(con=self._connection, inProject=Xsd_anyURI("http://www.salsah.org/version/2.0/SwissBritNet"))
        self.assertEqual([Iri("urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b")], users)

        users = User.search(con=self._connection, userId="GAGA")
        self.assertEqual([], users)

    #  #unittest.skip('Work in progress')
    def test_search_user_injection(self):
        with self.assertRaises(OmasErrorValue) as ex:
            users = User.search(con=self._connection, userId="fornaro\".}\nSELECT * WHERE {?s ?p ?s})#")
        self.assertEqual(str(ex.exception), 'Invalid string "fornaro".}\nSELECT * WHERE {?s ?p ?s})#" for NCName')

        users = User.search(con=self._connection, familyName="Rosenthaler\".}\nSELECT * WHERE{?s ?p ?s})#")
        self.assertEqual(len(users), 0)
        users = User.search(con=self._connection, givenName="John\".}\nSELECT * WHERE{?s ?p ?s})#")
        self.assertEqual(len(users), 0)

        with self.assertRaises(OmasErrorValue) as ex:
            users = User.search(con=self._connection, inProject="omas:HyperHamlet\".}\nSELECT * WHERE{?s ?p ?s})#")
        self.assertEqual(str(ex.exception), 'Invalid string for IRI: "omas:HyperHamlet".}\nSELECT * WHERE{?s ?p ?s})#"')

    #  #unittest.skip('Work in progress')
    def test_create_user(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0003-3478-9313"),
                    userId=Xsd_NCName("coyote"),
                    familyName="Coyote",
                    givenName="Wiley E.",
                    credentials="Super-Genius",
                    inProject={Iri('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                               AdminPermission.ADMIN_RESOURCES,
                                                               AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('omas:GenericView')},
                    isActive=True)
        user.create()
        user2 = User.read(con=self._connection, userId="coyote")
        self.assertEqual(user2.userId, user.userId)
        self.assertEqual(user2.userIri, user.userIri)
        self.assertEqual(user2.familyName, user.familyName)
        self.assertEqual(user2.givenName, user.givenName)
        self.assertEqual(user2.inProject, user.inProject)
        self.assertEqual(user2.hasPermissions, user.hasPermissions)
        self.assertTrue(user2.isActive)

    #  #unittest.skip('Work in progress')
    def test_create_user_no_admin_perms(self):
        user = User(con=self._connection,
                    userId=Xsd_NCName("birdy"),
                    familyName="Birdy",
                    givenName="Tweetie",
                    credentials="Sylvester",
                    inProject={Iri('omas:HyperHamlet'): set()},
                    hasPermissions={Iri('omas:GenericView')},
                    isActive=True)
        user.create()
        del user
        user = User.read(con=self._connection, userId=Xsd_NCName("birdy"))
        self.assertEqual(user.familyName, "Birdy")

    #  #unittest.skip('Work in progress')
    def test_create_user_no_in_project(self):
        user = User(con=self._connection,
                    userId=Xsd_NCName("yogi"),
                    familyName="Baer",
                    givenName="Yogi",
                    credentials="BuBu",
                    hasPermissions={Iri('omas:GenericView')},
                    isActive=True)
        user.create()
        del user
        user = User.read(con=self._connection, userId=Xsd_NCName("yogi"))
        self.assertEqual(user.familyName, "Baer")

    #  #unittest.skip('Work in progress')
    def test_create_user_no_permset(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0003-3478-9313"),
                    userId=Xsd_NCName("speedy"),
                    familyName="Ganzales",
                    givenName="Speedy",
                    credentials="fasterthanlight",
                    inProject={Iri('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                               AdminPermission.ADMIN_RESOURCES,
                                                               AdminPermission.ADMIN_CREATE}},
                    isActive=True)
        user.create()
        del user
        user = User.read(con=self._connection, userId=Xsd_NCName("speedy"))
        self.assertEqual(user.familyName, "Ganzales")


    #  #unittest.skip('Work in progress')
    def test_create_user_no_useriri(self):
        user = User(con=self._connection,
                    userId=Xsd_NCName("sylvester"),
                    familyName="Sylvester",
                    givenName="Cat",
                    credentials="Birdy",
                    inProject={Iri('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                               AdminPermission.ADMIN_RESOURCES,
                                                               AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('omas:GenericView')},
                    isActive=False)
        user.create()
        del user
        user = User.read(con=self._connection, userId=Xsd_NCName("sylvester"))
        self.assertTrue(str(user.userIri).startswith("urn:uuid:"))
        self.assertFalse(user.isActive)

    #  #unittest.skip('Work in progress')
    def test_create_user_duplicate_userid(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0003-3478-9314"),
                    userId=Xsd_NCName("fornaro"),
                    familyName="di Fornaro",
                    givenName="Petri",
                    credentials="Genius",
                    inProject={Iri('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                               AdminPermission.ADMIN_RESOURCES,
                                                               AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('omas:GenericView')})
        with self.assertRaises(OmasErrorAlreadyExists) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'A user with a user ID "fornaro" already exists')

    #  #unittest.skip('Work in progress')
    def test_create_user_duplicate_useriri(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0003-1681-4036"),
                    userId=Xsd_NCName("brown"),
                    familyName="Brown",
                    givenName="Emmett",
                    credentials="Time-Machine@1985",
                    inProject={Iri('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                               AdminPermission.ADMIN_RESOURCES,
                                                               AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('omas:GenericView')})
        with self.assertRaises(OmasErrorAlreadyExists) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'A user with a user IRI "https://orcid.org/0000-0003-1681-4036" already exists')

    #  #unittest.skip('Work in progress')
    def test_create_user_invalid_project(self):
        user = User(con=self._connection,
                    userId=Xsd_NCName("donald"),
                    familyName="Duck",
                    givenName="Donald",
                    credentials="Entenhausen@for&Ever",
                    inProject={Iri('omas:NotExistingproject'): {AdminPermission.ADMIN_USERS,
                                                                      AdminPermission.ADMIN_RESOURCES,
                                                                      AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('omas:GenericView')})
        with self.assertRaises(OmasErrorValue) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'One of the projects is not existing!')

    #  #unittest.skip('Work in progress')
    def test_create_user_invalid_permset(self):
        user = User(con=self._connection,
                    userId=Xsd_NCName("donald"),
                    familyName="Duck",
                    givenName="Donald",
                    credentials="Entenhausen@for&Ever",
                    inProject={Iri('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                               AdminPermission.ADMIN_RESOURCES,
                                                               AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('omas:GenericView'), Xsd_QName('omas:Gaga')})
        with self.assertRaises(OmasErrorValue) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'One of the permission sets is not existing!')

    #  #unittest.skip('Work in progress')
    def test_create_user_no_privilege(self):
        user = User(con=self._unpriv,
                    userId=Xsd_NCName("donald"),
                    familyName="Duck",
                    givenName="Donald",
                    credentials="Entenhausen@for&Ever",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('omas:GenericView')})
        with self.assertRaises(OmasErrorNoPermission) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'No permission to create user in project http://www.salsah.org/version/2.0/SwissBritNet.')

    #  #unittest.skip('Work in progress')
    def test_create_user_no_connection(self):
        user = User(userId=Xsd_NCName("brown"),
                    familyName="Dock",
                    givenName="Donald",
                    credentials="Entenhausen@for&Ever",
                    inProject={Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('omas:GenericView')})
        with self.assertRaises(OmasError) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'Cannot create: no connection')

    #  #unittest.skip('Work in progress')
    def test_delete_user(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2055"),
                    userId=Xsd_NCName("edison"),
                    familyName="Edison",
                    givenName="Thomas A.",
                    credentials="Lightbulb&Phonograph",
                    inProject={Iri('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                               AdminPermission.ADMIN_RESOURCES,
                                                               AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('omas:GenericView')})
        user.create()
        user2 = User.read(con=self._connection, userId="edison")
        self.assertEqual(user2.userIri, user.userIri)
        user2.delete()
        with self.assertRaises(OmasErrorNotFound) as ex:
            user = User.read(con=self._connection, userId="edison")
        self.assertEqual(str(ex.exception), 'User "edison" not found.')

    #  #unittest.skip('Work in progress')
    def test_delete_user_unpriv(self):
        user = User.read(con=self._unpriv, userId="bugsbunny")
        with self.assertRaises(OmasErrorNoPermission) as ex:
            user.delete()
        self.assertEqual(str(ex.exception), 'No permission to delete user in project omas:HyperHamlet.')

    #  #unittest.skip('Work in progress')
    def test_update_user(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-9991-2055"),
                    userId=Xsd_NCName("edison"),
                    familyName="Edison",
                    givenName="Thomas A.",
                    credentials="Lightbulb&Phonograph",
                    inProject={Iri('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                               AdminPermission.ADMIN_RESOURCES,
                                                               AdminPermission.ADMIN_CREATE}},
                    hasPermissions={Iri('omas:GenericView')})
        user.create()
        user2 = User.read(con=self._connection, userId="edison")
        user2.userId = "aedison"
        user2.familyName = "Edison et al."
        user2.givenName = "Thomas"
        user2.hasPermissions.add(Iri('omas:GenericRestricted'))
        user2.hasPermissions.add(Iri('omas:HyperHamletMember'))
        user2.hasPermissions.remove(Iri('omas:GenericView'))
        user2.inProject[Iri('omas:SystemProject')] = {AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES}
        user2.inProject[Iri('omas:HyperHamlet')].remove(AdminPermission.ADMIN_USERS)
        user2.update()
        user3 = User.read(con=self._connection, userId="aedison")
        self.assertEqual({Iri('omas:GenericRestricted'), Iri('omas:HyperHamletMember')}, user3.hasPermissions)
        user3.hasPermissions.add(Iri('omas:DoesNotExist'))
        with self.assertRaises(OmasErrorValue) as ex:
            user3.update()
            self.assertEqual(str(ex.exception), 'One of the permission sets is not existing!')
        self.assertEqual(InProjectClass({Iri('omas:HyperHamlet'): {AdminPermission.ADMIN_RESOURCES,
                                                                         AdminPermission.ADMIN_CREATE},
                                         Iri('omas:SystemProject'): {AdminPermission.ADMIN_USERS,
                                                                           AdminPermission.ADMIN_RESOURCES}}), user3.inProject)
        del user3
        user4 = User.read(con=self._connection, userId="aedison")
        user4.inProject = InProjectClass({Iri('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS}})
        user4.update()
        del user4

    #  #unittest.skip('Work in progress')
    def test_update_user_unpriv(self):
        user = User.read(con=self._unpriv, userId="bugsbunny")
        user.credentials = "ChangedPassword"
        with self.assertRaises(OmasErrorNoPermission) as ex:
            user.update()
        self.assertEqual(str(ex.exception), 'No permission to modify user in project omas:HyperHamlet.')

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
                    hasPermissions={Iri('omas:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet")
        user.inProject = InProjectClass({Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {AdminPermission.ADMIN_OLDAP}})
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet")
        self.assertEqual(user.inProject, InProjectClass({Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {AdminPermission.ADMIN_OLDAP}}))

    #  #unittest.skip('Work in progress')
    def test_update_user_empty_in_project(self):
        user = User(con=self._connection,
                    userIri=Iri("https://orcid.org/0000-0002-2553-8814"),
                    userId=Xsd_NCName("bsimpson"),
                    familyName="Simpson",
                    givenName="Bart",
                    credentials="AtomicPower",
                    hasPermissions={Iri('omas:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="bsimpson")
        user.inProject = InProjectClass({Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
            AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES
        }})
        user.update()
        del user
        user = User.read(con=self._connection, userId="bsimpson")
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
                    hasPermissions={Iri('omas:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet")
        user.inProject = None
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet")
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
                    hasPermissions={Iri('omas:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet")
        del user.inProject
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet")
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
                    hasPermissions={Iri('omas:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="bsimpson")
        user.inProject[Iri('omas:HyperHamlet')] = {AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE}
        user.update()
        del user
        user = User.read(con=self._connection, userId="bsimpson")
        self.assertEqual(user.inProject, InProjectClass(
            {
                Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                    AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE
                },
                Iri('omas:HyperHamlet'): {
                    AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE
                }
            }
        ))

    #  #unittest.skip('Work in progress')
    def test_update_user_rm_from_project(self):
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
                        Iri('omas:HyperHamlet'): {
                            AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE
                        }
                    },
                    hasPermissions={Iri('omas:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="bsimpson")
        user.inProject[Iri('omas:HyperHamlet')] = None
        user.update()
        del user
        user = User.read(con=self._connection, userId="bsimpson")
        self.assertEqual(user.inProject, InProjectClass(
            {
                Iri('http://www.salsah.org/version/2.0/SwissBritNet'): {
                    AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE
                }
            }
        ))

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
                        Iri('omas:HyperHamlet'): {
                            AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_CREATE
                        }
                    },
                    hasPermissions={Iri('omas:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="bsimpson")
        del user.inProject[Iri('omas:HyperHamlet')]
        user.update()
        del user
        user = User.read(con=self._connection, userId="bsimpson")
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
                    hasPermissions={Iri('omas:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet")
        del user.hasPermissions
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet")
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
                    hasPermissions={Iri('omas:GenericView')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet")
        user.hasPermissions.add(Iri('omas:HyperHamletMember'))
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet")
        self.assertEqual(user.hasPermissions, {Iri('omas:GenericView'), Iri('omas:HyperHamletMember')})

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
        user = User.read(con=self._connection, userId="chiquet")
        user.hasPermissions = {Iri('omas:GenericView'), Iri('omas:HyperHamletMember')}
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet")
        self.assertEqual(user.hasPermissions, {Iri('omas:GenericView'), Iri('omas:HyperHamletMember')})

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
        user = User.read(con=self._connection, userId="chiquet")
        user.hasPermissions = {Iri('omas:GAGA'), Iri('omas:HyperHamletMember')}
        with self.assertRaises(OmasErrorValue) as err:
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
                    hasPermissions={Iri('omas:GenericView'), Iri('omas:HyperHamletMember')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet")
        user.hasPermissions.discard(Iri('omas:HyperHamletMember'))
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet")
        self.assertEqual(user.hasPermissions, {Iri('omas:GenericView')})

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
                    hasPermissions={Iri('omas:GenericView'), Iri('omas:HyperHamletMember')})
        user.create()
        del user
        user = User.read(con=self._connection, userId="chiquet")
        user.hasPermissions.discard(Iri('omas:GenericRestricted'))
        user.update()
        del user
        user = User.read(con=self._connection, userId="chiquet")
        self.assertEqual(user.hasPermissions, {Iri('omas:GenericView'), Iri('omas:HyperHamletMember')})

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
                    hasPermissions={Iri('omas:GenericView'), Iri('omas:HyperHamletMember')})
        with self.assertRaises(OmasErrorNoPermission) as ex:
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
                    hasPermissions={Iri('omas:GenericView'), Iri('omas:HyperHamletMember')})
        user.create()
        user = User.read(con=self._unpriv, userId="niederer")
        user.familyName = "Niederer"
        user.inProject[Iri('http://www.salsah.org/version')] = {AdminPermission.ADMIN_CREATE}
        with self.assertRaises(OmasErrorNoPermission) as ex:
            user.update()
        with self.assertRaises(OmasErrorNoPermission) as ex:
            user.delete()


if __name__ == '__main__':
    unittest.main()
