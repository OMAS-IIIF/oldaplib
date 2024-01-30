import unittest
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName, NCName
from omaslib.src.helpers.omaserror import OmasErrorNotFound, OmasErrorAlreadyExists
from omaslib.src.helpers.permissions import AdminPermission
from omaslib.src.user import User


class TestUser(unittest.TestCase):
    _context: Context
    _connection: Connection

    @classmethod
    def setUp(cls):
        cls._context = Context(name="DEFAULT")

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     user_id="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        user = User(con=cls._connection, user_id=NCName("coyote"))
        user.delete()
        #cls._connection.clear_graph(QName('omas:admin'))
        #cls._connection.upload_turtle("omaslib/ontologies/ontologies/admin.trig")
        #sleep(1)  # upload may take a while...

    def tearDown(self):
        pass

    def test_constructor(self):
        user = User(con=self._connection,
                     user_id=NCName("testuser"),
                     family_name="Test",
                     given_name="Test",
                     credentials="Ein@geheimes&Passw0rt",
                     in_project={QName('omas:HyperHamlet'): [AdminPermission.ADMIN_USERS,
                                                             AdminPermission.ADMIN_RESOURCES,
                                                             AdminPermission.ADMIN_CREATE]},
                     has_permissions=[QName('omas:GenericView')])

        self.assertEqual(user.user_id, NCName("testuser"))
        self.assertEqual(user.familyName, "Test")
        self.assertEqual(user.givenName, "Test")
        self.assertEqual(user.credentials, "Ein@geheimes&Passw0rt")
        self.assertEqual(user.in_project, {QName("omas:HyperHamlet"): [
                AdminPermission.ADMIN_USERS,
                AdminPermission.ADMIN_RESOURCES,
                AdminPermission.ADMIN_CREATE
        ]})
        self.assertEqual(user.has_permissions, [QName('omas:GenericView')])

    def test_read_user(self):
        user = User.read(con=self._connection, user_id="rosenth")
        self.assertEqual(user.user_id, NCName("rosenth"))
        self.assertEqual(user.user_iri, "https://orcid.org/0000-0003-1681-4036")
        self.assertEqual(user.familyName, "Rosenthaler")
        self.assertEqual(user.givenName, "Lukas")
        self.assertEqual(user.in_project, {
                QName("omas:SystemProject"): [AdminPermission.ADMIN_OLDAP],
                QName('omas:HyperHamlet'): [AdminPermission.ADMIN_RESOURCES]
        })
        self.assertEqual(user.has_permissions, [QName("omas:GenericRestricted"), QName('omas:GenericView')])

    def test_read_unknown_user(self):
        with self.assertRaises(OmasErrorNotFound) as ex:
            user = User.read(con=self._connection, user_id="nosuchuser")
        self.assertEqual(str(ex.exception), 'User "nosuchuser" not found.')

    def test_create_user(self):
        user = User(con=self._connection,
                    user_iri="https://orcid.org/0000-0003-3478-9313",
                    user_id=NCName("coyote"),
                    family_name="Coyote",
                    given_name="Wiley E.",
                    credentials="Super-Genius",
                    in_project={QName('omas:HyperHamlet'): [AdminPermission.ADMIN_USERS,
                                                            AdminPermission.ADMIN_RESOURCES,
                                                            AdminPermission.ADMIN_CREATE]},
                    has_permissions=[QName('omas:GenericView')])
        user.create()
        user2 = User.read(con=self._connection, user_id="coyote")
        self.assertEqual(user2.user_id, user.user_id)
        self.assertEqual(user2.user_iri, user.user_iri)
        self.assertEqual(user2.familyName, user.familyName)
        self.assertEqual(user2.givenName, user.givenName)
        self.assertEqual(user2.in_project, user.in_project)
        self.assertEqual(user2.has_permissions, user.has_permissions)

        with self.assertRaises(OmasErrorAlreadyExists) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'A user with a user ID "coyote" already exists')

        user3 = User(con=self._connection,
                     user_iri="https://orcid.org/0000-0003-3478-9313",
                     user_id=NCName("brown"),
                     family_name="Brown",
                     given_name="Emmett",
                     credentials="Time-Machine@1985",
                     in_project={QName('omas:HyperHamlet'): [AdminPermission.ADMIN_USERS,
                                                             AdminPermission.ADMIN_RESOURCES,
                                                             AdminPermission.ADMIN_CREATE]},
                     has_permissions=[QName('omas:GenericView')])
        with self.assertRaises(OmasErrorAlreadyExists) as ex:
            user3.create()
        self.assertEqual(str(ex.exception), 'A user with a user IRI "https://orcid.org/0000-0003-3478-9313" already exists')


    def test_delete_user(self):
        user = User(con=self._connection,
                    user_iri="https://orcid.org/0000-0002-9991-2055",
                    user_id=NCName("edison"),
                    family_name="Edison",
                    given_name="Thomas A.",
                    credentials="Lightbulb&Phonograph",
                    in_project={QName('omas:HyperHamlet'): [AdminPermission.ADMIN_USERS,
                                                            AdminPermission.ADMIN_RESOURCES,
                                                            AdminPermission.ADMIN_CREATE]},
                    has_permissions=[QName('omas:GenericView')])
        user.create()
        user2 = User.read(con=self._connection, user_id="edison")
        self.assertEqual(user2.user_iri, user.user_iri)
        user2.delete()
        with self.assertRaises(OmasErrorNotFound) as ex:
            user = User.read(con=self._connection, user_id="edison")
        self.assertEqual(str(ex.exception), 'User "edison" not found.')

if __name__ == '__main__':
    unittest.main()
