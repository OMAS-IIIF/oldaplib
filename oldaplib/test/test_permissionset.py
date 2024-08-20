import unittest
from copy import deepcopy
from pathlib import Path
from time import sleep

from oldaplib.src.enums.permissionsetattr import PermissionSetAttr
from oldaplib.src.permissionset import PermissionSet
from oldaplib.src.connection import Connection
from oldaplib.src.enums.language import Language
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency, OldapErrorNotFound, OldapErrorNoPermission, OldapErrorAlreadyExists, OldapErrorImmutable
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName
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


class TestPermissionSet(unittest.TestCase):
    _connection: Connection
    _unpriv: Connection

    @classmethod
    def setUpClass(cls):
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

        cls._connection.clear_graph(Xsd_QName('oldap:admin'))
        file = project_root / 'oldaplib' / 'ontologies' / 'admin.trig'
        cls._connection.upload_turtle(file)
        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(Xsd_QName('oldap:admin'))
        #cls._connection.upload_turtle("oldap/ontologies/admin.trig")
        #sleep(1)  # upload may take a while...
        pass

    def test_construct_permissionset(self):
        ps = PermissionSet(con=self._connection,
                           permissionSetId="test1_ps",
                           label=LangString("testPerm@en", "test@Perm@de"),
                           comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('oldap:SystemProject'))
        self.assertEqual(ps.givesPermission, DataPermission.DATA_UPDATE)
        self.assertEqual(ps.label, LangString("testPerm@en", "test@Perm@de"))
        self.assertEqual(ps.comment, LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"))
        self.assertEqual(ps.definedByProject, Iri('oldap:SystemProject'))

    def test_deepcopy_permissionset(self):
        ps = PermissionSet(con=self._connection,
                           permissionSetId="test1_ps",
                           label=LangString("testPerm@en", "test@Perm@de"),
                           comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('oldap:SystemProject'))
        ps1 = deepcopy(ps)
        self.assertEqual(ps.permissionSetId, ps1.permissionSetId)
        self.assertFalse(ps.permissionSetId is ps1.permissionSetId)

        self.assertEqual(ps.label, ps1.label)
        self.assertFalse(ps.label is ps1.label)

        self.assertEqual(ps.comment, ps1.comment)
        self.assertFalse(ps.comment is ps1.comment)

        self.assertEqual(ps.givesPermission, ps1.givesPermission)

        self.assertEqual(ps.definedByProject, ps1.definedByProject)
        self.assertFalse(ps.definedByProject is ps1.definedByProject)


    def test_create_permissionset(self):
        ps = PermissionSet(con=self._connection,
                           permissionSetId="test3_ps",
                           label=LangString("\";SELECT * { password ?p ?o . }@en", "test@Perm@de"),
                           comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('oldap:SystemProject'))
        ps.create()
        self.assertIsNotNone(ps.created)
        self.assertIsNotNone(ps.creator)
        self.assertIsNotNone(ps.modified)
        self.assertIsNotNone(ps.contributor)
        del ps
        ps = PermissionSet.read(self._connection, "test3_ps", Iri('oldap:SystemProject'), ignore_cache=True)
        self.assertEqual(ps.givesPermission, DataPermission.DATA_UPDATE)
        self.assertEqual(ps.label, LangString("\";SELECT * { password ?p ?o . }@en", "test@Perm@de"))
        self.assertEqual(ps.comment, LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"))
        self.assertEqual(ps.definedByProject, Iri('oldap:SystemProject'))

    def test_create_permset_with_shortname(self):
        ps = PermissionSet(con=self._connection,
                           permissionSetId="test4_ps",
                           label=LangString("test4@en", "test4@Perm@de"),
                           comment=LangString("Testing a PermissionSet 4@en", "Test eines PermissionSet 4@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject='britnet')
        ps.create()
        ps = PermissionSet.read(self._connection, "test4_ps", Iri('http://www.salsah.org/version/2.0/SwissBritNet'), ignore_cache=True)
        self.assertEqual(ps.givesPermission, DataPermission.DATA_UPDATE)
        self.assertEqual(ps.label, LangString("test4@en", "test4@Perm@de"))

    def test_create_prmission_set_without_label(self):
        ps = PermissionSet(con=self._connection,
                           permissionSetId="test5_ps",
                           label=LangString(),
                           comment=LangString("Testing a PermissionSet 4@en", "Test eines PermissionSet 4@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject='britnet')
        ps.create()
        self.assertEqual(ps.givesPermission, DataPermission.DATA_UPDATE)

    # @unittest.skip('Work in progress')
    def test_read_permission_A(self):
        ps = PermissionSet.read(self._connection, 'GenericView', 'oldap:SystemProject', ignore_cache=True)
        self.assertEqual(ps.givesPermission, DataPermission.DATA_VIEW)  # add assertion here
        self.assertEqual(ps.label, LangString("GenericView@en", "GenericView@de", "GenericView@fr", "GenericView@it"))
        self.assertEqual(ps.definedByProject, Iri('oldap:SystemProject'))

    def test_read_permission_B(self):
        ps = PermissionSet.read(self._connection, 'HyperHamletMember', 'oldap:HyperHamlet', ignore_cache=True)
        self.assertEqual(ps.givesPermission, DataPermission.DATA_UPDATE)  # add assertion here
        self.assertEqual(ps.label, LangString("HyHaUpdate@en", "HyHaUpdate@de", "HyHaUpdate@fr", "HyHaUpdate@it"))
        self.assertEqual(ps.definedByProject, Iri('oldap:HyperHamlet'))

    def test_read_permission_with_cache(self):
        ps = PermissionSet.read(self._connection, 'HyperHamletMember', 'oldap:HyperHamlet', ignore_cache=True)
        ps2 = PermissionSet.read(self._connection, 'HyperHamletMember', 'oldap:HyperHamlet')
        self.assertEqual(ps2.givesPermission, DataPermission.DATA_UPDATE)
        self.assertEqual(ps.givesPermission, ps2.givesPermission)

        self.assertEqual(ps2.label, LangString("HyHaUpdate@en", "HyHaUpdate@de", "HyHaUpdate@fr", "HyHaUpdate@it"))
        self.assertEqual(ps.label, ps2.label)
        self.assertFalse(ps.label is ps2.label)

        self.assertEqual(ps2.definedByProject, Iri('oldap:HyperHamlet'))
        self.assertEqual(ps.definedByProject, ps2.definedByProject)
        self.assertFalse(ps.definedByProject is ps2.definedByProject)


    def test_create_permission(self):
        ps = PermissionSet(con=self._connection,
                           permissionSetId="testPerm",
                           label=LangString("testPerm@en", "test@Perm@de"),
                           comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('oldap:SystemProject'))
        ps.create()
        self.assertIsNotNone(ps.created)
        self.assertIsNotNone(ps.creator)
        self.assertIsNotNone(ps.modified)
        self.assertIsNotNone(ps.contributor)
        del ps
        ps = PermissionSet.read(self._connection, "testPerm", 'oldap:SystemProject', ignore_cache=True)
        self.assertEqual(ps.givesPermission, DataPermission.DATA_UPDATE)
        self.assertEqual(ps.label, LangString("testPerm@en", "test@Perm@de"))
        self.assertEqual(ps.comment, LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"))
        self.assertEqual(ps.definedByProject, Iri('oldap:SystemProject'))

    def test_create_permission_strange_label(self):
        ps = PermissionSet(con=self._connection,
                           permissionSetId="gagaPerm",
                           label=LangString("\";SELECT * { password ?p ?o . }@en", "test@Perm@de"),
                           comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('oldap:SystemProject'))
        ps.create()
        self.assertIsNotNone(ps.created)
        self.assertIsNotNone(ps.creator)
        self.assertIsNotNone(ps.modified)
        self.assertIsNotNone(ps.contributor)
        del ps
        ps = PermissionSet.read(self._connection, "gagaPerm", 'oldap:SystemProject', ignore_cache=True)
        self.assertEqual(ps.givesPermission, DataPermission.DATA_UPDATE)
        self.assertEqual(ps.label, LangString("\";SELECT * { password ?p ?o . }@en", "test@Perm@de"))
        self.assertEqual(ps.comment, LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"))
        self.assertEqual(ps.definedByProject, Iri('oldap:SystemProject'))

    def test_create_permission_no_label(self):
        ps = PermissionSet(con=self._connection,
                           permissionSetId="gagaPerm2",
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('oldap:SystemProject'))
        ps.create()
        del ps
        ps = PermissionSet.read(self._connection, "gagaPerm2", 'oldap:SystemProject', ignore_cache=True)
        self.assertEqual(ps.givesPermission, DataPermission.DATA_UPDATE)
        self.assertIsNone(ps.label)
        self.assertIsNone(ps.comment)
        self.assertEqual(ps.definedByProject, Iri('oldap:SystemProject'))

    def test_create_permission_duplicate(self):
        ps = PermissionSet(con=self._connection,
                           permissionSetId="testPerm2",
                           label=LangString("testPerm@en", "test@Perm@de"),
                           comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('oldap:SystemProject'))
        ps.create()
        ps = PermissionSet(con=self._connection,
                           permissionSetId="testPerm2",
                           label=LangString("testPerm33@en", "test@Perm33@de"),
                           comment=LangString("Testing a PermissionSet33@en", "Test eines PermissionSet33@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('oldap:SystemProject'))
        with self.assertRaises(OldapErrorAlreadyExists) as ex:
            ps.create()


    def test_create_permission_unauthorized(self):
        ps = PermissionSet(con=self._unpriv,
                           permissionSetId="testPermUnauth",
                           label=LangString("testPermUnauth@en", "test@PermUnauth@de"),
                           comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('oldap:SystemProject'))
        with self.assertRaises(OldapErrorNoPermission):
            ps.create()

        def test_create_permission_unauthorized(self):
            ps = PermissionSet(con=self._unpriv,
                               label=LangString("testPermUnauth2@en", "test@PermUnauth2@de"),
                               comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                               givesPermission=DataPermission.DATA_UPDATE,
                               definedByProject=Iri('oldap:HyperHamlet'))
            with self.assertRaises(OldapErrorNoPermission):
                ps.create()

    # TODO: More testing!!!
    def test_search_permission_sets(self):
        iris = PermissionSet.search(self._connection, label="GenericView")
        self.assertEqual(len(iris), 2)
        self.assertTrue(Iri('oldap:GenericView') in iris)

        iris = PermissionSet.search(self._connection, label=Xsd_string("GenericView@de"))
        self.assertEqual(len(iris), 2)
        self.assertTrue(Iri('oldap:GenericView') in iris)

        iris = PermissionSet.search(self._connection, definedByProject=Iri("oldap:HyperHamlet"))
        self.assertEqual(len(iris), 1)
        self.assertEqual(Iri('hyha:HyperHamletMember'), iris[0])

        iris = PermissionSet.search(self._connection, givesPermission=DataPermission.DATA_RESTRICTED)
        #self.assertEqual(len(iris), 1)
        self.assertEqual([Iri('oldap:GenericRestricted')], iris)

    def test_update_permission_set(self):
        ps = PermissionSet(con=self._connection,
                           permissionSetId="testUpdatePerm",
                           label=LangString("testUpdatePerm@en", "testVerändernPerm@de"),
                           comment=LangString("Testing update of PermissionSet@en", "Test einer Veränderung eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('oldap:SystemProject'))
        ps.create()
        psId = ps.permissionSetId
        del ps
        ps = PermissionSet.read(self._connection, psId, Iri('oldap:SystemProject'), ignore_cache=True)
        ps.label[Language.FR] = "testeModificationPerm"
        ps.givesPermission = DataPermission.DATA_VIEW
        ps.update()
        ps = PermissionSet.read(self._connection, psId, Iri('oldap:SystemProject'))
        self.assertEqual(ps.givesPermission, DataPermission.DATA_VIEW)
        self.assertEqual(ps.label, LangString("testUpdatePerm@en", "testVerändernPerm@de", "testeModificationPerm@fr"))
        del ps.comment
        ps.update()
        self.assertIsNone(ps.comment)
        self.assertIsNone(ps.get(PermissionSetAttr.COMMENT))

        ps = PermissionSet.read(self._connection, psId, Iri('oldap:SystemProject'), ignore_cache=True)
        ps.comment = LangString("gagagaga@en")
        with self.assertRaises(OldapErrorImmutable):
            ps[PermissionSetAttr.DEFINED_BY_PROJECT] = Iri('oldap:HyperHamlet')

        ps = PermissionSet.read(self._unpriv, psId, Iri('oldap:SystemProject'), ignore_cache=True)
        ps.comment = LangString("gagagaga@fr")
        with self.assertRaises(OldapErrorNoPermission):
            ps.update()

    def test_update_permissionset_B(self):
        ps = PermissionSet(con=self._connection,
                           permissionSetId="testUpdatePermB",
                           label=LangString("testUpdatePerm@en", "testVerändernPerm@de"),
                           comment=LangString("Testing update of PermissionSet@en", "Test einer Veränderung eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('oldap:SystemProject'))
        ps.create()
        psId = ps.permissionSetId
        del ps
        ps = PermissionSet.read(self._connection, psId, Iri('oldap:SystemProject'), ignore_cache=True)

        ps.label[Language.IT] = "TEST_ADD_DEL"
        del ps.label[Language.EN]
        ps.update()

    def test_delete_permission_set(self):
        ps = PermissionSet(con=self._connection,
                           permissionSetId="testDeletePerm",
                           label=LangString("testDeletePerm@en", "testDeletePerm@de"),
                           comment=LangString("Testing deleting a PermissionSet@en", "Test einer Löschung eines PermissionSet@Perm@de"),
                           givesPermission=DataPermission.DATA_UPDATE,
                           definedByProject=Iri('oldap:HyperHamlet'))
        ps.create()
        del ps
        ps = PermissionSet.read(self._connection, "testDeletePerm", Iri('oldap:HyperHamlet'), ignore_cache=True)
        ps.delete()

        with self.assertRaises(OldapErrorNotFound) as ex:
            project = ps.read(self._connection, "testDeletePerm", Iri('oldap:HyperHamlet'), ignore_cache=True)


if __name__ == '__main__':
    unittest.main()
