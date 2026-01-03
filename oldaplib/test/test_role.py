import json
import unittest
from copy import deepcopy
from pathlib import Path
from pprint import pprint
from time import sleep

from oldaplib.src.cachesingleton import CacheSingleton, CacheSingletonRedis
from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.roleattr import RoleAttr
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.role import Role
from oldaplib.src.connection import Connection
from oldaplib.src.enums.language import Language
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency, OldapErrorNotFound, OldapErrorNoPermission, \
    OldapErrorAlreadyExists, OldapErrorImmutable, OldapErrorInUse, OldapErrorType
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_integer import Xsd_integer
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
        cache = CacheSingletonRedis()
        cache.clear()
        super().setUpClass()
        cls._project_root = find_project_root(__file__)


        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://testing.org/datatypes#")
        cls._context.use('test')

        cls._connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._unpriv = Connection(userId="fornaro",
                                 credentials="RioGrande",
                                 context_name="DEFAULT")

        cls._connection.clear_graph(Xsd_QName('oldap:admin'))
        file = cls._project_root / 'oldaplib' / 'ontologies' / 'admin.trig'
        cls._connection.upload_turtle(file)

        file = cls._project_root / 'oldaplib' / 'ontologies' / 'admin-testing.trig'
        cls._connection.upload_turtle(file)

        cls._connection.clear_graph(Xsd_QName('test:test'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:lists'))
        cls._connection.clear_graph(Xsd_QName('test:data'))
        file = cls._project_root / 'oldaplib' / 'testdata' / 'connection_test.trig'
        cls._connection.upload_turtle(file)

        cls._project = Project.read(cls._connection, "test")
        LangString.defaultLanguage = Language.EN

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(Xsd_QName('oldap:admin'))
        #cls._connection.upload_turtle("oldap/ontologies/admin.trig")
        #sleep(1)  # upload may take a while...
        pass

    def test_construct_permissionset(self):
        ps = Role(con=self._connection,
                  roleId="test1_ps",
                  label=LangString("testPerm@en", "test@Perm@de"),
                  comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                  definedByProject=Iri('oldap:SystemProject'))
        self.assertEqual(ps.label, LangString("testPerm@en", "test@Perm@de"))
        self.assertEqual(ps.comment, LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"))
        self.assertEqual(ps.definedByProject, Iri('oldap:SystemProject'))

    def test_deepcopy_permissionset(self):
        ps = Role(con=self._connection,
                  roleId="test1_ps",
                  label=LangString("testPerm@en", "test@Perm@de"),
                  comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                  definedByProject=Iri('oldap:SystemProject'))
        ps1 = deepcopy(ps)
        self.assertEqual(ps.roleId, ps1.roleId)
        self.assertFalse(ps.roleId is ps1.roleId)

        self.assertEqual(ps.label, ps1.label)
        self.assertFalse(ps.label is ps1.label)

        self.assertEqual(ps.comment, ps1.comment)
        self.assertFalse(ps.comment is ps1.comment)

        self.assertEqual(ps.definedByProject, ps1.definedByProject)
        self.assertFalse(ps.definedByProject is ps1.definedByProject)


    def test_create_permissionset(self):
        ps = Role(con=self._connection,
                  roleId="test3_ps",
                  label=LangString("\";SELECT * { password ?p ?o . }@en", "test@Perm@de"),
                  comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                  definedByProject=Iri('oldap:SystemProject'))
        ps.create()
        self.assertIsNotNone(ps.created)
        self.assertIsNotNone(ps.creator)
        self.assertIsNotNone(ps.modified)
        self.assertIsNotNone(ps.contributor)
        del ps
        ps = Role.read(con=self._connection, roleId="test3_ps", definedByProject=Iri('oldap:SystemProject'), ignore_cache=True)
        self.assertEqual(ps.label, LangString("\";SELECT * { password ?p ?o . }@en", "test@Perm@de"))
        self.assertEqual(ps.comment, LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"))
        self.assertEqual(ps.definedByProject, Iri('oldap:SystemProject'))

        ps.delete()  # cleanup

    def test_create_permset_with_shortname(self):
        ps = Role(con=self._connection,
                  roleId="test4_ps",
                  label=LangString("test4@en", "test4@Perm@de"),
                  comment=LangString("Testing a PermissionSet 4@en", "Test eines PermissionSet 4@Perm@de"),
                  definedByProject='britnet')
        ps.create()
        ps = Role.read(con=self._connection, roleId="test4_ps", definedByProject=Iri('http://www.salsah.org/version/2.0/SwissBritNet'), ignore_cache=True)
        self.assertEqual(ps.label, LangString("test4@en", "test4@Perm@de"))

        ps.delete()  # cleanup

    def test_create_prmission_set_without_label(self):
        ps = Role(con=self._connection,
                  roleId="test5_ps",
                  label=LangString(),
                  comment=LangString("Testing a PermissionSet 4@en", "Test eines PermissionSet 4@Perm@de"),
                  definedByProject='britnet')
        ps.create()

        ps.read(con=self._connection, roleId="test5_ps", definedByProject='britnet')
        self.assertEqual(ps.definedByProject, Iri("http://www.salsah.org/version/2.0/SwissBritNet"))
        ps.delete()


    # @unittest.skip('Work in progress')
    def test_read_permission_A(self):
        ps = Role.read(con=self._connection, roleId='Unknown', definedByProject='oldap:SystemProject', ignore_cache=True)
        self.assertEqual(ps.label, LangString("Unknown user@en", "Unbekannte(r) Nutzer:in@de", "Utilisateur inconnu@fr", "Utenti sconosciuti@it"))
        self.assertEqual(ps.definedByProject, Iri('oldap:SystemProject'))

    def test_read_permission_B(self):
        ps = Role.read(con=self._connection, roleId='HyperHamletMember', definedByProject='oldap:HyperHamlet', ignore_cache=True)
        self.assertEqual(ps.label, LangString("Team HyperHamlet@en", "Team HyperHamlet@de", "Équipe HyperHamlet@fr", "Team HyperHamlet@it"))
        self.assertEqual(ps.definedByProject, Iri('oldap:HyperHamlet'))

    def test_read_permission_with_cache(self):
        ps = Role.read(con=self._connection, roleId='HyperHamletMember', definedByProject='oldap:HyperHamlet', ignore_cache=True)
        ps2 = Role.read(con=self._connection, roleId='HyperHamletMember', definedByProject='oldap:HyperHamlet')

        self.assertEqual(ps2.label, LangString("Team HyperHamlet@en", "Team HyperHamlet@de", "Équipe HyperHamlet@fr", "Team HyperHamlet@it"))
        self.assertEqual(ps.label, ps2.label)
        self.assertFalse(ps.label is ps2.label)

        self.assertEqual(ps2.definedByProject, Iri('oldap:HyperHamlet'))
        self.assertEqual(ps.definedByProject, ps2.definedByProject)
        self.assertFalse(ps.definedByProject is ps2.definedByProject)

    def test_read_permission_with_iri(self):
        ps = Role.read(con=self._connection, qname=Xsd_QName('hyha:HyperHamletMember'), ignore_cache=True)
        self.assertEqual(ps.label, LangString("Team HyperHamlet@en", "Team HyperHamlet@de", "Équipe HyperHamlet@fr", "Team HyperHamlet@it"))
        self.assertEqual(ps.definedByProject, Iri('oldap:HyperHamlet'))


    def test_create_permission(self):
        ps = Role(con=self._connection,
                  roleId="testPerm",
                  label=LangString("testPerm@en", "test@Perm@de"),
                  comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                  definedByProject=Iri('oldap:SystemProject'))
        ps.create()
        self.assertIsNotNone(ps.created)
        self.assertIsNotNone(ps.creator)
        self.assertIsNotNone(ps.modified)
        self.assertIsNotNone(ps.contributor)
        del ps
        ps = Role.read(con=self._connection, roleId="testPerm", definedByProject='oldap:SystemProject', ignore_cache=True)
        self.assertEqual(ps.label, LangString("testPerm@en", "test@Perm@de"))
        self.assertEqual(ps.comment, LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"))
        self.assertEqual(ps.definedByProject, Iri('oldap:SystemProject'))

        ps.delete()  # cleanup

    def test_create_permission_strange_label(self):
        ps = Role(con=self._connection,
                  roleId="gagaPerm",
                  label=LangString("\";SELECT * { password ?p ?o . }@en", "test@Perm@de"),
                  comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                  definedByProject=Iri('oldap:SystemProject'))
        ps.create()
        self.assertIsNotNone(ps.created)
        self.assertIsNotNone(ps.creator)
        self.assertIsNotNone(ps.modified)
        self.assertIsNotNone(ps.contributor)
        del ps
        ps = Role.read(con=self._connection, roleId="gagaPerm", definedByProject='oldap:SystemProject', ignore_cache=True)
        self.assertEqual(ps.label, LangString("\";SELECT * { password ?p ?o . }@en", "test@Perm@de"))
        self.assertEqual(ps.comment, LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"))
        self.assertEqual(ps.definedByProject, Iri('oldap:SystemProject'))

        ps.delete()

    def test_create_permission_no_label(self):
        ps = Role(con=self._connection,
                  roleId="gagaPerm2",
                  definedByProject=Iri('oldap:SystemProject'))
        ps.create()
        del ps
        ps = Role.read(con=self._connection, roleId="gagaPerm2", definedByProject='oldap:SystemProject', ignore_cache=True)
        self.assertIsNone(ps.label)
        self.assertIsNone(ps.comment)
        self.assertEqual(ps.definedByProject, Iri('oldap:SystemProject'))

        ps.delete()

    def test_create_permission_duplicate(self):
        ps = Role(con=self._connection,
                  roleId="testPerm2",
                  label=LangString("testPerm@en", "test@Perm@de"),
                  comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                  definedByProject=Iri('oldap:SystemProject'))
        ps.create()
        ps = Role(con=self._connection,
                  roleId="testPerm2",
                  label=LangString("testPerm33@en", "test@Perm33@de"),
                  comment=LangString("Testing a PermissionSet33@en", "Test eines PermissionSet33@Perm@de"),
                  definedByProject=Iri('oldap:SystemProject'))
        with self.assertRaises(OldapErrorAlreadyExists) as ex:
            ps.create()

        ps.read(con=self._connection, roleId="testPerm2", definedByProject=Iri('oldap:SystemProject'))

        ps.delete()

    def test_create_permission_unauthorized(self):
        ps = Role(con=self._unpriv,
                  roleId="testPermUnauth",
                  label=LangString("testPermUnauth@en", "test@PermUnauth@de"),
                  comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                  definedByProject=Iri('oldap:SystemProject'))
        with self.assertRaises(OldapErrorNoPermission):
            ps.create()

    def test_create_permission_unauthorized(self):
        ps = Role(con=self._unpriv,
                           roleId="testPermUnauth",
                           label=LangString("testPermUnauth2@en", "test@PermUnauth2@de"),
                           comment=LangString("Testing a PermissionSet@en", "Test eines PermissionSet@Perm@de"),
                           definedByProject=Iri('oldap:HyperHamlet'))
        with self.assertRaises(OldapErrorNoPermission):
            ps.create()

    # TODO: More testing!!!
    def test_search_roles(self):
        iris = Role.search(self._connection, label="Unknown user")
        self.assertEqual(len(iris), 1)
        self.assertTrue(Xsd_QName('oldap:Unknown') in iris)

        iris = Role.search(self._connection, label=Xsd_string("Unbekannte(r) Nutzer:in@de"))
        self.assertEqual(len(iris), 1)
        self.assertTrue(Xsd_QName('oldap:Unknown') in iris)

        iris = Role.search(self._connection, definedByProject=Iri("oldap:HyperHamlet"))
        self.assertEqual(len(iris), 1)
        self.assertEqual(Xsd_QName('hyha:HyperHamletMember'), iris[0])

        iris = Role.search(self._connection)
        self.assertEqual({Xsd_QName("oldap:Unknown"),
                          Xsd_QName("hyha:HyperHamletMember")}, set(iris))

    def test_update_permission_set(self):
        ps = Role(con=self._connection,
                  roleId="testUpdatePerm",
                  label=LangString("testUpdatePerm@en", "testVerändernPerm@de"),
                  comment=LangString("Testing update of PermissionSet@en", "Test einer Veränderung eines PermissionSet@Perm@de"),
                  definedByProject=Iri('oldap:SystemProject'))
        ps.create()

        psId = ps.roleId
        del ps
        ps = Role.read(con=self._connection, roleId=psId, definedByProject=Iri('oldap:SystemProject'), ignore_cache=True)
        ps.label[Language.FR] = "testeModificationPerm"
        ps.update()
        ps = Role.read(con=self._connection, roleId=psId, definedByProject=Iri('oldap:SystemProject'))
        self.assertEqual(ps.label, LangString("testUpdatePerm@en", "testVerändernPerm@de", "testeModificationPerm@fr"))
        del ps.comment
        ps.update()
        self.assertIsNone(ps.comment)
        self.assertIsNone(ps.get(RoleAttr.COMMENT))

        ps = Role.read(con=self._connection, roleId=psId, definedByProject=Iri('oldap:SystemProject'), ignore_cache=True)
        ps.comment = LangString("gagagaga@en")
        with self.assertRaises(OldapErrorImmutable):
            ps[RoleAttr.DEFINED_BY_PROJECT] = Iri('oldap:HyperHamlet')

        ps = Role.read(con=self._unpriv, roleId=psId, definedByProject=Iri('oldap:SystemProject'), ignore_cache=True)
        ps.comment = LangString("gagagaga@fr")
        with self.assertRaises(OldapErrorNoPermission):
            ps.update()

        ps = Role.read(con=self._connection, roleId=psId, definedByProject=Iri('oldap:SystemProject'), ignore_cache=True)
        ps.delete()


    def test_update_permissionset_B(self):
        ps = Role(con=self._connection,
                  roleId="testUpdatePermB",
                  label=LangString("testUpdatePerm@en", "testVerändernPerm@de"),
                  comment=LangString("Testing update of PermissionSet@en", "Test einer Veränderung eines PermissionSet@Perm@de"),
                  definedByProject=Iri('oldap:SystemProject'))
        ps.create()
        psId = ps.roleId
        del ps
        ps = Role.read(con=self._connection, roleId=psId, definedByProject=Iri('oldap:SystemProject'), ignore_cache=True)

        ps.label[Language.IT] = "TEST_ADD_DEL"
        del ps.label[Language.EN]
        ps.update()

    def test_delete_permission_set(self):
        ps = Role(con=self._connection,
                  roleId="testDeletePerm",
                  label=LangString("testDeletePerm@en", "testDeletePerm@de"),
                  comment=LangString("Testing deleting a PermissionSet@en", "Test einer Löschung eines PermissionSet@Perm@de"),
                  definedByProject=Iri('oldap:HyperHamlet'))
        ps.create()
        del ps
        ps = Role.read(con=self._connection, roleId="testDeletePerm", definedByProject=Iri('oldap:HyperHamlet'), ignore_cache=True)
        ps.delete()

        with self.assertRaises(OldapErrorNotFound) as ex:
            project = ps.read(con=self._connection, roleId="testDeletePerm", definedByProject=Iri('oldap:HyperHamlet'), ignore_cache=True)

    def test_delete_permission_set_in_use(self):
        ps = Role.read(con=self._connection, roleId="Unknown", definedByProject=Iri('oldap:SystemProject'), ignore_cache=True)
        with self.assertRaises(OldapErrorInUse):
            ps.delete()

    # TODO: THIS TEST MUST BE TESTED LATER AFTER DATAMODEL ETC. HAVE bEEN ADAPED TO ROLES!
    def test_delete_permission_set_user_with_data(self):
        dm = DataModel.read(self._connection, self._project, ignore_cache=True)
        dm_name = self._project.projectShortName

        irgendwas = PropertyClass(con=self._connection,
                                  project=self._project,
                                  property_class_iri=Xsd_QName(f'{dm_name}:irgendwas'),
                                  datatype=XsdDatatypes.string,
                                  name=LangString(["AnyString@en", "Irgendwas@de"]))

        #
        # Now we create a simple data model
        #
        resobj = ResourceClass(con=self._connection,
                               project=self._project,
                               owlclass_iri=Xsd_QName(f'{dm_name}:DummyClass'),
                               label=LangString(["Dummy@en", "Dummy@de"]),
                               hasproperties=[
                                   HasProperty(con=self._connection, project=self._project, prop=irgendwas, maxCount=Xsd_integer(1),
                                               minCount=Xsd_integer(1), order=1)])
        dm[Xsd_QName(f'{dm_name}:resobj')] = resobj
        dm.update()
        dm = DataModel.read(self._connection, self._project, ignore_cache=True)

        factory = ResourceInstanceFactory(con=self._connection, project=self._project)
        DummyClass = factory.createObjectInstance('DummyClass')
        r = DummyClass(irgendwas="Dies ist irgend ein String", grantsPermission=Xsd_QName('oldap:GenericUpdate'))
        r.create()

        ps = Role.read(con=self._connection, roleId="GenericUpdate", definedByProject=Iri('oldap:SystemProject'), ignore_cache=True)
        with self.assertRaises(OldapErrorInUse):
            ps.delete()



if __name__ == '__main__':
    unittest.main()
