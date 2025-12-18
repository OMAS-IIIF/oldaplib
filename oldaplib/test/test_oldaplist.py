import json
import unittest
from pathlib import Path
from time import sleep

from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.language import Language
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.json_encoder import SpecialEncoder
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapErrorImmutable, OldapErrorNoPermission, \
    OldapErrorInUse
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.iconnection import IConnection
from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.enums.oldaplistattr import OldapListAttr
from oldaplib.src.oldaplist_helpers import load_list_from_yaml
from oldaplib.src.oldaplistnode import OldapListNode
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
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


class TestOldapList(unittest.TestCase):

    _connection: IConnection
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
        pass

    def test_constructor_project_shortname(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestList",
                              prefLabel="TestList",
                              definition="A list for testing...")
        self.assertEqual(Xsd_NCName('TestList'), oldaplist.oldapListId)
        self.assertEqual(LangString("TestList"), oldaplist.prefLabel)
        self.assertEqual(LangString("A list for testing..."), oldaplist.definition)
        self.assertEqual(NamespaceIRI("http://oldap.org/test/TestList#"), oldaplist.node_namespaceIri)
        self.assertEqual(Xsd_NCName('L-TestList'), oldaplist.node_prefix)

    def test_constructor_project_object(self):
        oldaplist = OldapList(con=self._connection,
                              project=self._project,
                              oldapListId="TestList2",
                              prefLabel="TestList2",
                              definition="A list for testing...")
        self.assertEqual(Xsd_NCName('TestList2'), oldaplist.oldapListId)
        self.assertEqual(LangString("TestList2"), oldaplist.prefLabel)
        self.assertEqual(LangString("A list for testing..."), oldaplist.definition)
        self.assertEqual(NamespaceIRI("http://oldap.org/test/TestList2#"), oldaplist.node_namespaceIri)
        self.assertEqual(Xsd_NCName('L-TestList2'), oldaplist.node_prefix)

    def test_dump_json_spez(self):
        oldaplist = OldapList(con=self._connection,
                              project=self._project,
                              oldapListId="TestList3",
                              prefLabel="TestList3",
                              definition="A list for testing...")
        jsonstr = json.dumps(oldaplist, default=serializer.encoder_default)
        oldaplist2 = json.loads(jsonstr, object_hook=serializer.make_decoder_hook(connection=self._connection))
        self.assertEqual(oldaplist2.oldapListId, "TestList3")
        self.assertEqual(oldaplist2.prefLabel, LangString("TestList3@en"))
        self.assertEqual(oldaplist2.definition, LangString("A list for testing...@en"))
        self.assertEqual(oldaplist2.node_classIri, "test:TestList3Node")
        self.assertEqual(oldaplist2.node_namespaceIri, "http://oldap.org/test/TestList3#")
        self.assertEqual(oldaplist2.node_prefix, "L-TestList3")
        self.assertEqual(oldaplist2.iri, "test:TestList3")

    def test_dump_json_list_with_nodes(self):
        oldaplist = OldapList(con=self._connection,
                              project=self._project,
                              oldapListId="TestList3a",
                              prefLabel="TestList3a",
                              definition="A list for testing...")
        jsonstr = json.dumps(oldaplist, default=serializer.encoder_default, indent=2)
        oldaplist2 = json.loads(jsonstr, object_hook=serializer.make_decoder_hook(connection=self._connection))
        self.assertEqual(oldaplist.oldapListId, "TestList3a")
        self.assertEqual(oldaplist.prefLabel, LangString("TestList3a@en"))
        self.assertEqual(oldaplist.definition, LangString("A list for testing...@en"))
        self.assertEqual(oldaplist.node_classIri, "test:TestList3aNode")
        self.assertEqual(oldaplist.node_namespaceIri, "http://oldap.org/test/TestList3a#")
        self.assertEqual(oldaplist.node_prefix, "L-TestList3a")
        self.assertEqual(oldaplist.iri, "test:TestList3a")


    def test_create_read_project_id(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestList_B",
                              prefLabel="TestList_B",
                              definition="A list for testing...")
        oldaplist.create()
        del oldaplist
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestList_B")
        self.assertEqual("TestList_B", oldaplist.oldapListId)
        self.assertEqual(LangString("TestList_B"), oldaplist.prefLabel)
        self.assertEqual(LangString("A list for testing..."), oldaplist.definition)
        self.assertEqual(NamespaceIRI("http://oldap.org/test/TestList_B#"), oldaplist.node_namespaceIri)
        self.assertEqual(Xsd_NCName('L-TestList_B'), oldaplist.node_prefix)

    def test_create_unpriv(self):
        oldaplist = OldapList(con=self._unpriv,
                              project="test",
                              oldapListId="TestList_Unpriv",
                              prefLabel="TestList_Unpriv",
                              definition="A list for testing...")
        with self.assertRaises(OldapErrorNoPermission) as ex:
            oldaplist.create()

    def test_create_read_project_object(self):
        oldaplist = OldapList(con=self._connection,
                              project=self._project,
                              oldapListId="TestList_A",
                              prefLabel="TestList_A",
                              definition="A list for testing...")
        oldaplist.create()
        del oldaplist
        oldaplist = OldapList.read(con=self._connection,
                                   project=self._project,
                                   oldapListId="TestList_A")
        self.assertEqual("TestList_A", oldaplist.oldapListId)
        self.assertEqual(LangString("TestList_A"), oldaplist.prefLabel)
        self.assertEqual(LangString("A list for testing..."), oldaplist.definition)
        self.assertEqual(NamespaceIRI("http://oldap.org/test/TestList_A#"), oldaplist.node_namespaceIri)

    def test_update_A(self):
        oldaplist = OldapList(con=self._connection,
                              project=self._project,
                              oldapListId="TestUpdateListA",
                              prefLabel="TestUpdateListA",
                              definition="A list for testing updates...")
        oldaplist.create()
        del oldaplist
        oldaplist = OldapList.read(con=self._connection,
                                   project=self._project,
                                   oldapListId="TestUpdateListA")
        self.assertEqual("TestUpdateListA", oldaplist.oldapListId)
        self.assertEqual(LangString("TestUpdateListA"), oldaplist.prefLabel)
        self.assertEqual(LangString("A list for testing updates..."), oldaplist.definition)

        oldaplist.prefLabel[Language.FR] = "TestesDeModifications"
        oldaplist.definition = LangString("Test-A@en", "test-B@fr", "test-C@de")
        oldaplist.update()
        oldaplist = OldapList.read(con=self._connection,
                                   project=self._project,
                                   oldapListId="TestUpdateListA")
        self.assertEqual(oldaplist.prefLabel, LangString("TestUpdateListA@en", "TestesDeModifications@fr"))
        self.assertEqual(oldaplist.definition, LangString("Test-A@en", "test-B@fr", "test-C@de"))

        with self.assertRaises(OldapErrorImmutable):
            oldaplist.oldapListId = "Gagagag"

    def test_update_B(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestUpdateListB",
                              prefLabel="TestUpdateListB")
        oldaplist.create()
        del oldaplist
        oldaplist = OldapList.read(con=self._connection,
                                   project=self._project,
                                   oldapListId="TestUpdateListB")
        oldaplist.definition=LangString("Test-A@en", "test-B@fr", "test-C@de")
        oldaplist.update()
        oldaplist = OldapList.read(con=self._connection,
                                   project=self._project,
                                   oldapListId="TestUpdateListB")
        self.assertEqual(oldaplist.definition, LangString("Test-A@en", "test-B@fr", "test-C@de"))

    def test_update_C(self):
        oldaplist = OldapList(con=self._connection,
                              project=self._project,
                              oldapListId="TestUpdateListC",
                              prefLabel="TestUpdateListC",
                              definition="A list for testing updates...")
        oldaplist.create()
        del oldaplist
        oldaplist = OldapList.read(con=self._connection,
                                   project=self._project,
                                   oldapListId="TestUpdateListC")
        del oldaplist.definition
        oldaplist.update()
        oldaplist = OldapList.read(con=self._connection,
                                   project=self._project,
                                   oldapListId="TestUpdateListC")
        self.assertFalse(oldaplist.get(OldapListAttr.DEFINITION))

    def test_delete(self):
        oldaplist = OldapList(con=self._connection,
                              project=self._project,
                              oldapListId="TestDeleteList",
                              prefLabel="TestDeleteList",
                              definition="A list for testing deletes...")
        oldaplist.create()
        del oldaplist
        oldaplist = OldapList.read(con=self._connection,
                                   project=self._project,
                                   oldapListId="TestDeleteList")
        self.assertFalse(oldaplist.in_use())

        oldaplist.delete()
        with self.assertRaises(OldapErrorNotFound) as ex:
            oldaplist = OldapList.read(con=self._connection,
                                       project=self._project,
                                       oldapListId="TestDeleteList")

    def test_delete_no_priv(self):
        oldaplist = OldapList(con=self._connection,
                              project=self._project,
                              oldapListId="TestDeleteList",
                              prefLabel="TestDeleteList",
                              definition="A list for testing deletes...")
        oldaplist.create()
        del oldaplist
        oldaplist = OldapList.read(con=self._unpriv,
                                   project=self._project,
                                   oldapListId="TestDeleteList")
        with self.assertRaises(OldapErrorNoPermission) as ex:
            oldaplist.delete()

    def test_delete_hierarchy(self):
        file = self._project_root / 'oldaplib' / 'testdata' / 'playground_list.yaml'
        oldaplists = load_list_from_yaml(con=self._connection,
                                         project="test",
                                         filepath=file)
        oldaplists[0].delete()

    def test_delete_hierarchy_no_priv(self):
        file = self._project_root / 'oldaplib' / 'testdata' / 'source_type.yaml'
        oldaplists = load_list_from_yaml(con=self._connection,
                                         project="test",
                                         filepath=file)

        oldaplist = OldapList.read(con=self._unpriv,
                                   project=self._project,
                                   oldapListId="source_type")
        with self.assertRaises(OldapErrorNoPermission) as ex:
            oldaplist.delete()

    def test_delete_with_nodes(self):
        dm = DataModel.read(self._connection, self._project, ignore_cache=True)
        dm_name = self._project.projectShortName

        oldaplist = OldapList(con=self._connection,
                              project=self._project,
                              oldapListId="TestDeleteList2",
                              prefLabel="TestDeleteList",
                              definition="A list for testing deletes...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project=self._project,
                                   oldapListId="TestDeleteList2")
        node_classIri = oldaplist.node_classIri
        node = OldapListNode(con=self._connection,
                             **oldaplist.info,
                             oldapListNodeId="TestDeleteList2Node1",
                             prefLabel="TestDelete2ListNode1",
                             definition="A node for testing deletes...")
        node.create_root_node()

        oldaplist = OldapList.read(con=self._connection,
                                   project=self._project,
                                   oldapListId="TestDeleteList2")
        nodes = oldaplist.nodes

        selection = PropertyClass(con=self._connection,
                                  project=self._project,
                                  property_class_iri=Xsd_QName(f'{dm_name}:selection'),
                                  toClass=node_classIri,
                                  name=LangString(["Selection@en", "Selektion@de"]))

        resobj = ResourceClass(con=self._connection,
                               project=self._project,
                               owlclass_iri=Xsd_QName(f'{dm_name}:Resobj'),
                               label=LangString(["Resobj@en", "Resobj@de"]),
                               hasproperties=[
                                   HasProperty(con=self._connection, project=self._project, prop=selection, maxCount=Xsd_integer(1),
                                               minCount=Xsd_integer(1), order=1)])
        dm[Xsd_QName(f'{dm_name}:resobj')] = resobj
        dm.update()
        dm = DataModel.read(self._connection, self._project, ignore_cache=True)

        factory = ResourceInstanceFactory(con=self._connection, project=self._project)
        Resobj = factory.createObjectInstance('Resobj')
        r = Resobj(selection=nodes[0].iri)
        r.create()

        oldaplist = OldapList.read(self._connection, self._project, oldapListId="TestDeleteList2")
        self.assertTrue(oldaplist.in_use())

        with self.assertRaises(OldapErrorInUse):
            node.delete_node()

    def test_search(self):
        oldaplist = OldapList(con=self._connection,
                              project=self._project,
                              oldapListId="animals",
                              prefLabel=LangString("Animals@en", "Tiere@de", "Animaux@fr"),
                              definition="A hierarchical list of all animals")
        oldaplist.create()
        oldaplist = OldapList(con=self._connection,
                              project=self._project,
                              oldapListId="plants",
                              prefLabel=LangString("Plants@en", "Pflanzen@de"),
                              definition="A hierarchical list of all plants")
        oldaplist.create()

        iris = OldapList.search(con=self._connection,
                                project=self._project,
                                prefLabel=Xsd_string("Animals", "en"))
        self.assertEqual(iris, [Xsd_QName('test:animals')])

        iris = OldapList.search(con=self._connection,
                                project=self._project,
                                prefLabel=Xsd_string("Animals"))
        self.assertEqual(iris, [Xsd_QName('test:animals')])

        iris = OldapList.search(con=self._connection,
                                project=self._project,
                                prefLabel=Xsd_string("Pflanzen", "de"))
        self.assertEqual(iris, [Xsd_QName('test:plants')])

        iris = OldapList.search(con=self._connection,
                                project=self._project,
                                prefLabel=Xsd_string("Tier"))
        self.assertEqual(iris, [Xsd_QName('test:animals')])

        iris = OldapList.search(con=self._connection,
                                project=self._project,
                                prefLabel=Xsd_string("Tier"),
                                exactMatch=True)
        self.assertEqual(iris, [])

        iris = OldapList.search(con=self._connection,
                                project=self._project,
                                prefLabel=Xsd_string("Pilze"))
        self.assertEqual(iris, [])

        iris = OldapList.search(con=self._connection,
                                project=self._project,
                                definition=Xsd_string("hierarchical"))
        self.assertTrue(Xsd_QName('test:animals') in iris)
        self.assertTrue(Xsd_QName('test:plants') in iris)





if __name__ == '__main__':
    unittest.main()
