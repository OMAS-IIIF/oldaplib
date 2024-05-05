import unittest
from pathlib import Path
from time import sleep

from omaslib.src.enums.permissionsetattr import PermissionSetAttr
from omaslib.src.permissionset import PermissionSet
from omaslib.src.connection import Connection
from omaslib.src.enums.language import Language
from omaslib.src.enums.permissions import DataPermission
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.omaserror import OmasErrorInconsistency, OmasErrorNotFound, OmasErrorNoPermission, OmasErrorAlreadyExists, OmasErrorImmutable
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_string import Xsd_string


def find_project_root(current_path):
    # Climb up the directory hierarchy and check for a marker file
    path = Path(current_path).absolute()
    while not (path / 'pyproject.toml').exists():
        if path.parent == path:
            # Root of the filesystem, file not found
            raise RuntimeError('Project root not found')
        path = path.parent
    return path


class TestPermissionSet(unittest.TestCase):
    _connection: Connection
    _unpriv: Connection

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        project_root = find_project_root(__file__)

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
        file = project_root / 'omaslib' / 'ontologies' / 'admin.trig'
        cls._connection.upload_turtle(file)
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
        self.assertIsNotNone(ps.created)
        self.assertIsNotNone(ps.creator)
        self.assertIsNotNone(ps.modified)
        self.assertIsNotNone(ps.contributor)
        del ps
        ps = PermissionSet.read(self._connection, iri)
        self.assertEqual(ps.givesPermission, DataPermission.DATA_UPDATE)
        self.assertEqual(ps.label, LangString("\";SELECT * { password ?p ?o . }@en", "test@Perm@de"))
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
        self.assertIsNotNone(ps.created)
        self.assertIsNotNone(ps.creator)
        self.assertIsNotNone(ps.modified)
        self.assertIsNotNone(ps.contributor)
        del ps
        ps = PermissionSet.read(self._connection, iri)
        self.assertEqual(ps.givesPermission, DataPermission.DATA_UPDATE)
        self.assertEqual(ps.label, LangString("testPerm@en", "test@Perm@de"))
        self.assertEqual(ps.comment, LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"))
        self.assertEqual(ps.definedByProject, Iri('omas:SystemProject'))

        ps = PermissionSet(con=self._connection,
                           label=LangString("\";SELECT * { password ?p ?o . }@en", "test@Perm@de"),
                           comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('omas:SystemProject'))
        ps.create()
        iri = ps.permissionSetIri
        self.assertIsNotNone(ps.created)
        self.assertIsNotNone(ps.creator)
        self.assertIsNotNone(ps.modified)
        self.assertIsNotNone(ps.contributor)
        del ps
        ps = PermissionSet.read(self._connection, iri)
        self.assertEqual(ps.givesPermission, DataPermission.DATA_UPDATE)
        self.assertEqual(ps.label, LangString("\";SELECT * { password ?p ?o . }@en", "test@Perm@de"))
        self.assertEqual(ps.comment, LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"))
        self.assertEqual(ps.definedByProject, Iri('omas:SystemProject'))

        ps = PermissionSet(con=self._connection,
                           permissionSetIri=Iri('omas:APermSet'),
                           label=LangString("testPerm@en", "test@Perm@de"),
                           comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('omas:SystemProject'))
        ps.create()
        ps = PermissionSet(con=self._connection,
                           permissionSetIri=Iri('omas:APermSet'),
                           label=LangString("testPerm33@en", "test@Perm33@de"),
                           comment=LangString("Testing a PermissionSet33@en", "Test eines PermissionSet33@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('omas:hyperHamlet'))
        with self.assertRaises(OmasErrorAlreadyExists) as ex:
            ps.create()


    def test_create_permission_unauthorized(self):
        ps = PermissionSet(con=self._unpriv,
                           label=LangString("testPermUnauth@en", "test@PermUnauth@de"),
                           comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('omas:SystemProject'))
        with self.assertRaises(OmasErrorNoPermission):
            ps.create()

        def test_create_permission_unauthorized(self):
            ps = PermissionSet(con=self._unpriv,
                               label=LangString("testPermUnauth2@en", "test@PermUnauth2@de"),
                               comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                               givesPermission=DataPermission.DATA_UPDATE,
                               definedByProject=Iri('omas:HyperHamlet'))
            with self.assertRaises(OmasErrorNoPermission):
                ps.create()

    # TODO: More testing!!!
    def test_search_permission_sets(self):
        iris = PermissionSet.search(self._connection, label="GenericView")
        self.assertEqual(len(iris), 1)
        self.assertEqual(Iri('omas:GenericView'), iris[0])

        iris = PermissionSet.search(self._connection, label=Xsd_string("GenericView@de"))
        self.assertEqual(len(iris), 1)
        self.assertEqual(Iri('omas:GenericView'), iris[0])

        iris = PermissionSet.search(self._connection, definedByProject=Iri("omas:HyperHamlet"))
        self.assertEqual(len(iris), 1)
        self.assertEqual(Iri('omas:HyperHamletMember'), iris[0])

        iris = PermissionSet.search(self._connection, givesPermission=DataPermission.DATA_RESTRICTED)
        self.assertEqual(len(iris), 1)
        self.assertEqual(Iri('omas:GenericRestricted'), iris[0])

    def test_update_permission_set(self):
        ps = PermissionSet(con=self._connection,
                           label=LangString("testUpdatePerm@en", "testVerändernPerm@de"),
                           comment=LangString("Testing update of PermissionSet@en", "Test einer Veränderung eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('omas:SystemProject'))
        ps.create()
        psIri = ps.permissionSetIri
        del ps
        ps = PermissionSet.read(self._connection, psIri)
        ps.label[Language.FR] = "testeModificationPerm"
        ps.givesPermission = DataPermission.DATA_VIEW
        ps.update()
        ps = PermissionSet.read(self._connection, psIri)
        self.assertEqual(ps.givesPermission, DataPermission.DATA_VIEW)
        self.assertEqual(ps.label, LangString("testUpdatePerm@en", "testVerändernPerm@de", "testeModificationPerm@fr"))
        del ps.comment
        ps.update()
        self.assertIsNone(ps.comment)
        self.assertIsNone(ps.get(PermissionSetAttr.COMMENT))

        ps = PermissionSet.read(self._connection, psIri)
        ps.comment = LangString("gagagaga@en")
        with self.assertRaises(OmasErrorImmutable):
            ps[PermissionSetAttr.DEFINED_BY_PROJECT] = Iri('omas:HyperHamlet')

        ps = PermissionSet.read(self._unpriv, psIri)
        ps.comment[Language.FR] = "gagagaga"
        with self.assertRaises(OmasErrorNoPermission):
            ps.update()


    def test_delete_permission_set(self):
        ps = PermissionSet(con=self._connection,
                           label=LangString("testDeletePerm@en", "testDeletePerm@de"),
                           comment=LangString("Testing deleting a PermissionSet@en", "Test einer Löschung eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('omas:HyperHamlet'))
        ps.create()
        psIri = ps.permissionSetIri
        del ps
        ps = PermissionSet.read(self._connection, psIri)
        ps.delete()

        with self.assertRaises(OmasErrorNotFound) as ex:
            project = ps.read(self._connection, psIri)


if __name__ == '__main__':
    unittest.main()
