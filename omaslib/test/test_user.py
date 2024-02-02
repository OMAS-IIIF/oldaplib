import unittest
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName, NCName, AnyIRI
from omaslib.src.helpers.omaserror import OmasErrorNotFound, OmasErrorAlreadyExists, OmasValueError
from omaslib.src.helpers.permissions import AdminPermission
from omaslib.src.user import User
from omaslib.src.in_project import InProjectType


class TestUser(unittest.TestCase):
    _context: Context
    _connection: Connection

    @classmethod
    def setUp(cls):

        cls._context = Context(name="DEFAULT")

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        user = User(con=cls._connection, userId=NCName("coyote"))
        user.delete()
        #cls._connection.clear_graph(QName('omas:admin'), login_required=False)
        #cls._connection.upload_turtle("omaslib/ontologies/ontologies/admin.trig", login_required=False)
        #sleep(1)  # upload may take a while...


    def tearDown(self):
        pass

    def test_constructor(self):
        user = User(con=self._connection,
                     userId=NCName("testuser"),
                     family_name="Test",
                     given_name="Test",
                     credentials="Ein@geheimes&Passw0rt",
                     inProject={QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                             AdminPermission.ADMIN_RESOURCES,
                                                             AdminPermission.ADMIN_CREATE}},
                     hasPermissions={QName('omas:GenericView')})

        self.assertEqual(user.userId, NCName("testuser"))
        self.assertEqual(user.familyName, "Test")
        self.assertEqual(user.givenName, "Test")
        self.assertEqual(user.inProject, InProjectType({QName("omas:HyperHamlet"): {
                AdminPermission.ADMIN_USERS,
                AdminPermission.ADMIN_RESOURCES,
                AdminPermission.ADMIN_CREATE
        }}))
        self.assertEqual(user.hasPermissions, {QName('omas:GenericView')})

    #@unittest.skip('Work in progress')
    def test_read_user(self):
        user = User.read(con=self._connection, userId="rosenth")
        self.assertEqual(user.userId, NCName("rosenth"))
        self.assertEqual(user.userIri, "https://orcid.org/0000-0003-1681-4036")
        self.assertEqual(user.familyName, "Rosenthaler")
        self.assertEqual(user.givenName, "Lukas")
        self.assertEqual(user.inProject, InProjectType({
                QName("omas:SystemProject"): {AdminPermission.ADMIN_OLDAP},
                QName('omas:HyperHamlet'): {AdminPermission.ADMIN_RESOURCES}
        }))
        self.assertEqual(user.hasPermissions, {QName("omas:GenericRestricted"), QName('omas:GenericView')})

    #@unittest.skip('Work in progress')
    def test_read_unknown_user(self):
        with self.assertRaises(OmasErrorNotFound) as ex:
            user = User.read(con=self._connection, userId="nosuchuser")
        self.assertEqual(str(ex.exception), 'User "nosuchuser" not found.')

    #@unittest.skip('Work in progress')
    def test_create_user(self):
        user = User(con=self._connection,
                    userIri=AnyIRI("https://orcid.org/0000-0003-3478-9313"),
                    userId=NCName("coyote"),
                    family_name="Coyote",
                    given_name="Wiley E.",
                    credentials="Super-Genius",
                    inProject=InProjectType({QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                                         AdminPermission.ADMIN_RESOURCES,
                                                                         AdminPermission.ADMIN_CREATE}}),
                    hasPermissions={QName('omas:GenericView')})
        user.create()
        user2 = User.read(con=self._connection, userId="coyote")
        self.assertEqual(user2.userId, user.userId)
        self.assertEqual(user2.userIri, user.userIri)
        self.assertEqual(user2.familyName, user.familyName)
        self.assertEqual(user2.givenName, user.givenName)
        self.assertEqual(user2.inProject, user.inProject)
        self.assertEqual(user2.hasPermissions, user.hasPermissions)

        with self.assertRaises(OmasErrorAlreadyExists) as ex:
            user.create()
        self.assertEqual(str(ex.exception), 'A user with a user ID "coyote" already exists')

        user3 = User(con=self._connection,
                     userIri=AnyIRI("https://orcid.org/0000-0003-3478-9313"),
                     userId=NCName("brown"),
                     family_name="Brown",
                     given_name="Emmett",
                     credentials="Time-Machine@1985",
                     inProject=InProjectType({QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                                          AdminPermission.ADMIN_RESOURCES,
                                                                          AdminPermission.ADMIN_CREATE}}),
                     hasPermissions={QName('omas:GenericView')})
        with self.assertRaises(OmasErrorAlreadyExists) as ex:
            user3.create()
        self.assertEqual(str(ex.exception), 'A user with a user IRI "https://orcid.org/0000-0003-3478-9313" already exists')
        user4 = User(con=self._connection,
                     userId=NCName("brown"),
                     family_name="Dock",
                     given_name="Donald",
                     credentials="Entenhausen@for&Ever",
                     inProject=InProjectType({QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                                          AdminPermission.ADMIN_RESOURCES,
                                                                          AdminPermission.ADMIN_CREATE}}),
                     hasPermissions={QName('omas:GenericView'), QName('omas:Gaga')})
        with self.assertRaises(OmasValueError) as ex:
            user4.create()

    #@unittest.skip('Work in progress')
    def test_delete_user(self):
        user = User(con=self._connection,
                    userIri=AnyIRI("https://orcid.org/0000-0002-9991-2055"),
                    userId=NCName("edison"),
                    family_name="Edison",
                    given_name="Thomas A.",
                    credentials="Lightbulb&Phonograph",
                    inProject=InProjectType({QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                                         AdminPermission.ADMIN_RESOURCES,
                                                                         AdminPermission.ADMIN_CREATE}}),
                    hasPermissions={QName('omas:GenericView')})
        user.create()
        user2 = User.read(con=self._connection, userId="edison")
        self.assertEqual(user2.userIri, user.userIri)
        user2.delete()
        with self.assertRaises(OmasErrorNotFound) as ex:
            user = User.read(con=self._connection, userId="edison")
        self.assertEqual(str(ex.exception), 'User "edison" not found.')

    #@unittest.skip('Work in progress')
    def test_update_user(self):
        user = User(con=self._connection,
                    userIri=AnyIRI("https://orcid.org/0000-0002-9991-2055"),
                    userId=NCName("edison"),
                    family_name="Edison",
                    given_name="Thomas A.",
                    credentials="Lightbulb&Phonograph",
                    inProject=InProjectType({QName('omas:HyperHamlet'): {AdminPermission.ADMIN_USERS,
                                                                         AdminPermission.ADMIN_RESOURCES,
                                                                         AdminPermission.ADMIN_CREATE}}),
                    hasPermissions={QName('omas:GenericView')})
        user.create()
        user2 = User.read(con=self._connection, userId="edison")
        user2.userId = "aedison"
        user2.familyName = "Edison et al."
        user2.givenName = "Thomas"
        user2.hasPermissions.add(QName('omas:GenericRestricted'))
        user2.hasPermissions.add(QName('omas:HyperHamletMember'))
        user2.hasPermissions.remove(QName('omas:GenericView'))
        user2.inProject[QName('omas:SystemProject')] = {AdminPermission.ADMIN_USERS, AdminPermission.ADMIN_RESOURCES}
        user2.inProject[QName('omas:HyperHamlet')].remove(AdminPermission.ADMIN_USERS)
        user2.update()
        user3 = User.read(con=self._connection, userId="aedison")
        self.assertEqual({'omas:GenericRestricted', 'omas:HyperHamletMember'}, user3.hasPermissions)
        user3.hasPermissions.add(QName('omas:DoesNotExist'))
        with self.assertRaises(OmasValueError) as ex:
            user3.update()
            self.assertEqual(str(ex.exception), 'One of the permission sets is not existing!')
        self.assertEqual(InProjectType({QName('omas:HyperHamlet'): {AdminPermission.ADMIN_RESOURCES,
                                                                    AdminPermission.ADMIN_CREATE},
                                        QName('omas:SystemProject'): {AdminPermission.ADMIN_USERS,
                                                                      AdminPermission.ADMIN_RESOURCES}}), user3.inProject)
        user3.delete()


if __name__ == '__main__':
    unittest.main()
