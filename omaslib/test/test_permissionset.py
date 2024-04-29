import unittest
from time import sleep

from omaslib.enums.permissionsetattr import PermissionSetAttr
from omaslib.src.PermissionSet import PermissionSet
from omaslib.src.connection import Connection
from omaslib.src.enums.permissions import AdminPermission, DataPermission
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.omaserror import OmasErrorInconsistency
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_qname import Xsd_QName


class TestPermissionSet(unittest.TestCase):
    _connection: Connection
    _unpriv: Connection

    @classmethod
    def setUpClass(cls):
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

        cls._connection.clear_graph(Xsd_QName('omas:admin'))
        cls._connection.upload_turtle("omaslib/ontologies/admin.trig")
        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(Xsd_QName('omas:admin'))
        #cls._connection.upload_turtle("omaslib/ontologies/admin.trig")
        #sleep(1)  # upload may take a while...
        pass

    def test_construct_permissionset(self):
        ps = PermissionSet(con=self._connection,
                           label=LangString("testPerm@en", "test@Perm@de"),
                           comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('omas:SystemProject'))
        self.assertEqual(ps.givesPermission, DataPermission.DATA_UPDATE)
        self.assertEqual(ps.label, LangString("testPerm@en", "test@Perm@de"))
        self.assertEqual(ps.comment, LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"))
        self.assertEqual(ps.definedByProject, Iri('omas:SystemProject'))

        with self.assertRaises(OmasErrorInconsistency):
            ps = PermissionSet(con=self._connection,
                               comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                               givesPermission=DataPermission.DATA_UPDATE,
                               definedByProject=Iri('omas:SystemProject'))

        ps = PermissionSet(con=self._connection,
                           label=LangString("\";SELECT * { password ?p ?o . }@en", "test@Perm@de"),
                           comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('omas:SystemProject'))
        ps.create()
        iri = ps.permissionSetIri
        print("\n-------->", iri)
        del ps
        ps = PermissionSet.read(self._connection, iri)
        self.assertEqual(ps.givesPermission, DataPermission.DATA_UPDATE)
        self.assertEqual(ps.label, LangString("testPerm@en", "test@Perm@de"))
        self.assertEqual(ps.comment, LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"))
        self.assertEqual(ps.definedByProject, Iri('omas:SystemProject'))


    # @unittest.skip('Work in progress')
    def test_read_permission(self):
        ps = PermissionSet.read(self._connection, Iri('omas:GenericView'))
        self.assertEqual(ps.givesPermission, DataPermission.DATA_VIEW)  # add assertion here
        self.assertEqual(ps.label, LangString("GenericView@en", "GenericView@de", "GenericView@fr", "GenericView@it"))
        self.assertEqual(ps.definedByProject, Iri('omas:SystemProject'))

    def test_create_permission(self):
        ps = PermissionSet(con=self._connection,
                           label=LangString("testPerm@en", "test@Perm@de"),
                           comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('omas:SystemProject'))
        ps.create()
        iri = ps.permissionSetIri
        del ps
        ps = PermissionSet.read(self._connection, iri)
        self.assertEqual(ps.givesPermission, DataPermission.DATA_UPDATE)
        self.assertEqual(ps.label, LangString("testPerm@en", "test@Perm@de"))
        self.assertEqual(ps.comment, LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"))
        self.assertEqual(ps.definedByProject, Iri('omas:SystemProject'))

    @unittest.skip('Work in progress')
    def test_search_permission_sets(self):
        iris = PermissionSet.search(self._connection)
        print(iris)

if __name__ == '__main__':
    unittest.main()
