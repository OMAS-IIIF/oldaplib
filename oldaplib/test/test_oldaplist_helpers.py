import json
import unittest
from pathlib import Path
from pprint import pprint
from time import sleep

from oldaplib.src.connection import Connection
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.language import Language
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.iconnection import IConnection
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplist_helpers import get_nodes_from_list, print_sublist, get_list
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

class OldapListHelperTestCase(unittest.TestCase):

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
        cls._connection.clear_graph(Xsd_QName('hyha:onto'))
        cls._connection.clear_graph(Xsd_QName('hyha:shacl'))
        cls._connection.clear_graph(Xsd_QName('hyha:lists'))
        cls._connection.clear_graph(Xsd_QName('hyha:data'))
        file = project_root / 'oldaplib' / 'testdata' / 'connection_test.trig'
        cls._connection.upload_turtle(file)
        sleep(1)
        cls._project = Project.read(cls._connection, "test")
        LangString.defaultLanguage = Language.EN


    @classmethod
    def tearDownClass(cls):
        pass

    def test_get_all_nodes_A(self):
        oldaplist = OldapList(con=self._connection,
                              project="hyha",
                              oldapListId="TestList_HYHA",
                              prefLabel="TestList_HYHA-label",
                              definition="TestList_HYHA-definition")
        oldaplist.create()

        olA = OldapListNode(con=self._connection,
                            oldapList=oldaplist,
                            oldapListNodeId="Node_A",
                            prefLabel=["GUGUSELI@en", "HIHIHI@de"])
        olA.create_root_node()

        full_list = get_list(con=self._connection, project="hyha", oldapListId="TestList_HYHA")
        full_list_obj = json.loads(full_list)
        self.assertEqual(full_list_obj['oldapListId'], 'TestList_HYHA')
        self.assertEqual(full_list_obj['prefLabel'], ['TestList_HYHA-label@en'])
        self.assertIsNotNone(full_list_obj['nodes'])
        self.assertIsInstance(full_list_obj['nodes'], list)

        sorted_nodes = sorted(full_list_obj['nodes'], key=lambda node: node['oldapListNodeId'])
        self.assertEqual(sorted_nodes[0]['oldapListNodeId'], 'Node_A')
        self.assertEqual(sorted_nodes[0]['prefLabel'], ["GUGUSELI@en", "HIHIHI@de"])


    def test_get_all_nodes_B(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestListXX",
                              prefLabel="TestListXX",
                              definition="A list for testing...")
        oldaplist.create()
        oldaplist = OldapList.read(con=self._connection,
                                   project="test",
                                   oldapListId="TestListXX")
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A",
                            prefLabel=["GUGUSELI@en", "HIHIHI@de"])
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

        olBAB = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_BAB")
        olBAB.insert_node_right_of(leftnode=olBAA)
        self.assertEqual(Xsd_integer(7), olBAB.leftIndex)
        self.assertEqual(Xsd_integer(8), olBAB.rightIndex)

        #nodes = get_nodes_from_list(con=self._connection, oldapList=oldaplist)
        #print_sublist(nodes)

        full_list = get_list(con=self._connection, project="test", oldapListId="TestListXX")
        full_list_obj = json.loads(full_list)
        self.assertEqual(full_list_obj['oldapListId'], 'TestListXX')
        self.assertEqual(full_list_obj['prefLabel'], ['TestListXX@en'])
        self.assertIsNotNone(full_list_obj['nodes'])
        self.assertIsInstance(full_list_obj['nodes'], list)
        sorted_nodes = sorted(full_list_obj['nodes'], key=lambda node: node['oldapListNodeId'])
        self.assertEqual(sorted_nodes[0]['oldapListNodeId'], 'Node_A')
        self.assertEqual(sorted_nodes[1]['oldapListNodeId'], 'Node_B')
        self.assertEqual(sorted_nodes[2]['oldapListNodeId'], 'Node_C')

        self.assertIsNotNone(sorted_nodes[1]['nodes'])
        self.assertIsInstance(sorted_nodes[1]['nodes'], list)

        x_node_BA = sorted_nodes[1]['nodes'][0]
        self.assertEqual(x_node_BA['oldapListNodeId'], 'Node_BA')

        self.assertIsNotNone(x_node_BA['nodes'])
        self.assertIsInstance(x_node_BA['nodes'], list)

        sorted_nodes_BA = sorted(x_node_BA['nodes'], key=lambda node: node['oldapListNodeId'])
        self.assertEqual(sorted_nodes_BA[0]['oldapListNodeId'], 'Node_BAA')
        self.assertEqual(sorted_nodes_BA[1]['oldapListNodeId'], 'Node_BAB')


if __name__ == '__main__':
    unittest.main()
