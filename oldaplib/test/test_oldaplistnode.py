import json
import unittest
from pathlib import Path
from pprint import pprint
from time import sleep

from oldaplib.src.helpers.json_encoder import SpecialEncoder
from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.language import Language
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapErrorInconsistency
from oldaplib.src.iconnection import IConnection
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplistnode import OldapListNode
from oldaplib.src.oldaplist_helpers import get_nodes_from_list, print_sublist, get_list
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_integer import Xsd_integer
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
        super().setUpClass()
        project_root = find_project_root(__file__)

        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://testing.org/datatypes#")
        cls._context.use('test')
        cls._connection = Connection(server='http://localhost:7200',
                                     repo="oldap",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._connection.clear_graph(Xsd_QName('oldap:admin'))
        file = project_root / 'oldaplib' / 'ontologies' / 'admin.trig'
        cls._connection.upload_turtle(file)


        cls._connection.clear_graph(Xsd_QName('test:test'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:lists'))
        cls._connection.clear_graph(Xsd_QName('test:data'))
        file = project_root / 'oldaplib' / 'testdata' / 'connection_test.trig'
        cls._connection.upload_turtle(file)
        sleep(1)
        cls._project = Project.read(cls._connection, "test")
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
                            oldapList=oldaplist,
                            oldapListNodeId="Node_A",
                            prefLabel="Node_A",
                            definition="First node")
        oln.create_root_node()

        oln = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual("Node_A", oln.oldapListNodeId)
        self.assertEqual(LangString("Node_A"), oln.prefLabel)
        self.assertEqual(LangString("First node@en"), oln.definition)
        self.assertEqual(Xsd_integer(1), oln.leftIndex)
        self.assertEqual(Xsd_integer(2), oln.rightIndex)

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
                            oldapList=oldaplist,
                            oldapListNodeId="Node_A",
                            prefLabel="Node_A",
                            definition="First node")
        oln.create_root_node()
        oln = OldapListNode.read(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        oln.prefLabel = LangString("First Node")
        oln.definition = LangString("Erster Knoten@de")
        oln.update()
        oln = OldapListNode.read(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        self.assertEqual(oln.oldapListNodeId, "Node_A")
        self.assertEqual(oln.prefLabel, LangString("First Node@en"))
        self.assertEqual(oln.definition, LangString("Erster Knoten@de"))

        oln.prefLabel[Language.DE] = "Erster Knoten"
        oln.definition[Language.EN] = "First Node"
        oln.update()

        oln = OldapListNode.read(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        self.assertEqual(oln.prefLabel, LangString("First Node@en", "Erster Knoten@de"))
        self.assertEqual(oln.definition, LangString("Erster Knoten@de", "First Node@en"))

        del oln.prefLabel[Language.EN]
        del oln.definition
        oln.update()
        self.assertEqual(oln.prefLabel, LangString("Erster Knoten@de"))
        self.assertIsNone(oln.definition)

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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olC.leftIndex)
        self.assertEqual(Xsd_integer(4), olC.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.create_root_node()
        self.assertEqual(Xsd_integer(1), olB.leftIndex)
        self.assertEqual(Xsd_integer(2), olB.rightIndex)

        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.insert_node_left_of(rightnode=olB)
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olC.leftIndex)
        self.assertEqual(Xsd_integer(4), olC.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_left_of(rightnode=olC)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olAA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_AA")
        olAA.insert_node_below_of(parentnode=olA)
        self.assertEqual(Xsd_integer(2), olAA.leftIndex)
        self.assertEqual(Xsd_integer(3), olAA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(4), olA.rightIndex)

        olAA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_AA")
        self.assertEqual(Xsd_integer(2), olAA.leftIndex)
        self.assertEqual(Xsd_integer(3), olAA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(5), olB.leftIndex)
        self.assertEqual(Xsd_integer(6), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(6), olB.rightIndex)

        olBA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_BA")
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olCA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_CA")
        olCA.insert_node_below_of(parentnode=olC)
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(7), olCA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(8), olC.rightIndex)

        olCA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olAB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_AB")
        olAB.insert_node_below_of(parentnode=olA)
        self.assertEqual(Xsd_integer(2), olAB.leftIndex)
        self.assertEqual(Xsd_integer(3), olAB.rightIndex)

        olAA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_AA")
        olAA.insert_node_left_of(olAB)
        self.assertEqual(Xsd_integer(2), olAB.leftIndex)
        self.assertEqual(Xsd_integer(3), olAB.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(6), olA.rightIndex)

        olAA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_AA")
        self.assertEqual(Xsd_integer(2), olAA.leftIndex)
        self.assertEqual(Xsd_integer(3), olAA.rightIndex)

        olAB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_AB")
        self.assertEqual(Xsd_integer(4), olAB.leftIndex)
        self.assertEqual(Xsd_integer(5), olAB.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(7), olB.leftIndex)
        self.assertEqual(Xsd_integer(8), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_BB")
        olBB.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBB.leftIndex)
        self.assertEqual(Xsd_integer(5), olBB.rightIndex)

        olBA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_BA")
        olBA.insert_node_left_of(rightnode=olBB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(8), olB.rightIndex)

        olBA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_BA")
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olBB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_BB")
        self.assertEqual(Xsd_integer(6), olBB.leftIndex)
        self.assertEqual(Xsd_integer(7), olBB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olCB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_CB")
        olCB.insert_node_below_of(parentnode=olC)
        self.assertEqual(Xsd_integer(6), olCB.leftIndex)
        self.assertEqual(Xsd_integer(7), olCB.rightIndex)

        olCA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_CA")
        olCA.insert_node_left_of(rightnode=olCB)
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(7), olCA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(10), olC.rightIndex)

        olCA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_CA")
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(7), olCA.rightIndex)

        olCB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olAA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_AA")
        olAA.insert_node_below_of(parentnode=olA)
        self.assertEqual(Xsd_integer(2), olAA.leftIndex)
        self.assertEqual(Xsd_integer(3), olAA.rightIndex)

        olAB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_AB")
        olAB.insert_node_right_of(leftnode=olAA)
        self.assertEqual(Xsd_integer(4), olAB.leftIndex)
        self.assertEqual(Xsd_integer(5), olAB.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(6), olA.rightIndex)

        olAA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_AA")
        self.assertEqual(Xsd_integer(2), olAA.leftIndex)
        self.assertEqual(Xsd_integer(3), olAA.rightIndex)

        olAB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_AB")
        self.assertEqual(Xsd_integer(4), olAB.leftIndex)
        self.assertEqual(Xsd_integer(5), olAB.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(7), olB.leftIndex)
        self.assertEqual(Xsd_integer(8), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olBB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_BB")
        olBB.insert_node_right_of(leftnode=olBA)
        self.assertEqual(Xsd_integer(6), olBB.leftIndex)
        self.assertEqual(Xsd_integer(7), olBB.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(8), olB.rightIndex)

        olBA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_BA")
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olBB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_BB")
        self.assertEqual(Xsd_integer(6), olBB.leftIndex)
        self.assertEqual(Xsd_integer(7), olBB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olCA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_CA")
        olCA.insert_node_below_of(parentnode=olC)
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(7), olCA.rightIndex)

        olCB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_CB")
        olCB.insert_node_right_of(leftnode=olCA)
        self.assertEqual(Xsd_integer(8), olCB.leftIndex)
        self.assertEqual(Xsd_integer(9), olCB.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(10), olC.rightIndex)

        olCA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_CA")
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(7), olCA.rightIndex)

        olCB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olAA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_AA")
        olAA.insert_node_below_of(parentnode=olA)
        self.assertEqual(Xsd_integer(2), olAA.leftIndex)
        self.assertEqual(Xsd_integer(3), olAA.rightIndex)

        olAAA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_AAA")
        olAAA.insert_node_below_of(parentnode=olAA)
        self.assertEqual(Xsd_integer(3), olAAA.leftIndex)
        self.assertEqual(Xsd_integer(4), olAAA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(6), olA.rightIndex)

        olAA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_AA")
        self.assertEqual(Xsd_integer(2), olAA.leftIndex)
        self.assertEqual(Xsd_integer(5), olAA.rightIndex)

        olAAA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_AAA")
        self.assertEqual(Xsd_integer(3), olAAA.leftIndex)
        self.assertEqual(Xsd_integer(4), olAAA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(7), olB.leftIndex)
        self.assertEqual(Xsd_integer(8), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olBAA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_BAA")
        olBAA.insert_node_below_of(parentnode=olBA)
        self.assertEqual(Xsd_integer(5), olBAA.leftIndex)
        self.assertEqual(Xsd_integer(6), olBAA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(8), olB.rightIndex)

        olBA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_BA")
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(7), olBA.rightIndex)

        olBAA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_BAA")
        self.assertEqual(Xsd_integer(5), olBAA.leftIndex)
        self.assertEqual(Xsd_integer(6), olBAA.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olCA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_CA")
        olCA.insert_node_below_of(parentnode=olC)
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(7), olCA.rightIndex)

        olCAA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_CAA")
        olCAA.insert_node_below_of(parentnode=olCA)
        self.assertEqual(Xsd_integer(7), olCAA.leftIndex)
        self.assertEqual(Xsd_integer(8), olCAA.rightIndex)

        #
        # Now reread the nodes and check
        #
        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_C")
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(10), olC.rightIndex)

        olCA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_CA")
        self.assertEqual(Xsd_integer(6), olCA.leftIndex)
        self.assertEqual(Xsd_integer(9), olCA.rightIndex)

        olCAA = OldapListNode.read(con=self._connection,
                                   oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        olA.delete_node()

        del olA

        with self.assertRaises(OldapErrorNotFound):
            olA = OldapListNode.read(con=self._connection,
                                     oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olC.leftIndex)
        self.assertEqual(Xsd_integer(4), olC.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olA.delete_node()
        with self.assertRaises(OldapErrorNotFound):
            olA = OldapListNode.read(con=self._connection,
                                     oldapList=oldaplist,
                                     oldapListNodeId="Node_A")

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(1), olB.leftIndex)
        self.assertEqual(Xsd_integer(2), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olC.leftIndex)
        self.assertEqual(Xsd_integer(4), olC.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olB.delete_node()
        with self.assertRaises(OldapErrorNotFound):
            olB = OldapListNode.read(con=self._connection,
                                     oldapList=oldaplist,
                                     oldapListNodeId="Node_B")

        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olC.leftIndex)
        self.assertEqual(Xsd_integer(4), olC.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC.delete_node()
        with self.assertRaises(OldapErrorNotFound):
            olC = OldapListNode.read(con=self._connection,
                                     oldapList=oldaplist,
                                     oldapListNodeId="Node_C")

        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olA.delete_node()
        with self.assertRaises(OldapErrorNotFound):
            olA = OldapListNode.read(con=self._connection,
                                     oldapList=oldaplist,
                                     oldapListNodeId="Node_A")

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(1), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olBA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_BA")
        self.assertEqual(Xsd_integer(2), olBA.leftIndex)
        self.assertEqual(Xsd_integer(3), olBA.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        with self.assertRaises(OldapErrorInconsistency):
            olB.delete_node()

        olBA.delete_node()
        with self.assertRaises(OldapErrorNotFound):
            olBA = OldapListNode.read(con=self._connection,
                                     oldapList=oldaplist,
                                     oldapListNodeId="Node_BA")

        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A")
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B")
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C")
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_BA")
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)


        olC.delete_node()
        with self.assertRaises(OldapErrorNotFound):
            olC = OldapListNode.read(con=self._connection,
                                     oldapList=oldaplist,
                                     oldapListNodeId="Node_C")

        olA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_A")
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_B")
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(6), olB.rightIndex)

        olBA = OldapListNode.read(con=self._connection,
                                 oldapList=oldaplist,
                                 oldapListNodeId="Node_BA")
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A",
                            prefLabel=LangString("Node_A@en", "Neud_A@fr"),
                            definition=LangString("A node for testing A@en", "Eine Liste zum Testen A@de"))
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B",
                            prefLabel=LangString("Node_B@en", "Neud_A@fr"),
                            definition=LangString("A node for testing B@en", "Eine Liste zum Testen B@de"))
        olB.insert_node_right_of(leftnode=olA)
        self.assertEqual(Xsd_integer(3), olB.leftIndex)
        self.assertEqual(Xsd_integer(4), olB.rightIndex)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C",
                            prefLabel=LangString("Node_C@en", "Neud_C@fr"),
                            definition=LangString("A node for testing C@en", "Eine Liste zum Testen C@de"))
        olC.insert_node_right_of(leftnode=olB)
        self.assertEqual(Xsd_integer(5), olC.leftIndex)
        self.assertEqual(Xsd_integer(6), olC.rightIndex)

        olBA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_BA",
                            prefLabel=LangString("Node_BA@en", "Neud_BA@fr"),
                            definition=LangString("A node for testing BA@en", "Eine Liste zum Testen BA@de"))
        olBA.insert_node_below_of(parentnode=olB)
        self.assertEqual(Xsd_integer(4), olBA.leftIndex)
        self.assertEqual(Xsd_integer(5), olBA.rightIndex)

        olBAA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_BAA",
                            prefLabel=LangString("Node_BAA@en", "Neud_BAA@fr"),
                            definition=LangString("A node for testing BAA@en", "Eine Liste zum Testen BAA@de"))
        olBAA.insert_node_below_of(parentnode=olBA)
        self.assertEqual(Xsd_integer(5), olBAA.leftIndex)
        self.assertEqual(Xsd_integer(6), olBAA.rightIndex)

        olBAB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_BAB",
                            prefLabel=LangString("Node_BAB@en", "Neud_BAB@fr"),
                            definition=LangString("A node for testing BAB@en", "Eine Liste zum Testen BAB@de"))
        olBAB.insert_node_right_of(leftnode=olBAA)
        self.assertEqual(Xsd_integer(7), olBAB.leftIndex)
        self.assertEqual(Xsd_integer(8), olBAB.rightIndex)

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, id="Node_BA", exactMatch=True)
        self.assertEqual([Iri("L-TestListY:Node_BA")], irilist)

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, id="Node_XX", exactMatch=True)
        self.assertEqual([], irilist)

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, id="BA")
        self.assertTrue(Iri("L-TestListY:Node_BA") in irilist)
        self.assertTrue(Iri("L-TestListY:Node_BAA") in irilist)
        self.assertTrue(Iri("L-TestListY:Node_BAB") in irilist)

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, prefLabel="BA@en")
        self.assertTrue(Iri("L-TestListY:Node_BA") in irilist)
        self.assertTrue(Iri("L-TestListY:Node_BAA") in irilist)
        self.assertTrue(Iri("L-TestListY:Node_BAB") in irilist)

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, prefLabel="BA@zu")
        self.assertEqual([], irilist)

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, prefLabel="Neud_BA@fr", exactMatch=True)
        self.assertEqual([Iri("L-TestListY:Node_BA")], irilist)

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, prefLabel="BA@en")
        self.assertTrue(Iri("L-TestListY:Node_BA") in irilist)
        self.assertTrue(Iri("L-TestListY:Node_BAA") in irilist)
        self.assertTrue(Iri("L-TestListY:Node_BAB") in irilist)

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, prefLabel="XX")
        self.assertEqual([], irilist)

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, prefLabel="Neud_BA", exactMatch=True)
        self.assertEqual([Iri("L-TestListY:Node_BA")], irilist)

        ##

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, definition="BA@en")
        self.assertTrue(Iri("L-TestListY:Node_BA") in irilist)
        self.assertTrue(Iri("L-TestListY:Node_BAA") in irilist)
        self.assertTrue(Iri("L-TestListY:Node_BAB") in irilist)

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, definition="BA@zu")
        self.assertEqual([], irilist)

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, definition="Eine Liste zum Testen BA@de", exactMatch=True)
        self.assertEqual([Iri("L-TestListY:Node_BA")], irilist)

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, definition="BA@en")
        self.assertTrue(Iri("L-TestListY:Node_BA") in irilist)
        self.assertTrue(Iri("L-TestListY:Node_BAA") in irilist)
        self.assertTrue(Iri("L-TestListY:Node_BAB") in irilist)

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, definition="XX")
        self.assertEqual([], irilist)

        irilist = OldapListNode.search(con=self._connection, oldapList=oldaplist, definition="Eine Liste zum Testen BA", exactMatch=True)
        self.assertEqual([Iri("L-TestListY:Node_BA")], irilist)

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
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A",
                            prefLabel=LangString("Node_A@en", "Neud_A@fr"),
                            definition=LangString("A node for testing A@en", "Eine Liste zum Testen A@de"))
        olA.create_root_node()

        olB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_B",
                            prefLabel=LangString("Node_B@en", "Neud_A@fr"),
                            definition=LangString("A node for testing B@en", "Eine Liste zum Testen B@de"))
        olB.insert_node_right_of(leftnode=olA)

        olC = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_C",
                            prefLabel=LangString("Node_C@en", "Neud_C@fr"),
                            definition=LangString("A node for testing C@en", "Eine Liste zum Testen C@de"))
        olC.insert_node_right_of(leftnode=olB)

        dm_name = project.projectShortName

        title = PropertyClass(con=self._connection,
                              project=project,
                              property_class_iri=Iri(f'{dm_name}:title'),
                              datatype=XsdDatatypes.langString,
                              name=LangString(["Title@en", "Titel@de"]),
                              description=LangString(["Title of book@en", "Titel des Buches@de"]),
                              uniqueLang=Xsd_boolean(True),
                              languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        category = PropertyClass(con=self._connection,
                                project=project,
                                property_class_iri=Iri(f'{dm_name}:category'),
                                toClass=oldaplist.node_class_iri,
                                name=LangString(["Category@en", "Kategorie@de"]),
                                description=LangString(["Category@en", "Kategorie@de"]))

        categoryitem = ResourceClass(con=self._connection,
                                     project=project,
                                     owlclass_iri=Iri(f'{dm_name}:CategoryItem'),
                                     label=LangString(["CategoryItem@en", "CategoryItem@de"]),
                                     comment=LangString("Something with categories@en"),
                                     closed=Xsd_boolean(True),
                                     hasproperties=[
                                         HasProperty(con=self._connection, prop=title, minCount=Xsd_integer(1),
                                                     order=1),
                                         HasProperty(con=self._connection, prop=category, minCount=Xsd_integer(1),
                                                     order=2)])
        dm = DataModel(con=self._connection,
                       project=project,
                       resclasses=[categoryitem])
        dm.create()

        factory = ResourceInstanceFactory(con=self._connection, project=project)
        CategoryItem = factory.createObjectInstance("CategoryItem")

        citem1 = CategoryItem(title="Item1@en",
                              category=olA.iri,
                              grantsPermission=Iri('oldap:GenericView'))
        citem1.create()

        testitem = CategoryItem.read(con=self._connection,
                                     project=project,
                                     iri=citem1.iri)
        self.assertEqual(testitem.title, LangString("Item1@en"))
        self.assertEqual(testitem.category, {olA.iri})


if __name__ == '__main__':
    unittest.main()
