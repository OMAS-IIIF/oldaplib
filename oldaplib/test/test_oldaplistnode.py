import unittest
from pathlib import Path
from time import sleep

from oldaplib.src.connection import Connection
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.language import Language
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.iconnection import IConnection
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplistnode import OldapListNode
from oldaplib.src.project import Project
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


if __name__ == '__main__':
    unittest.main()
