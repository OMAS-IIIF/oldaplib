import json
import unittest
from pathlib import Path
from pprint import pprint
from time import sleep

from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.language import Language
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapErrorInconsistency, OldapErrorNoPermission, \
    OldapErrorInUse
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.iconnection import IConnection
from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplist_helpers import load_list_from_yaml, get_node_by_id
from oldaplib.src.oldaplistnode import OldapListNode
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


def find_project_root(current_path):
    # Climb up the directory hierarchy and check for a marker file
    path = Path(current_path).absolute()
    while not (path / 'pyproject.toml').exists():
        if path.parent == path:
            # Root of the filesystem, file not found
            raise RuntimeError('Project root not found')
        path = path.parent
    return path

class TestOldapListNode(unittest.TestCase):

    _connection: IConnection

    @classmethod
    def setUpClass(cls):
        cache = CacheSingletonRedis()
        cache.clear()

        super().setUpClass()
        cls._project_root = find_project_root(__file__)

        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://testing.org/datatypes#")
        cls._context['dmtest'] = NamespaceIRI('http://oldap.org/dmtest#')

        cls._context.use('test', 'dmtest')
        cls._connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._unpriv = Connection(userId="unknown",
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
        cls._connection.clear_graph(Xsd_QName('dmtest:shacl'))
        cls._connection.clear_graph(Xsd_QName('dmtest:onto'))
        cls._connection.clear_graph(Xsd_QName('dmtest:data'))
        cls._connection.clear_graph(Xsd_QName('dmtest:lists'))

        file = cls._project_root / 'oldaplib' / 'testdata' / 'connection_test.trig'
        cls._connection.upload_turtle(file)

        cls._project = Project.read(cls._connection, "test")
        cls._dmproject = Project.read(cls._connection, "dmtest", ignore_cache=True)
        LangString.defaultLanguage = Language.EN


    @classmethod
    def tearDownClass(cls):
        pass

    def test_root_constructor(self):
        project = Project.read(con=self._connection, projectIri_SName="test")
        oldaplist = OldapList(con=self._connection,
                              project=project,
                              oldapListId="TestList",
                              prefLabel="TestList",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project=project,
                                   oldapListId="TestList")
        oln = OldapListNode(con=self._connection,
                            **oldaplist.info,
                            oldapListNodeId="Node_A",
                            prefLabel="Node_A",
                            definition="First node")
        oln.create_root_node()

        oln = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual("Node_A", oln.oldapListNodeId)
        self.assertEqual(LangString("Node_A"), oln.prefLabel)
        self.assertEqual(LangString("First node@en"), oln.definition)
        self.assertEqual(Xsd_integer(1), oln.leftIndex)
        self.assertEqual(Xsd_integer(2), oln.rightIndex)

    def test_lists_jsonify(self):
        project = Project.read(con=self._connection, projectIri_SName="test")
        oldaplist = OldapList(con=self._connection,
                              project=project,
                              oldapListId="TestListCache",
                              prefLabel="TestListCache",
                              definition="A list for testing cache...")
        oldaplist.create()

        olnA = OldapListNode(con=self._connection,
                            **oldaplist.info,
                            oldapListNodeId="Node_A",
                            prefLabel="Node_A",
                            definition="First node")
        olnA.create_root_node()

        olnB = OldapListNode(con=self._connection,
                            **oldaplist.info,
                            oldapListNodeId="Node_B",
                            prefLabel="Node_B",
                            definition="Second node")
        olnB.insert_node_right_of(olnA)

        olnC = OldapListNode(con=self._connection,
                            **oldaplist.info,
                            oldapListNodeId="Node_C",
                            prefLabel="Node_C",
                            definition="third node")
        olnC.insert_node_right_of(olnB)

        olnBA = OldapListNode(con=self._connection,
                            **oldaplist.info,
                            oldapListNodeId="Node_BA",
                            prefLabel="Node_BA",
                            definition="sub to second")
        olnBA.insert_node_below_of(olnB)


        oldaplist1 = OldapList.read(con=self._connection,
                                    project=project,
                                    oldapListId="TestListCache")
        oldaplist2 = OldapList.read(con=self._connection,
                                    project=project,
                                    oldapListId="TestListCache")
        self.assertEqual(oldaplist1.nodes[0], oldaplist2.nodes[0])
        self.assertEqual(oldaplist1.nodes[1], oldaplist2.nodes[1])
        self.assertEqual(oldaplist1.nodes[1].nodes[0], oldaplist2.nodes[1].nodes[0])
        self.assertEqual(oldaplist1.nodes[2], oldaplist2.nodes[2])

    def test_root_constructor_unpriv(self):
        project = Project.read(con=self._connection, projectIri_SName="test")
        oldaplist = OldapList(con=self._connection,
                              project=project,
                              oldapListId="TestListUnpriv",
                              prefLabel="TestListUnpriv",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._unpriv,
                                   project=project,
                                   oldapListId="TestListUnpriv")
        oln = OldapListNode(con=self._unpriv,
                            **oldaplist.info,
                            oldapListNodeId="Node_A",
                            prefLabel="Node_A",
                            definition="First node")
        with self.assertRaises(OldapErrorNoPermission) as ex:
            oln.create_root_node()
        #
        # oln = OldapListNode.read(con=self._connection,
        #                          oldapList=oldaplist,
        #                          oldapListNodeId="Node_A")
        # self.assertEqual("Node_A", oln.oldapListNodeId)
        # self.assertEqual(LangString("Node_A"), oln.prefLabel)
        # self.assertEqual(LangString("First node@en"), oln.definition)
        # self.assertEqual(Xsd_integer(1), oln.leftIndex)
        # self.assertEqual(Xsd_integer(2), oln.rightIndex)

    def test_update(self):
        project = Project.read(con=self._connection, projectIri_SName="test")
        oldaplist = OldapList(con=self._connection,
                              project=project,
                              oldapListId="TestListUpdate",
                              prefLabel="TestListUpdate",
                              definition="A list for test updating...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project=project,
                                   oldapListId="TestListUpdate")
        oln = OldapListNode(con=self._connection,
                            **oldaplist.info,
                            oldapListNodeId="Node_A",
                            prefLabel="Node_A",
                            definition="First node")
        oln.create_root_node()
        oln = OldapListNode.read(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        oln.prefLabel = LangString("First Node")
        oln.definition = LangString("Erster Knoten@de")
        oln.update()
        oln = OldapListNode.read(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        self.assertEqual(oln.oldapListNodeId, "Node_A")
        self.assertEqual(oln.prefLabel, LangString("First Node@en"))
        self.assertEqual(oln.definition, LangString("Erster Knoten@de"))

        oln.prefLabel[Language.DE] = "Erster Knoten"
        oln.definition[Language.EN] = "First Node"
        oln.update()

        oln = OldapListNode.read(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        self.assertEqual(oln.prefLabel, LangString("First Node@en", "Erster Knoten@de"))
        self.assertEqual(oln.definition, LangString("Erster Knoten@de", "First Node@en"))

        del oln.prefLabel[Language.EN]
        del oln.definition
        oln.update()
        self.assertEqual(oln.prefLabel, LangString("Erster Knoten@de"))
        self.assertIsNone(oln.definition)

    def test_get_nodes_from_list(self):
        project = Project.read(con=self._connection, projectIri_SName="test")
        oldaplist = OldapList(con=self._connection,
                              project=project,
                              oldapListId="TestGetNodesFromList",
                              prefLabel="TestGetNodesFromList",
                              definition="A list for test updating...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project=project,
                                   oldapListId="TestGetNodesFromList")
        oln = OldapListNode(con=self._connection,
                            **oldaplist.info,
                            oldapListNodeId="Node_A",
                            prefLabel="Node_A",
                            definition="First node")
        oln.create_root_node()
        oln = OldapListNode.read(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        oln.prefLabel = LangString("First Node")
        oln.definition = LangString("Erster Knoten@de")
        oln.update()

        oldaplist = OldapList.read(con=self._connection,
                                   project=project,
                                   oldapListId="TestGetNodesFromList")
        hlist = oldaplist.nodes
        self.assertEqual(hlist[0].prefLabel, LangString("First Node@en"))
        self.assertEqual(len(hlist[0].prefLabel), 1)

    def test_insert_right_of_A(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListA",
                              prefLabel="TestListA",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListA")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

    def test_insert_right_of_B(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListB",
                              prefLabel="TestListB",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListB")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olC.leftIndex)
        self.assertEqual(Xsd_integer(4), olC.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

    def test_insert_left_of_A(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListC",
                              prefLabel="TestListC",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListC")
        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.create_root_node()
        self.assertEqual(Xsd_integer(1), olB.leftIndex)
        self.assertEqual(Xsd_integer(2), olB.rightIndex)

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.insert_node_left_of(rightnode=olB)
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

    def test_insert_left_of_B(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListD",
                              prefLabel="TestListD",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListD")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olC.leftIndex)
        self.assertEqual(Xsd_integer(4), olC.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_left_of(rightnode=olC)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

    def test_insert_below_of_A(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListE",
                              prefLabel="TestListE",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListE")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_AA")
        olAA.insert_node_below_of(parentnode=olA)
        self.assertEqual(Xsd_integer(2), olAA.leftIndex)
        self.assertEqual(Xsd_integer(3), olAA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(4), olA.rightIndex)

        olAA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_AA")
        self.assertEqual(Xsd_integer(2), olAA.leftIndex)
        self.assertEqual(Xsd_integer(3), olAA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(5), olB.leftIndex)
        self.assertEqual(Xsd_integer(6), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(7), olC.leftIndex)
        self.assertEqual(Xsd_integer(8), olC.rightIndex)

    def test_insert_below_of_B(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListF",
                              prefLabel="TestListF",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListF")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(6), olB.rightIndex)

        olBA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_BA")
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(7), olC.leftIndex)
        self.assertEqual(Xsd_integer(8), olC.rightIndex)

    def test_insert_below_of_C(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListG",
                              prefLabel="TestListG",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListG")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olCA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_CA")
        olCA.insert_node_below_of(parentnode=olC)
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(7), olCA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(8), olC.rightIndex)

        olCA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_CA")
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(7), olCA.rightIndex)

    def test_insert_below_left_A(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListH",
                              prefLabel="TestListH",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListH")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olAB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_AB")
        olAB.insert_node_below_of(parentnode=olA)
        self.assertEqual(Xsd_integer(2), olAB.leftIndex)
        self.assertEqual(Xsd_integer(3), olAB.rightIndex)

        olAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_AA")
        olAA.insert_node_left_of(olAB)
        self.assertEqual(Xsd_integer(2), olAB.leftIndex)
        self.assertEqual(Xsd_integer(3), olAB.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(6), olA.rightIndex)

        olAA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_AA")
        self.assertEqual(Xsd_integer(2), olAA.leftIndex)
        self.assertEqual(Xsd_integer(3), olAA.rightIndex)

        olAB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_AB")
        self.assertEqual(Xsd_integer(4), olAB.leftIndex)
        self.assertEqual(Xsd_integer(5), olAB.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(7), olB.leftIndex)
        self.assertEqual(Xsd_integer(8), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(9), olC.leftIndex)
        self.assertEqual(Xsd_integer(10), olC.rightIndex)

    def test_insert_below_left_B(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListI",
                              prefLabel="TestListI",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListI")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BB")
        olBB.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBB.leftIndex)
        self.assertEqual(Xsd_integer(5), olBB.rightIndex)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_left_of(rightnode=olBB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(8), olB.rightIndex)

        olBA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_BA")
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olBB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_BB")
        self.assertEqual(Xsd_integer(6), olBB.leftIndex)
        self.assertEqual(Xsd_integer(7), olBB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(9), olC.leftIndex)
        self.assertEqual(Xsd_integer(10), olC.rightIndex)

    def test_insert_below_left_C(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListJ",
                              prefLabel="TestListJ",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListJ")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olCB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_CB")
        olCB.insert_node_below_of(parentnode=olC)
        self.assertEqual(Xsd_integer(6), olCB.leftIndex)
        self.assertEqual(Xsd_integer(7), olCB.rightIndex)

        olCA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_CA")
        olCA.insert_node_left_of(rightnode=olCB)
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(7), olCA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(10), olC.rightIndex)

        olCA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_CA")
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(7), olCA.rightIndex)

        olCB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_CB")
        self.assertEqual(Xsd_integer(8), olCB.leftIndex)
        self.assertEqual(Xsd_integer(9), olCB.rightIndex)

    def test_insert_below_right_A(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListK",
                              prefLabel="TestListK",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListK")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_AA")
        olAA.insert_node_below_of(parentnode=olA)
        self.assertEqual(Xsd_integer(2), olAA.leftIndex)
        self.assertEqual(Xsd_integer(3), olAA.rightIndex)

        olAB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_AB")
        olAB.insert_node_right_of(leftnode=olAA)
        self.assertEqual(Xsd_integer(4), olAB.leftIndex)
        self.assertEqual(Xsd_integer(5), olAB.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(6), olA.rightIndex)

        olAA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_AA")
        self.assertEqual(Xsd_integer(2), olAA.leftIndex)
        self.assertEqual(Xsd_integer(3), olAA.rightIndex)

        olAB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_AB")
        self.assertEqual(Xsd_integer(4), olAB.leftIndex)
        self.assertEqual(Xsd_integer(5), olAB.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(7), olB.leftIndex)
        self.assertEqual(Xsd_integer(8), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(9), olC.leftIndex)
        self.assertEqual(Xsd_integer(10), olC.rightIndex)

    def test_insert_below_right_B(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListL",
                              prefLabel="TestListL",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListL")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olBB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BB")
        olBB.insert_node_right_of(leftnode=olBA)
        self.assertEqual(Xsd_integer(6), olBB.leftIndex)
        self.assertEqual(Xsd_integer(7), olBB.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(8), olB.rightIndex)

        olBA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_BA")
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olBB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_BB")
        self.assertEqual(Xsd_integer(6), olBB.leftIndex)
        self.assertEqual(Xsd_integer(7), olBB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(9), olC.leftIndex)
        self.assertEqual(Xsd_integer(10), olC.rightIndex)

    def test_insert_below_right_C(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListM",
                              prefLabel="TestListM",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListM")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olCA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_CA")
        olCA.insert_node_below_of(parentnode=olC)
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(7), olCA.rightIndex)

        olCB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_CB")
        olCB.insert_node_right_of(leftnode=olCA)
        self.assertEqual(Xsd_integer(8), olCB.leftIndex)
        self.assertEqual(Xsd_integer(9), olCB.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(10), olC.rightIndex)

        olCA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_CA")
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(7), olCA.rightIndex)

        olCB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_CB")
        self.assertEqual(Xsd_integer(8), olCB.leftIndex)
        self.assertEqual(Xsd_integer(9), olCB.rightIndex)

    def test_insert_below_below_A(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListN",
                              prefLabel="TestListN",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListN")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_AA")
        olAA.insert_node_below_of(parentnode=olA)
        self.assertEqual(Xsd_integer(2), olAA.leftIndex)
        self.assertEqual(Xsd_integer(3), olAA.rightIndex)

        olAAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_AAA")
        olAAA.insert_node_below_of(parentnode=olAA)
        self.assertEqual(Xsd_integer(3), olAAA.leftIndex)
        self.assertEqual(Xsd_integer(4), olAAA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(6), olA.rightIndex)

        olAA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_AA")
        self.assertEqual(Xsd_integer(2), olAA.leftIndex)
        self.assertEqual(Xsd_integer(5), olAA.rightIndex)

        olAAA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_AAA")
        self.assertEqual(Xsd_integer(3), olAAA.leftIndex)
        self.assertEqual(Xsd_integer(4), olAAA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(7), olB.leftIndex)
        self.assertEqual(Xsd_integer(8), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(9), olC.leftIndex)
        self.assertEqual(Xsd_integer(10), olC.rightIndex)

    def test_insert_below_below_B(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListO",
                              prefLabel="TestListO",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListO")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olBAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BAA")
        olBAA.insert_node_below_of(parentnode=olBA)
        self.assertEqual(Xsd_integer(5), olBAA.leftIndex)
        self.assertEqual(Xsd_integer(6), olBAA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(8), olB.rightIndex)

        olBA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_BA")
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(7), olBA.rightIndex)

        olBAA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_BAA")
        self.assertEqual(Xsd_integer(5), olBAA.leftIndex)
        self.assertEqual(Xsd_integer(6), olBAA.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(9), olC.leftIndex)
        self.assertEqual(Xsd_integer(10), olC.rightIndex)

    def test_insert_below_below_C(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListP",
                              prefLabel="TestListP",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListP")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olCA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_CA")
        olCA.insert_node_below_of(parentnode=olC)
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(7), olCA.rightIndex)

        olCAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_CAA")
        olCAA.insert_node_below_of(parentnode=olCA)
        self.assertEqual(Xsd_integer(7), olCAA.leftIndex)
        self.assertEqual(Xsd_integer(8), olCAA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(10), olC.rightIndex)

        olCA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_CA")
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(9), olCA.rightIndex)

        olCAA = OldapListNode.read(con=self._connection,
                                   **oldaplist.info,
                                   oldapListNodeId="Node_CAA")
        self.assertEqual(Xsd_integer(7), olCAA.leftIndex)
        self.assertEqual(Xsd_integer(8), olCAA.rightIndex)

    def test_delete_A(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListQ",
                              prefLabel="TestListQ",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListQ")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        olA.delete_node()

        del olA

        with self.assertRaises(OldapErrorNotFound):
            olA = OldapListNode.read(con=self._connection,
                                     **oldaplist.info,
                                     oldapListNodeId="Node_A")

    def test_delete_B(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListR",
                              prefLabel="TestListR",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListR")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olC.leftIndex)
        self.assertEqual(Xsd_integer(4), olC.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olA.delete_node()
        with self.assertRaises(OldapErrorNotFound):
            olA = OldapListNode.read(con=self._connection,
                                     **oldaplist.info,
                                     oldapListNodeId="Node_A")

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(1), olB.leftIndex)
        self.assertEqual(Xsd_integer(2), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(3), olC.leftIndex)
        self.assertEqual(Xsd_integer(4), olC.rightIndex)

    def test_delete_C(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListS",
                              prefLabel="TestListS",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListS")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olC.leftIndex)
        self.assertEqual(Xsd_integer(4), olC.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olB.delete_node()
        with self.assertRaises(OldapErrorNotFound):
            olB = OldapListNode.read(con=self._connection,
                                     **oldaplist.info,
                                     oldapListNodeId="Node_B")

        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(3), olC.leftIndex)
        self.assertEqual(Xsd_integer(4), olC.rightIndex)

    def test_delete_D(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListT",
                              prefLabel="TestListT",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListT")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olC.leftIndex)
        self.assertEqual(Xsd_integer(4), olC.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC.delete_node()
        with self.assertRaises(OldapErrorNotFound):
            olC = OldapListNode.read(con=self._connection,
                                     **oldaplist.info,
                                     oldapListNodeId="Node_C")

        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

    def test_delete_E(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListU",
                              prefLabel="TestListU",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListU")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olA.delete_node()
        with self.assertRaises(OldapErrorNotFound):
            olA = OldapListNode.read(con=self._connection,
                                     **oldaplist.info,
                                     oldapListNodeId="Node_A")

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(1), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olBA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_BA")
        self.assertEqual(Xsd_integer(2), olBA.leftIndex)
        self.assertEqual(Xsd_integer(3), olBA.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

    def test_delete_F(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListV",
                              prefLabel="TestListV",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListV")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        with self.assertRaises(OldapErrorInUse):
            olB.delete_node()

        olBA.delete_node()
        with self.assertRaises(OldapErrorNotFound):
            olBA = OldapListNode.read(con=self._connection,
                                     **oldaplist.info,
                                     oldapListNodeId="Node_BA")

        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

    def test_delete_G(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListW",
                              prefLabel="TestListW",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListW")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)


        olC.delete_node()
        with self.assertRaises(OldapErrorNotFound):
            olC = OldapListNode.read(con=self._connection,
                                     **oldaplist.info,
                                     oldapListNodeId="Node_C")

        olA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(6), olB.rightIndex)

        olBA = OldapListNode.read(con=self._connection,
                                 **oldaplist.info,
                                 oldapListNodeId="Node_BA")
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

    def test_delete_in_use(self):
        dm = DataModel(con=self._connection, project=self._dmproject)
        dm.create()
        #
        # load hierarchical list from YAML
        #
        file = self._project_root / 'oldaplib' / 'testdata' / 'testlist.yaml'
        oldaplists = load_list_from_yaml(con=self._connection,
                                         project=self._dmproject,
                                         filepath=file)
        testnode = get_node_by_id(oldaplists[0].nodes, Xsd_NCName("node_A"))

        node_classIri = oldaplists[0].node_classIri
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        dm_name = self._dmproject.projectShortName

        selection = PropertyClass(con=self._connection,
                                  project=self._dmproject,
                                  property_class_iri=Xsd_QName(f'{dm_name}:selection'),
                                  toClass=node_classIri,
                                  name=LangString(["Selection@en", "Selektion@de"]))

        #
        # Now we create a simple data model
        #
        resobj = ResourceClass(con=self._connection,
                               project=self._dmproject,
                               owlclass_iri=Xsd_QName(f'{dm_name}:Resobj'),
                               label=LangString(["Resobj@en", "Resobj@de"]),
                               hasproperties=[
                                   HasProperty(con=self._connection, project=self._dmproject, prop=selection, maxCount=Xsd_integer(1),
                                               minCount=Xsd_integer(1), order=1)])
        dm[Xsd_QName(f'{dm_name}:resobj')] = resobj
        dm.update()
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)

        #
        # let's add a resource which references the node
        #
        factory = ResourceInstanceFactory(con=self._connection, project=self._dmproject)
        Resobj = factory.createObjectInstance('Resobj')
        r = Resobj(selection=testnode.iri)
        r.create()

        with self.assertRaises(OldapErrorInUse):
            testnode.delete_node()


    def test_delete_recursively(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestDelRec",
                              prefLabel="TestDelRec",
                              definition="A list for testing...")
        oldaplist.create()
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)

        olBB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BB")
        olBB.insert_node_right_of(leftnode=olBA)

        olBC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BC")
        olBC.insert_node_right_of(leftnode=olBB)

        olBBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBA")
        olBBA.insert_node_below_of(parentnode=olBB)

        olBBB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBB")
        olBBB.insert_node_right_of(leftnode=olBBA)

        olBBC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBC")
        olBBC.insert_node_right_of(leftnode=olBBB)

        olBBBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBBA")
        olBBBA.insert_node_below_of(parentnode=olBBB)



        olBB.delete_node_recursively()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestDelRec")
        nodes = oldaplist.nodes
        #nodes = get_nodes_from_list(con=self._connection, **oldaplist.info)

        node_A = nodes[0]
        self.assertEqual(Xsd_integer(1), node_A.leftIndex)
        self.assertEqual(Xsd_integer(2), node_A.rightIndex)

        node_B = nodes[1]
        self.assertEqual(Xsd_integer(3), node_B.leftIndex)
        self.assertEqual(Xsd_integer(8), node_B.rightIndex)

        node_BA = nodes[1].nodes[0]
        self.assertEqual(Xsd_integer(4), node_BA.leftIndex)
        self.assertEqual(Xsd_integer(5), node_BA.rightIndex)

        node_BC = nodes[1].nodes[1]
        self.assertEqual(Xsd_integer(6), node_BC.leftIndex)
        self.assertEqual(Xsd_integer(7), node_BC.rightIndex)

        node_C = nodes[2]
        self.assertEqual(Xsd_integer(9), node_C.leftIndex)
        self.assertEqual(Xsd_integer(10), node_C.rightIndex)

    def test_delete_recursively_in_user(self):
        #
        # load a hierarchical list from YAML
        #
        file = self._project_root / 'oldaplib' / 'testdata' / 'playground_list.yaml'
        oldaplists = load_list_from_yaml(con=self._connection,
                                         project="test",
                                         filepath=file)
        testnode = get_node_by_id(oldaplists[0].nodes, Xsd_NCName("physics"))
        node_classIri = oldaplists[0].node_classIri

        dm = DataModel.read(self._connection, self._project, ignore_cache=True)
        dm_name = self._project.projectShortName


        #
        # Now we create a simple data model
        #
        selection = PropertyClass(con=self._connection,
                                  project=self._project,
                                  property_class_iri=Xsd_QName(f'{dm_name}:selection2'),
                                  toClass=node_classIri,
                                  name=LangString(["Selection2@en", "Selektion2@de"]))

        resobj = ResourceClass(con=self._connection,
                               project=self._project,
                               owlclass_iri=Xsd_QName(f'{dm_name}:Resobj2'),
                               label=LangString(["Resobj2@en", "Resobj2@de"]),
                               hasproperties=[
                                   HasProperty(con=self._connection, project=self._project, prop=selection, maxCount=Xsd_integer(1),
                                               minCount=Xsd_integer(1), order=1)])
        dm[Xsd_QName(f'{dm_name}:Resobj2')] = resobj
        dm.update()
        dm = DataModel.read(self._connection, self._project, ignore_cache=True)

        #
        # let's add a resource which references the node
        #
        factory = ResourceInstanceFactory(con=self._connection, project=self._project)
        Resobj = factory.createObjectInstance('Resobj2')
        r = Resobj(selection2=testnode.iri)
        r.create()

        delnode = get_node_by_id(oldaplists[0].nodes, Xsd_NCName("nonfiction"))
        with self.assertRaises(OldapErrorInUse):
            delnode.delete_node()

    def test_move_simple_A(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveSimpleA",
                              prefLabel="TestMoveSimpleA",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olB.move_node_left_of(con=self._connection, rightnode=olA)

        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveSimpleA")
        nodes = oldaplist.nodes
        self.assertEqual(nodes[0].oldapListNodeId, "Node_B")
        self.assertEqual(nodes[0].leftIndex, 1)
        self.assertEqual(nodes[0].rightIndex, 2)
        self.assertEqual(nodes[1].oldapListNodeId, "Node_A")
        self.assertEqual(nodes[1].leftIndex, 3)
        self.assertEqual(nodes[1].rightIndex, 4)

    def test_move_simple_B(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveSimpleB",
                              prefLabel="TestMoveSimpleB",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olA.move_node_right_of(con=self._connection, leftnode=olB)

        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveSimpleB")
        nodes = oldaplist.nodes
        self.assertEqual(nodes[0].oldapListNodeId, "Node_B")
        self.assertEqual(nodes[0].leftIndex, 1)
        self.assertEqual(nodes[0].rightIndex, 2)
        self.assertEqual(nodes[1].oldapListNodeId, "Node_A")
        self.assertEqual(nodes[1].leftIndex, 3)
        self.assertEqual(nodes[1].rightIndex, 4)

    def test_move_simple_C(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveSimpleC",
                              prefLabel="TestMoveSimpleC",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olA.move_node_below(con=self._connection, target=olB)

        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveSimpleC")
        nodes = oldaplist.nodes
        self.assertEqual(nodes[0].oldapListNodeId, "Node_B")
        self.assertEqual(len(nodes[0].nodes), 1)
        self.assertEqual(nodes[0].leftIndex, 1)
        self.assertEqual(nodes[0].rightIndex, 4)
        self.assertEqual(nodes[0].nodes[0].oldapListNodeId, "Node_A")
        self.assertEqual(nodes[0].nodes[0].leftIndex, 2)
        self.assertEqual(nodes[0].nodes[0].rightIndex, 3)

    def test_move_simple_D(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveSimpleD",
                              prefLabel="TestMoveSimpleD",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olB.move_node_below(con=self._connection, target=olA)

        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveSimpleD")
        nodes = oldaplist.nodes
        self.assertEqual(nodes[0].oldapListNodeId, "Node_A")
        self.assertEqual(len(nodes[0].nodes), 1)
        self.assertEqual(nodes[0].leftIndex, 1)
        self.assertEqual(nodes[0].rightIndex, 4)
        self.assertEqual(nodes[0].nodes[0].oldapListNodeId, "Node_B")
        self.assertEqual(nodes[0].nodes[0].leftIndex, 2)
        self.assertEqual(nodes[0].nodes[0].rightIndex, 3)


    def test_move_below_toR(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveBelowR",
                              prefLabel="TestMoveBelowR",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)

        olBB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BB")
        olBB.insert_node_right_of(leftnode=olBA)

        olBC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BC")
        olBC.insert_node_right_of(leftnode=olBB)

        olBBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBA")
        olBBA.insert_node_below_of(parentnode=olBB)

        olBBB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBB")
        olBBB.insert_node_right_of(leftnode=olBBA)

        olBBC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBC")
        olBBC.insert_node_right_of(leftnode=olBBB)

        olBBBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBBA")
        olBBBA.insert_node_below_of(parentnode=olBBB)

        olBB.move_node_below(con=self._connection, target=olC)
        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveBelowR")
        nodes = oldaplist.nodes
        for node in nodes:
            match node.oldapListNodeId:
                case "Node_A":
                    self.assertEqual(node.leftIndex, 1)
                    self.assertEqual(node.rightIndex, 2)
                    self.assertIsNone(node.nodes)
                case "Node_B":
                    self.assertEqual(node.leftIndex, 3)
                    self.assertEqual(node.rightIndex, 8)
                    self.assertEqual(len(node.nodes), 2)
                    for node2 in node.nodes:
                        match node2.oldapListNodeId:
                            case "Node_BA":
                                self.assertEqual(node2.leftIndex, 4)
                                self.assertEqual(node2.rightIndex, 5)
                                self.assertIsNone(node2.nodes)
                            case "Node_BC":
                                self.assertEqual(node2.leftIndex, 6)
                                self.assertEqual(node2.rightIndex, 7)
                                self.assertIsNone(node2.nodes)
                            case _:
                                raise AssertionError(f'Found unexpected node: {node.oldpListNodeId}')
                case "Node_C":
                    self.assertEqual(node.leftIndex, 9)
                    self.assertEqual(node.rightIndex, 20)
                    self.assertEqual(len(node.nodes), 1)
                    self.assertEqual(node.nodes[0].oldapListNodeId, "Node_BB")
                    self.assertEqual(node.nodes[0].leftIndex, 10)
                    self.assertEqual(node.nodes[0].rightIndex, 19)
                    self.assertEqual(len(node.nodes[0].nodes), 3)
                    for node2 in node.nodes[0].nodes:
                        match node2.oldapListNodeId:
                            case "Node_BBA":
                                self.assertEqual(node2.leftIndex, 11)
                                self.assertEqual(node2.rightIndex, 12)
                            case "Node_BBB":
                                self.assertEqual(node2.leftIndex, 13)
                                self.assertEqual(node2.rightIndex, 16)
                                self.assertEqual(len(node2.nodes), 1)
                                self.assertEqual(node2.nodes[0].leftIndex, 14)
                                self.assertEqual(node2.nodes[0].rightIndex, 15)
                            case "Node_BBC":
                                self.assertEqual(node2.leftIndex, 17)
                                self.assertEqual(node2.rightIndex, 18)
                            case _:
                                raise AssertionError(f'Found unexpected node: {node.oldpListNodeId}')

    def test_move_below_toR02(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveBelowR02",
                              prefLabel="TestMoveBelowR02",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)

        olA.move_node_below(con=self._connection, target=olC)

        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveBelowR02")
        nodes = oldaplist.nodes
        self.assertEqual(len(nodes), 2)
        for node in nodes:
            match node.oldapListNodeId:
                case "Node_B":
                    self.assertEqual(node.leftIndex, 1)
                    self.assertEqual(node.rightIndex, 2)
                case "Node_C":
                    self.assertEqual(node.leftIndex, 3)
                    self.assertEqual(node.rightIndex, 6)
                    self.assertEqual(len(node.nodes), 1)
                    self.assertEqual(node.nodes[0].oldapListNodeId, "Node_A")
                    self.assertEqual(node.nodes[0].leftIndex, 4)
                    self.assertEqual(node.nodes[0].rightIndex, 5)
                case _:
                    raise AssertionError("Invalid node")

    def test_move_below_toL(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveBelowL",
                              prefLabel="TestMoveBelowL",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)

        olBB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BB")
        olBB.insert_node_right_of(leftnode=olBA)

        olBC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BC")
        olBC.insert_node_right_of(leftnode=olBB)

        olBBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBA")
        olBBA.insert_node_below_of(parentnode=olBB)

        olBBB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBB")
        olBBB.insert_node_right_of(leftnode=olBBA)

        olBBC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBC")
        olBBC.insert_node_right_of(leftnode=olBBB)

        olBBBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBBA")
        olBBBA.insert_node_below_of(parentnode=olBBB)

        olBB.move_node_below(con=self._connection, target=olA)
        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveBelowL")
        nodes = oldaplist.nodes
        for node in nodes:
            match node.oldapListNodeId:
                case "Node_A":
                    self.assertEqual(node.leftIndex, 1)
                    self.assertEqual(node.rightIndex, 12)
                    self.assertEqual(len(node.nodes), 1)
                    self.assertEqual(node.nodes[0].oldapListNodeId, "Node_BB")
                    self.assertEqual(node.nodes[0].leftIndex, 2)
                    self.assertEqual(node.nodes[0].rightIndex, 11)
                    for node2 in node.nodes[0].nodes:
                        match node2.oldapListNodeId:
                            case "Node_BBA":
                                self.assertEqual(node2.leftIndex, 3)
                                self.assertEqual(node2.rightIndex, 4)
                            case "Node_BBB":
                                self.assertEqual(node2.leftIndex, 5)
                                self.assertEqual(node2.rightIndex, 8)
                                self.assertEqual(len(node2.nodes), 1)
                                self.assertEqual(node2.nodes[0].oldapListNodeId, "Node_BBBA")
                                self.assertEqual(node2.nodes[0].leftIndex, 6)
                                self.assertEqual(node2.nodes[0].rightIndex, 7)
                            case "Node_BBC":
                                self.assertEqual(node2.leftIndex, 9)
                                self.assertEqual(node2.rightIndex, 10)
                            case _:
                                raise AssertionError("Unexpected node")
                case "Node_B":
                    self.assertEqual(node.leftIndex, 13)
                    self.assertEqual(node.rightIndex, 18)
                case "Node_C":
                    self.assertEqual(node.leftIndex, 19)
                    self.assertEqual(node.rightIndex, 20)
                case _:
                    raise AssertionError("Unexpected node")

    def test_move_below_toL02(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveBelowL02",
                              prefLabel="TestMoveBelowL02",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)

        olC.move_node_below(con=self._connection, target=olA)

        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveBelowL02")
        nodes = oldaplist.nodes
        self.assertEqual(len(nodes), 2)
        for node in nodes:
            match node.oldapListNodeId:
                case "Node_A":
                    self.assertEqual(node.leftIndex, 1)
                    self.assertEqual(node.rightIndex, 4)
                    self.assertEqual(len(node.nodes), 1)
                    self.assertEqual(node.nodes[0].oldapListNodeId, "Node_C")
                    self.assertEqual(node.nodes[0].leftIndex, 2)
                    self.assertEqual(node.nodes[0].rightIndex, 3)
                case "Node_B":
                    self.assertEqual(node.leftIndex, 5)
                    self.assertEqual(node.rightIndex, 6)
                case _:
                    raise AssertionError("Unexpected node")


    def test_move_right_of_toR(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveRightOfL",
                              prefLabel="TestMoveRightOfL",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)

        olCA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_CA")
        olCA.insert_node_below_of(parentnode=olC)

        olD = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_D")
        olD.insert_node_right_of(leftnode=olC)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)

        olBB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BB")
        olBB.insert_node_right_of(leftnode=olBA)

        olBC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BC")
        olBC.insert_node_right_of(leftnode=olBB)

        olBBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBA")
        olBBA.insert_node_below_of(parentnode=olBB)

        olBBB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBB")
        olBBB.insert_node_right_of(leftnode=olBBA)

        olBBC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBC")
        olBBC.insert_node_right_of(leftnode=olBBB)

        olBBBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBBA")
        olBBBA.insert_node_below_of(parentnode=olBBB)

        olDA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_DA")
        olDA.insert_node_below_of(parentnode=olD)

        olBB.move_node_right_of(con=self._connection, leftnode=olC)

        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveRightOfL")
        nodes = oldaplist.nodes

        for node in nodes:
            match node.oldapListNodeId:
                case "Node_A":
                    self.assertEqual(node.leftIndex, 1)
                    self.assertEqual(node.rightIndex, 2)
                case "Node_B":
                    self.assertEqual(node.leftIndex, 3)
                    self.assertEqual(node.rightIndex, 8)
                    self.assertEqual(len(node.nodes), 2)
                    for node2 in node.nodes:
                        match node2.oldapListNodeId:
                            case "Node_BA":
                                self.assertEqual(node2.leftIndex, 4)
                                self.assertEqual(node2.rightIndex, 5)
                            case "Node_BC":
                                self.assertEqual(node2.leftIndex, 6)
                                self.assertEqual(node2.rightIndex, 7)
                            case _:
                                raise AssertionError("Unexpected node")
                case "Node_C":
                    self.assertEqual(node.leftIndex, 9)
                    self.assertEqual(node.rightIndex, 12)
                    self.assertEqual(len(node.nodes), 1)
                    self.assertEqual(node.nodes[0].oldapListNodeId, "Node_CA")
                    self.assertEqual(node.nodes[0].leftIndex, 10)
                    self.assertEqual(node.nodes[0].rightIndex, 11)
                case "Node_BB":
                    self.assertEqual(node.leftIndex, 13)
                    self.assertEqual(node.rightIndex, 22)
                    self.assertEqual(len(node.nodes), 3)
                    for node2 in node.nodes:
                        match node2.oldapListNodeId:
                            case "Node_BBA":
                                self.assertEqual(node2.leftIndex, 14)
                                self.assertEqual(node2.rightIndex, 15)
                            case "Node_BBB":
                                self.assertEqual(node2.leftIndex, 16)
                                self.assertEqual(node2.rightIndex, 19)
                                self.assertEqual(len(node2.nodes), 1)
                                self.assertEqual(node2.nodes[0].oldapListNodeId, "Node_BBBA")
                                self.assertEqual(node2.nodes[0].leftIndex, 17)
                                self.assertEqual(node2.nodes[0].rightIndex, 18)
                            case "Node_BBC":
                                self.assertEqual(node2.leftIndex, 20)
                                self.assertEqual(node2.rightIndex, 21)
                            case _:
                                raise AssertionError("Unexpected node")
                case "Node_D":
                    self.assertEqual(node.leftIndex, 23)
                    self.assertEqual(node.rightIndex, 26)
                    self.assertEqual(len(node.nodes), 1)
                    self.assertEqual(node.nodes[0].leftIndex, 24)
                    self.assertEqual(node.nodes[0].rightIndex, 25)
                case _:
                    raise AssertionError("Unexpected node")

    def test_move_right_of_toR02(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveRightOf02",
                              prefLabel="TestMoveRightOf02",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)

        olD = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_D")
        olD.insert_node_right_of(leftnode=olC)

        olA.move_node_right_of(con=self._connection, leftnode=olD)
        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveRightOf02")
        nodes = oldaplist.nodes
        for node in nodes:
            match node.oldapListNodeId:
                case "Node_B":
                    self.assertEqual(node.leftIndex, 1)
                    self.assertEqual(node.rightIndex, 2)
                case "Node_C":
                    self.assertEqual(node.leftIndex, 3)
                    self.assertEqual(node.rightIndex, 4)
                case "Node_D":
                    self.assertEqual(node.leftIndex, 5)
                    self.assertEqual(node.rightIndex, 6)
                case "Node_A":
                    self.assertEqual(node.leftIndex, 7)
                    self.assertEqual(node.rightIndex, 8)


    def test_move_right_of_toL01(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveRightOfL01",
                              prefLabel="TestMoveRightOfRL01",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)

        olBB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BB")
        olBB.insert_node_right_of(leftnode=olBA)

        olBC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BC")
        olBC.insert_node_right_of(leftnode=olBB)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)

        olD = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_D")
        olD.insert_node_right_of(leftnode=olC)

        olDA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_DA")
        olDA.insert_node_below_of(parentnode=olD)

        olDAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_DAA")
        olDAA.insert_node_below_of(parentnode=olDA)

        olDAB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_DAB")
        olDAB.insert_node_right_of(leftnode=olDAA)

        olDAC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_DAC")
        olDAC.insert_node_right_of(leftnode=olDAB)

        olE = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_E")
        olE.insert_node_right_of(leftnode=olD)

        olDA.move_node_right_of(con=self._connection, leftnode=olBB)
        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveRightOfL01")
        nodes = oldaplist.nodes

        for node in nodes:
            match node.oldapListNodeId:
                case "Node_A":
                    self.assertEqual(node.leftIndex, 1)
                    self.assertEqual(node.rightIndex, 2)
                case "Node_B":
                    self.assertEqual(node.leftIndex, 3)
                    self.assertEqual(node.rightIndex, 18)
                    self.assertEqual(len(node.nodes), 4)
                    for node2 in node.nodes:
                        match node2.oldapListNodeId:
                            case "Node_BA":
                                self.assertEqual(node2.leftIndex, 4)
                                self.assertEqual(node2.rightIndex, 5)
                            case "Node_BB":
                                self.assertEqual(node2.leftIndex, 6)
                                self.assertEqual(node2.rightIndex, 7)
                            case "Node_DA":
                                self.assertEqual(node2.leftIndex, 8)
                                self.assertEqual(node2.rightIndex, 15)
                                self.assertEqual(len(node2.nodes), 3)
                                for node3 in node2.nodes:
                                    match node3.oldapListNodeId:
                                        case "Node_DAA":
                                            self.assertEqual(node3.leftIndex, 9)
                                            self.assertEqual(node3.rightIndex, 10)
                                        case "Node_DAB":
                                            self.assertEqual(node3.leftIndex, 11)
                                            self.assertEqual(node3.rightIndex, 12)
                                        case "Node_DAC":
                                            self.assertEqual(node3.leftIndex, 13)
                                            self.assertEqual(node3.rightIndex, 14)
                                        case _:
                                            raise AssertionError("Unexpected node")
                            case "Node_BC":
                                self.assertEqual(node2.leftIndex, 16)
                                self.assertEqual(node2.rightIndex, 17)
                            case _:
                                raise AssertionError("Unexpected node")
                case "Node_C":
                    self.assertEqual(node.leftIndex, 19)
                    self.assertEqual(node.rightIndex, 20)
                case "Node_D":
                    self.assertEqual(node.leftIndex, 21)
                    self.assertEqual(node.rightIndex, 22)
                case "Node_E":
                    self.assertEqual(node.leftIndex, 23)
                    self.assertEqual(node.rightIndex, 24)
                case _:
                    raise AssertionError("Unexpected node")

    def test_move_right_of_toL02(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveRightOfR02",
                              prefLabel="TestMoveRightOfR02",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_AA")
        olAA.insert_node_below_of(parentnode=olA)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)

        olBB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BB")
        olBB.insert_node_right_of(leftnode=olBA)

        olBC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BC")
        olBC.insert_node_right_of(leftnode=olBB)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)

        olD = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_D")
        olD.insert_node_right_of(leftnode=olC)

        olDA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_DA")
        olDA.insert_node_below_of(parentnode=olD)

        olDAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_DAA")
        olDAA.insert_node_below_of(parentnode=olDA)

        olDAB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_DAB")
        olDAB.insert_node_right_of(leftnode=olDAA)

        olDAC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_DAC")
        olDAC.insert_node_right_of(leftnode=olDAB)

        olE = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_E")
        olE.insert_node_right_of(leftnode=olD)

        olDA.move_node_right_of(con=self._connection, leftnode=olA)

        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveRightOfR02")
        nodes = oldaplist.nodes

        for node in nodes:
            match node.oldapListNodeId:
                case "Node_A":
                    self.assertEqual(node.leftIndex, 1)
                    self.assertEqual(node.rightIndex, 4)
                    self.assertEqual(len(node.nodes), 1)
                    self.assertEqual(node.nodes[0].leftIndex, 2)
                    self.assertEqual(node.nodes[0].rightIndex, 3)
                case "Node_DA":
                    self.assertEqual(node.leftIndex, 5)
                    self.assertEqual(node.rightIndex, 12)
                    self.assertEqual(len(node.nodes), 3)
                    for node2 in node.nodes:
                        match node2.oldapListNodeId:
                            case "Node_DAA":
                                self.assertEqual(node2.leftIndex, 6)
                                self.assertEqual(node2.rightIndex, 7)
                            case "Node_DAB":
                                self.assertEqual(node2.leftIndex, 8)
                                self.assertEqual(node2.rightIndex, 9)
                            case "Node_DAC":
                                self.assertEqual(node2.leftIndex, 10)
                                self.assertEqual(node2.rightIndex, 11)
                            case _:
                                raise AssertionError("Unexpected node")
                case "Node_B":
                    self.assertEqual(node.leftIndex, 13)
                    self.assertEqual(node.rightIndex, 20)
                    self.assertEqual(len(node.nodes), 3)
                    for node2 in node.nodes:
                        match node2.oldapListNodeId:
                            case "Node_BA":
                                self.assertEqual(node2.leftIndex, 14)
                                self.assertEqual(node2.rightIndex, 15)
                            case "Node_BB":
                                self.assertEqual(node2.leftIndex, 16)
                                self.assertEqual(node2.rightIndex, 17)
                            case "Node_BC":
                                self.assertEqual(node2.leftIndex, 18)
                                self.assertEqual(node2.rightIndex, 19)
                            case _:
                                raise AssertionError("Unexpected node")
                case "Node_C":
                    self.assertEqual(node.leftIndex, 21)
                    self.assertEqual(node.rightIndex, 22)
                case "Node_D":
                    self.assertEqual(node.leftIndex, 23)
                    self.assertEqual(node.rightIndex, 24)
                case "Node_E":
                    self.assertEqual(node.leftIndex, 25)
                    self.assertEqual(node.rightIndex, 26)
                case _:
                    raise AssertionError("Unexpected node")

    def test_move_right_of_toL03(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveRightOfL03",
                              prefLabel="TestMoveRightOfRL03",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)

        olD = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_D")
        olD.insert_node_right_of(leftnode=olC)

        olD.move_node_right_of(con=self._connection, leftnode=olA)

        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveRightOfL03")
        nodes = oldaplist.nodes
        for node in nodes:
            match node.oldapListNodeId:
                case "Node_A":
                    self.assertEqual(node.leftIndex, 1)
                    self.assertEqual(node.rightIndex, 2)
                case "Node_D":
                    self.assertEqual(node.leftIndex, 3)
                    self.assertEqual(node.rightIndex, 4)
                case "Node_B":
                    self.assertEqual(node.leftIndex, 5)
                    self.assertEqual(node.rightIndex, 6)
                case "Node_C":
                    self.assertEqual(node.leftIndex, 7)
                    self.assertEqual(node.rightIndex, 8)


    def test_move_left_of_toR(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveLeftOf_toR",
                              prefLabel="TestMoveLeftOf_toR",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)

        olBB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BB")
        olBB.insert_node_right_of(leftnode=olBA)

        olBBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBA")
        olBBA.insert_node_below_of(parentnode=olBB)

        olBBB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBB")
        olBBB.insert_node_right_of(leftnode=olBBA)

        olBBC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BBC")
        olBBC.insert_node_right_of(leftnode=olBBB)

        olBC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BC")
        olBC.insert_node_right_of(leftnode=olBB)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)

        olD = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_D")
        olD.insert_node_right_of(leftnode=olC)

        olDA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_DA")
        olDA.insert_node_below_of(parentnode=olD)

        olBB.move_node_left_of(con=self._connection, rightnode=olD)

        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveLeftOf_toR")
        nodes = oldaplist.nodes
        for node in nodes:
            match node.oldapListNodeId:
                case "Node_A":
                    self.assertEqual(node.leftIndex, 1)
                    self.assertEqual(node.rightIndex, 2)
                case "Node_B":
                    self.assertEqual(node.leftIndex, 3)
                    self.assertEqual(node.rightIndex, 8)
                    self.assertEqual(len(node.nodes), 2)
                    for node2 in node.nodes:
                        match node2.oldapListNodeId:
                            case "Node_BA":
                                self.assertEqual(node2.leftIndex, 4)
                                self.assertEqual(node2.rightIndex, 5)
                            case "Node_BC":
                                self.assertEqual(node2.leftIndex, 6)
                                self.assertEqual(node2.rightIndex, 7)
                            case _:
                                raise AssertionError("Unexpected node")
                case "Node_C":
                    self.assertEqual(node.leftIndex, 9)
                    self.assertEqual(node.rightIndex, 10)
                case "Node_BB":
                    self.assertEqual(node.leftIndex, 11)
                    self.assertEqual(node.rightIndex, 18)
                    self.assertEqual(len(node.nodes), 3)
                    for node2 in node.nodes:
                        match node2.oldapListNodeId:
                            case "Node_BBA":
                                self.assertEqual(node2.leftIndex, 12)
                                self.assertEqual(node2.rightIndex, 13)
                            case "Node_BBB":
                                self.assertEqual(node2.leftIndex, 14)
                                self.assertEqual(node2.rightIndex, 15)
                            case "Node_BBC":
                                self.assertEqual(node2.leftIndex, 16)
                                self.assertEqual(node2.rightIndex, 17)
                            case _:
                                raise AssertionError("Unexpected node")
                case "Node_D":
                    self.assertEqual(node.leftIndex, 19)
                    self.assertEqual(node.rightIndex, 22)
                    self.assertEqual(len(node.nodes), 1)
                    self.assertEqual(node.nodes[0].oldapListNodeId, "Node_DA")
                    self.assertEqual(node.nodes[0].leftIndex, 20)
                    self.assertEqual(node.nodes[0].rightIndex, 21)
                case _:
                    raise AssertionError("Unexpected node")

    def test_move_left_of_toR02(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveLeftOf_toR02",
                              prefLabel="TestMoveLeftOf_toR02",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)

        olD = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_D")
        olD.insert_node_right_of(leftnode=olC)

        olA.move_node_left_of(con=self._connection, rightnode=olD)

        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveLeftOf_toR02")
        nodes = oldaplist.nodes
        for node in nodes:
            match node.oldapListNodeId:
                case "Node_B":
                    self.assertEqual(node.leftIndex, 1)
                    self.assertEqual(node.rightIndex, 2)
                case "Node_C":
                    self.assertEqual(node.leftIndex, 3)
                    self.assertEqual(node.rightIndex, 4)
                case "Node_A":
                    self.assertEqual(node.leftIndex, 5)
                    self.assertEqual(node.rightIndex, 6)
                case "Node_D":
                    self.assertEqual(node.leftIndex, 7)
                    self.assertEqual(node.rightIndex, 8)


    def test_move_left_of_toL01(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveLeftOf_toL01",
                              prefLabel="TestMoveLeftOf_toL01",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_AA")
        olAA.insert_node_below_of(parentnode=olA)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)

        olD = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_D")
        olD.insert_node_right_of(leftnode=olC)

        olDA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_DA")
        olDA.insert_node_below_of(parentnode=olD)

        olDAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_DAA")
        olDAA.insert_node_below_of(parentnode=olDA)

        olDAB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_DAB")
        olDAB.insert_node_right_of(leftnode=olDAA)

        olE = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_E")
        olE.insert_node_right_of(leftnode=olD)

        olEA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_EA")
        olEA.insert_node_below_of(parentnode=olE)

        olDA.move_node_left_of(con=self._connection, rightnode=olB)

        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveLeftOf_toL01")
        nodes = oldaplist.nodes

        for node in nodes:
            match node.oldapListNodeId:
                case "Node_A":
                    self.assertEqual(node.leftIndex, 1)
                    self.assertEqual(node.rightIndex, 4)
                    self.assertEqual(len(node.nodes), 1)
                    self.assertEqual(node.nodes[0].oldapListNodeId, "Node_AA")
                    self.assertEqual(node.nodes[0].leftIndex, 2)
                    self.assertEqual(node.nodes[0].rightIndex, 3)
                case "Node_DA":
                    self.assertEqual(node.leftIndex, 5)
                    self.assertEqual(node.rightIndex, 10)
                    self.assertEqual(len(node.nodes), 2)
                    for node2 in node.nodes:
                        match node2.oldapListNodeId:
                            case "Node_DAA":
                                self.assertEqual(node2.leftIndex, 6)
                                self.assertEqual(node2.rightIndex, 7)
                            case "Node_DAB":
                                self.assertEqual(node2.leftIndex, 8)
                                self.assertEqual(node2.rightIndex, 9)
                            case _:
                                raise AssertionError("Unexpected node")
                case "Node_B":
                    self.assertEqual(node.leftIndex, 11)
                    self.assertEqual(node.rightIndex, 14)
                    self.assertEqual(len(node.nodes), 1)
                    self.assertEqual(node.nodes[0].oldapListNodeId, "Node_BA")
                    self.assertEqual(node.nodes[0].leftIndex, 12)
                    self.assertEqual(node.nodes[0].rightIndex, 13)
                case "Node_C":
                    self.assertEqual(node.leftIndex, 15)
                    self.assertEqual(node.rightIndex, 16)
                case "Node_D":
                    self.assertEqual(node.leftIndex, 17)
                    self.assertEqual(node.rightIndex, 18)
                case "Node_E":
                    self.assertEqual(node.leftIndex, 19)
                    self.assertEqual(node.rightIndex, 22)
                    self.assertEqual(len(node.nodes), 1)
                    self.assertEqual(node.nodes[0].oldapListNodeId, "Node_EA")
                    self.assertEqual(node.nodes[0].leftIndex, 20)
                    self.assertEqual(node.nodes[0].rightIndex, 21)
                case _:
                    raise AssertionError("Unexpected node")

    def test_move_left_of_toL03(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestMoveLeftOf_toL02",
                              prefLabel="TestMoveLeftOf_toL02",
                              definition="A list for testing...")
        oldaplist.create()

        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A")
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)

        olD = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_D")
        olD.insert_node_right_of(leftnode=olC)

        olD.move_node_left_of(con=self._connection, rightnode=olA)

        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestMoveLeftOf_toL02")
        nodes = oldaplist.nodes
        for node in nodes:
            match node.oldapListNodeId:
                case "Node_D":
                    self.assertEqual(node.leftIndex, 1)
                    self.assertEqual(node.rightIndex, 2)
                case "Node_A":
                    self.assertEqual(node.leftIndex, 3)
                    self.assertEqual(node.rightIndex, 4)
                case "Node_B":
                    self.assertEqual(node.leftIndex, 5)
                    self.assertEqual(node.rightIndex, 6)
                case "Node_C":
                    self.assertEqual(node.leftIndex, 7)
                    self.assertEqual(node.rightIndex, 8)
                case _:
                    raise AssertionError("Unexpected node")

    def test_search(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListY",
                              prefLabel="TestListY",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListY")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A",
                            prefLabel=LangString("Node_A@en", "Neud_A@fr"),
                            definition=LangString("A node for testing A@en", "Eine Liste zum Testen A@de"))
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B",
                            prefLabel=LangString("Node_B@en", "Neud_A@fr"),
                            definition=LangString("A node for testing B@en", "Eine Liste zum Testen B@de"))
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C",
                            prefLabel=LangString("Node_C@en", "Neud_C@fr"),
                            definition=LangString("A node for testing C@en", "Eine Liste zum Testen C@de"))
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA",
                            prefLabel=LangString("Node_BA@en", "Neud_BA@fr"),
                            definition=LangString("A node for testing BA@en", "Eine Liste zum Testen BA@de"))
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olBAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BAA",
                            prefLabel=LangString("Node_BAA@en", "Neud_BAA@fr"),
                            definition=LangString("A node for testing BAA@en", "Eine Liste zum Testen BAA@de"))
        olBAA.insert_node_below_of(parentnode=olBA)
        self.assertEqual(Xsd_integer(5), olBAA.leftIndex)
        self.assertEqual(Xsd_integer(6), olBAA.rightIndex)

        olBAB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BAB",
                            prefLabel=LangString("Node_BAB@en", "Neud_BAB@fr"),
                            definition=LangString("A node for testing BAB@en", "Eine Liste zum Testen BAB@de"))
        olBAB.insert_node_right_of(leftnode=olBAA)
        self.assertEqual(Xsd_integer(7), olBAB.leftIndex)
        self.assertEqual(Xsd_integer(8), olBAB.rightIndex)

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, id="Node_BA", exactMatch=True)
        self.assertEqual([Xsd_QName("L-TestListY:Node_BA")], irilist)

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, id="Node_XX", exactMatch=True)
        self.assertEqual([], irilist)

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, id="BA")
        self.assertTrue(Xsd_QName("L-TestListY:Node_BA") in irilist)
        self.assertTrue(Xsd_QName("L-TestListY:Node_BAA") in irilist)
        self.assertTrue(Xsd_QName("L-TestListY:Node_BAB") in irilist)

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, prefLabel="BA@en")
        self.assertTrue(Xsd_QName("L-TestListY:Node_BA") in irilist)
        self.assertTrue(Xsd_QName("L-TestListY:Node_BAA") in irilist)
        self.assertTrue(Xsd_QName("L-TestListY:Node_BAB") in irilist)

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, prefLabel="BA@zu")
        self.assertEqual([], irilist)

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, prefLabel="Neud_BA@fr", exactMatch=True)
        self.assertEqual([Xsd_QName("L-TestListY:Node_BA")], irilist)

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, prefLabel="BA@en")
        self.assertTrue(Xsd_QName("L-TestListY:Node_BA") in irilist)
        self.assertTrue(Xsd_QName("L-TestListY:Node_BAA") in irilist)
        self.assertTrue(Xsd_QName("L-TestListY:Node_BAB") in irilist)

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, prefLabel="XX")
        self.assertEqual([], irilist)

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, prefLabel="Neud_BA", exactMatch=True)
        self.assertEqual([Xsd_QName("L-TestListY:Node_BA")], irilist)

        ##

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, definition="BA@en")
        self.assertTrue(Xsd_QName("L-TestListY:Node_BA") in irilist)
        self.assertTrue(Xsd_QName("L-TestListY:Node_BAA") in irilist)
        self.assertTrue(Xsd_QName("L-TestListY:Node_BAB") in irilist)

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, definition="BA@zu")
        self.assertEqual([], irilist)

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, definition="Eine Liste zum Testen BA@de", exactMatch=True)
        self.assertEqual([Xsd_QName("L-TestListY:Node_BA")], irilist)

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, definition="BA@en")
        self.assertTrue(Xsd_QName("L-TestListY:Node_BA") in irilist)
        self.assertTrue(Xsd_QName("L-TestListY:Node_BAA") in irilist)
        self.assertTrue(Xsd_QName("L-TestListY:Node_BAB") in irilist)

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, definition="XX")
        self.assertEqual([], irilist)

        irilist = OldapListNode.search(con=self._connection, **oldaplist.info, definition="Eine Liste zum Testen BA", exactMatch=True)
        self.assertEqual([Xsd_QName("L-TestListY:Node_BA")], irilist)

    def test_invalid_move_A(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListZ",
                              prefLabel="TestListZ",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListZ")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A",
                            prefLabel=LangString("Node_A@en", "Neud_A@fr"),
                            definition=LangString("A node for testing A@en", "Eine Liste zum Testen A@de"))
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B",
                            prefLabel=LangString("Node_B@en", "Neud_A@fr"),
                            definition=LangString("A node for testing B@en", "Eine Liste zum Testen B@de"))
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C",
                            prefLabel=LangString("Node_C@en", "Neud_C@fr"),
                            definition=LangString("A node for testing C@en", "Eine Liste zum Testen C@de"))
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA",
                            prefLabel=LangString("Node_BA@en", "Neud_BA@fr"),
                            definition=LangString("A node for testing BA@en", "Eine Liste zum Testen BA@de"))
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olBAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BAA",
                            prefLabel=LangString("Node_BAA@en", "Neud_BAA@fr"),
                            definition=LangString("A node for testing BAA@en", "Eine Liste zum Testen BAA@de"))
        olBAA.insert_node_below_of(parentnode=olBA)
        self.assertEqual(Xsd_integer(5), olBAA.leftIndex)
        self.assertEqual(Xsd_integer(6), olBAA.rightIndex)

        olBAB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BAB",
                            prefLabel=LangString("Node_BAB@en", "Neud_BAB@fr"),
                            definition=LangString("A node for testing BAB@en", "Eine Liste zum Testen BAB@de"))
        olBAB.insert_node_right_of(leftnode=olBAA)

        with self.assertRaises(OldapErrorInconsistency):
            olB.move_node_below(con=self._connection, target=olBAB)

    def test_invalid_move_B(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListAlpha",
                              prefLabel="TestListAlpha",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListAlpha")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A",
                            prefLabel=LangString("Node_A@en", "Neud_A@fr"),
                            definition=LangString("A node for testing A@en", "Eine Liste zum Testen A@de"))
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B",
                            prefLabel=LangString("Node_B@en", "Neud_A@fr"),
                            definition=LangString("A node for testing B@en", "Eine Liste zum Testen B@de"))
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C",
                            prefLabel=LangString("Node_C@en", "Neud_C@fr"),
                            definition=LangString("A node for testing C@en", "Eine Liste zum Testen C@de"))
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA",
                            prefLabel=LangString("Node_BA@en", "Neud_BA@fr"),
                            definition=LangString("A node for testing BA@en", "Eine Liste zum Testen BA@de"))
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olBAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BAA",
                            prefLabel=LangString("Node_BAA@en", "Neud_BAA@fr"),
                            definition=LangString("A node for testing BAA@en", "Eine Liste zum Testen BAA@de"))
        olBAA.insert_node_below_of(parentnode=olBA)
        self.assertEqual(Xsd_integer(5), olBAA.leftIndex)
        self.assertEqual(Xsd_integer(6), olBAA.rightIndex)

        olBAB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BAB",
                            prefLabel=LangString("Node_BAB@en", "Neud_BAB@fr"),
                            definition=LangString("A node for testing BAB@en", "Eine Liste zum Testen BAB@de"))
        olBAB.insert_node_right_of(leftnode=olBAA)

        with self.assertRaises(OldapErrorInconsistency):
            olBA.move_node_left_of(con=self._connection, rightnode=olBAB)

    def test_invalid_move_C(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListBeta",
                              prefLabel="TestListBeta",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListBeta")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A",
                            prefLabel=LangString("Node_A@en", "Neud_A@fr"),
                            definition=LangString("A node for testing A@en", "Eine Liste zum Testen A@de"))
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B",
                            prefLabel=LangString("Node_B@en", "Neud_A@fr"),
                            definition=LangString("A node for testing B@en", "Eine Liste zum Testen B@de"))
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C",
                            prefLabel=LangString("Node_C@en", "Neud_C@fr"),
                            definition=LangString("A node for testing C@en", "Eine Liste zum Testen C@de"))
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BA",
                            prefLabel=LangString("Node_BA@en", "Neud_BA@fr"),
                            definition=LangString("A node for testing BA@en", "Eine Liste zum Testen BA@de"))
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olBAA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BAA",
                            prefLabel=LangString("Node_BAA@en", "Neud_BAA@fr"),
                            definition=LangString("A node for testing BAA@en", "Eine Liste zum Testen BAA@de"))
        olBAA.insert_node_below_of(parentnode=olBA)
        self.assertEqual(Xsd_integer(5), olBAA.leftIndex)
        self.assertEqual(Xsd_integer(6), olBAA.rightIndex)

        olBAB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BAB",
                            prefLabel=LangString("Node_BAB@en", "Neud_BAB@fr"),
                            definition=LangString("A node for testing BAB@en", "Eine Liste zum Testen BAB@de"))
        olBAB.insert_node_right_of(leftnode=olBAA)

        with self.assertRaises(OldapErrorInconsistency):
            olBA.move_node_right_of(con=self._connection, leftnode=olBAB)

    def test_list_node_instances(self):
        project = Project.read(con=self._connection, projectIri_SName="test")

        oldaplist = OldapList(con=self._connection,
                              project=project,
                              oldapListId="TestNodeInstances",
                              prefLabel="TestNodeInstances",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestNodeInstances")
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A",
                            prefLabel=LangString("Node_A@en", "Neud_A@fr"),
                            definition=LangString("A node for testing A@en", "Eine Liste zum Testen A@de"))
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_B",
                            prefLabel=LangString("Node_B@en", "Neud_A@fr"),
                            definition=LangString("A node for testing B@en", "Eine Liste zum Testen B@de"))
        olB.insert_node_right_of(leftnode=olA)

        olC = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_C",
                            prefLabel=LangString("Node_C@en", "Neud_C@fr"),
                            definition=LangString("A node for testing C@en", "Eine Liste zum Testen C@de"))
        olC.insert_node_right_of(leftnode=olB)

        dm_name = project.projectShortName

        title = PropertyClass(con=self._connection,
                              project=project,
                              property_class_iri=Xsd_QName(f'{dm_name}:title'),
                              datatype=XsdDatatypes.langString,
                              name=LangString(["Title@en", "Titel@de"]),
                              description=LangString(["Title of book@en", "Titel des Buches@de"]),
                              uniqueLang=Xsd_boolean(True),
                              languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        category = PropertyClass(con=self._connection,
                                 project=project,
                                 property_class_iri=Xsd_QName(f'{dm_name}:category'),
                                 toClass=oldaplist.node_classIri,
                                 name=LangString(["Category@en", "Kategorie@de"]),
                                 description=LangString(["Category@en", "Kategorie@de"]))

        categoryitem = ResourceClass(con=self._connection,
                                     project=project,
                                     owlclass_iri=Xsd_QName(f'{dm_name}:CategoryItem'),
                                     label=LangString(["CategoryItem@en", "CategoryItem@de"]),
                                     comment=LangString("Something with categories@en"),
                                     closed=Xsd_boolean(True),
                                     hasproperties=[
                                         HasProperty(con=self._connection, project=project, prop=title, minCount=Xsd_integer(1),
                                                     order=1),
                                         HasProperty(con=self._connection, project=project, prop=category, minCount=Xsd_integer(1),
                                                     order=2)])
        #dm = DataModel(con=self._connection, project=project, resclasses=[categoryitem])
        #dm.create()

        dm = DataModel.read(con=self._connection, project=project)
        dm[Xsd_QName(f'{dm_name}:CategoryItem')] = categoryitem
        dm.update()

        factory = ResourceInstanceFactory(con=self._connection, project=project)
        CategoryItem = factory.createObjectInstance("CategoryItem")

        citem1 = CategoryItem(title="Item1@en",
                              category=olA.iri,
                              grantsPermission=Iri('oldap:GenericView'))
        citem1.create()

        testitem = CategoryItem.read(con=self._connection,
                                     iri=citem1.iri)
        self.assertEqual(testitem.title, LangString("Item1@en"))
        self.assertEqual(testitem.category, {olA.iri})


if __name__ == '__main__':
    unittest.main()
