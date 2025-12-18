import json
import unittest
from copy import deepcopy
from pathlib import Path
from pprint import pprint
from time import sleep

import yaml

from oldaplib.src.connection import Connection
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.language import Language
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.iconnection import IConnection
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplist_helpers import print_sublist, dump_list_to, ListFormat, \
    load_list_from_yaml
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
        cls._connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._connection.clear_graph(Xsd_QName('oldap:admin'))
        file = project_root / 'oldaplib' / 'ontologies' / 'admin.trig'
        cls._connection.upload_turtle(file)

        file = project_root / 'oldaplib' / 'ontologies' / 'admin-testing.trig'
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
                            **oldaplist.info,
                            oldapListNodeId="Node_A",
                            prefLabel=["GUGUSELI@en", "HIHIHI@de"])
        olA.create_root_node()

        full_list = dump_list_to(con=self._connection, project="hyha", oldapListId="TestList_HYHA")
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
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A",
                            prefLabel=["GUGUSELI@en", "HIHIHI@de"])
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

        olBAB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BAB")
        olBAB.insert_node_right_of(leftnode=olBAA)
        self.assertEqual(Xsd_integer(7), olBAB.leftIndex)
        self.assertEqual(Xsd_integer(8), olBAB.rightIndex)

        #nodes = get_nodes_from_list(con=self._connection, oldapList=oldaplist)
        #print_sublist(nodes)

        full_list = dump_list_to(con=self._connection, project="test", oldapListId="TestListXX")
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

    @unittest.skip('no longer needed')
    def test_deepcopy(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestDeepCopy",
                              prefLabel="TestDeepCopy@en",
                              definition="A list for testing deepcopy()")
        oldaplist.create()
        olA = OldapListNode(con=self._connection, oldapList=oldaplist, oldapListNodeId="Node_A",
                            prefLabel=["GUGUSELI@en", "HIHIHI@de"],
                            definition=["A test node named Node_A@en"])
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)
        self.assertEqual(LangString("GUGUSELI@en", "HIHIHI@de"), olA.prefLabel)
        self.assertEqual(LangString("A test node named Node_A@en"), olA.definition)

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

        oldaplist = OldapList.read(con=self._connection, project="test", oldapListId="TestDeepCopy")
        nodes = oldaplist.nodes
        listnode = OldapList.read(con=self._connection,
                                  project="test",
                                  oldapListId="TestDeepCopy")
        listnode.nodes = nodes

        listnode_copy = deepcopy(listnode)

        self.assertEqual(listnode_copy.node_classIri, listnode.node_classIri)
        self.assertEqual(listnode_copy.created, listnode.created)
        self.assertEqual(listnode_copy.creator, listnode.creator)
        self.assertEqual(listnode_copy.modified, listnode.modified)
        self.assertEqual(listnode_copy.contributor, listnode.contributor)
        self.assertEqual(listnode_copy.prefLabel, listnode.prefLabel)
        self.assertEqual(listnode_copy.definition, listnode.definition)

        self.assertEqual(len(listnode_copy.nodes), len(listnode.nodes))
        for i in range(len(listnode_copy.nodes)):
            self.assertEqual(listnode_copy.nodes[i].iri, listnode.nodes[i].iri)
            self.assertEqual(listnode_copy.nodes[i].created, listnode.nodes[i].created)
            self.assertEqual(listnode_copy.nodes[i].creator, listnode.nodes[i].creator)
            self.assertEqual(listnode_copy.nodes[i].modified, listnode.nodes[i].modified)
            self.assertEqual(listnode_copy.nodes[i].contributor, listnode.nodes[i].contributor)
            self.assertEqual(listnode_copy.nodes[i].prefLabel, listnode.nodes[i].prefLabel)
            self.assertEqual(listnode_copy.nodes[i].definition, listnode.nodes[i].definition)
            self.assertEqual(listnode_copy.nodes[i].leftIndex, listnode.nodes[i].leftIndex)
            self.assertEqual(listnode_copy.nodes[i].rightIndex, listnode.nodes[i].rightIndex)

        for i in range(len(listnode_copy.nodes[1].nodes)):
            self.assertEqual(listnode_copy.nodes[1].nodes[i].iri, listnode.nodes[1].nodes[i].iri)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].created, listnode.nodes[1].nodes[i].created)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].creator, listnode.nodes[1].nodes[i].creator)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].modified, listnode.nodes[1].nodes[i].modified)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].contributor, listnode.nodes[1].nodes[i].contributor)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].prefLabel, listnode.nodes[1].nodes[i].prefLabel)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].definition, listnode.nodes[1].nodes[i].definition)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].leftIndex, listnode.nodes[1].nodes[i].leftIndex)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].rightIndex, listnode.nodes[1].nodes[i].rightIndex)

    def test_cache(self):
        oldaplist = OldapList(con=self._connection,
                              project="hyha",
                              oldapListId="TestCache",
                              prefLabel="TestCache@en",
                              definition="A list for testing cache")
        oldaplist.create()
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A",
                            prefLabel=["GUGUSELI@en", "HIHIHI@de"],
                            definition=["A test node named Node_A@en"])
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)
        self.assertEqual(LangString("GUGUSELI@en", "HIHIHI@de"), olA.prefLabel)
        self.assertEqual(LangString("A test node named Node_A@en"), olA.definition)

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

        olBAB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BAB")
        olBAB.insert_node_right_of(leftnode=olBAA)
        self.assertEqual(Xsd_integer(7), olBAB.leftIndex)
        self.assertEqual(Xsd_integer(8), olBAB.rightIndex)

        listnode = OldapList.read(con=self._connection, project="hyha", oldapListId="TestCache")

        listnode_copy = OldapList.read(con=self._connection, project="hyha", oldapListId="TestCache")

        #self.assertEqual(listnode_copy.source, 'cache')
        self.assertEqual(listnode_copy.node_classIri, listnode.node_classIri)
        self.assertEqual(listnode_copy.created, listnode.created)
        self.assertEqual(listnode_copy.creator, listnode.creator)
        self.assertEqual(listnode_copy.modified, listnode.modified)
        self.assertEqual(listnode_copy.contributor, listnode.contributor)
        self.assertEqual(listnode_copy.prefLabel, listnode.prefLabel)
        self.assertEqual(listnode_copy.definition, listnode.definition)

        self.assertEqual(len(listnode_copy.nodes), len(listnode.nodes))
        for i in range(len(listnode_copy.nodes)):
            self.assertEqual(listnode_copy.nodes[i].iri, listnode.nodes[i].iri)
            self.assertEqual(listnode_copy.nodes[i].created, listnode.nodes[i].created)
            self.assertEqual(listnode_copy.nodes[i].creator, listnode.nodes[i].creator)
            self.assertEqual(listnode_copy.nodes[i].modified, listnode.nodes[i].modified)
            self.assertEqual(listnode_copy.nodes[i].contributor, listnode.nodes[i].contributor)
            self.assertEqual(listnode_copy.nodes[i].prefLabel, listnode.nodes[i].prefLabel)
            self.assertEqual(listnode_copy.nodes[i].definition, listnode.nodes[i].definition)
            self.assertEqual(listnode_copy.nodes[i].leftIndex, listnode.nodes[i].leftIndex)
            self.assertEqual(listnode_copy.nodes[i].rightIndex, listnode.nodes[i].rightIndex)

        for i in range(len(listnode_copy.nodes[1].nodes)):
            self.assertEqual(listnode_copy.nodes[1].nodes[i].iri, listnode.nodes[1].nodes[i].iri)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].created, listnode.nodes[1].nodes[i].created)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].creator, listnode.nodes[1].nodes[i].creator)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].modified, listnode.nodes[1].nodes[i].modified)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].contributor, listnode.nodes[1].nodes[i].contributor)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].prefLabel, listnode.nodes[1].nodes[i].prefLabel)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].definition, listnode.nodes[1].nodes[i].definition)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].leftIndex, listnode.nodes[1].nodes[i].leftIndex)
            self.assertEqual(listnode_copy.nodes[1].nodes[i].rightIndex, listnode.nodes[1].nodes[i].rightIndex)

        olBAB.delete_node()
        listnode_del = dump_list_to(con=self._connection, project="hyha", oldapListId="TestCache", listformat=ListFormat.PYTHON)
        self.assertEqual(listnode_del.source, 'db')

    def test_yaml_dump(self) -> None:
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestYAML",
                              prefLabel="TestYAML@en",
                              definition="A list for testing YAML")
        oldaplist.create()
        olA = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_A",
                            prefLabel=["GUGUSELI@en", "HIHIHI@de"],
                            definition=["A test node named Node_A@en"])
        olA.create_root_node()
        self.assertEqual(Xsd_integer(1), olA.leftIndex)
        self.assertEqual(Xsd_integer(2), olA.rightIndex)
        self.assertEqual(LangString("GUGUSELI@en", "HIHIHI@de"), olA.prefLabel)
        self.assertEqual(LangString("A test node named Node_A@en"), olA.definition)

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

        olBAB = OldapListNode(con=self._connection, **oldaplist.info, oldapListNodeId="Node_BAB")
        olBAB.insert_node_right_of(leftnode=olBAA)
        self.assertEqual(Xsd_integer(7), olBAB.leftIndex)
        self.assertEqual(Xsd_integer(8), olBAB.rightIndex)

        yaml_list = dump_list_to(con=self._connection, project="test", oldapListId="TestYAML", listformat=ListFormat.YAML)
        obj = yaml.safe_load(yaml_list)
        self.assertIsNotNone(obj.get(oldaplist.oldapListId))
        obj2 = obj[oldaplist.oldapListId]
        self.assertEqual(LangString(obj2['definition']), oldaplist.definition)
        self.assertEqual(LangString(obj2['label']), oldaplist.prefLabel)
        self.assertIsNotNone(obj2['nodes'])
        for id3, obj3 in obj2['nodes'].items():
            match id3:
                case 'Node_A':
                    self.assertEqual(LangString(obj3['label']), olA.prefLabel)
                    self.assertEqual(LangString(obj3['definition']), olA.definition)
                case 'Node_B':
                    self.assertEqual(LangString(obj3['label']), olB.prefLabel)
                    for id4, obj4 in obj3['nodes'].items():
                        self.assertEqual(id4, "Node_BA")
                        for id5, obj5 in obj4['nodes'].items():
                            match id5:
                                case 'Node_BAA':
                                    self.assertEqual(LangString(obj5['label']), olBAA.prefLabel)
                                case 'Node_BAB':
                                    self.assertEqual(LangString(obj5['label']), olBAB.prefLabel)
                case 'Node_C':
                    self.assertEqual(LangString(obj3['label']), olC.prefLabel)

    def test_yaml_load(self):
        project_root = find_project_root(__file__)
        file = project_root / 'oldaplib' / 'testdata' / 'testlist.yaml'
        listnodes = load_list_from_yaml(con=self._connection,
                                       project='test',
                                       filepath=file)
        self.assertEqual(len(listnodes), 1)
        listnode = listnodes[0]
        self.assertEqual(listnode.oldapListId, 'testlist')
        self.assertEqual(listnode.prefLabel, LangString('Test-list@en', 'Testliste@de', "liste de test@fr"))
        self.assertEqual(listnode.definition, LangString('a list for testing lists and listnoded@en', 'Eine Liste zum Testen des Listenelements und der Listenknoten@de'))
        self.assertEqual(len(listnode.nodes), 3)

        self.assertEqual(listnode.nodes[0].oldapListNodeId, 'node_A')
        self.assertEqual(listnode.nodes[0].prefLabel, LangString('Node_A@en', 'Knoten_A@de', 'Noed_a@fr'))
        self.assertEqual(listnode.nodes[0].definition, LangString('Node A from list testlist@en', 'Knoten A von der Liste testliste@de'))
        self.assertIsNone(listnode.nodes[0].nodes)

        self.assertEqual(listnode.nodes[1].oldapListNodeId, 'node_B')
        self.assertEqual(listnode.nodes[1].prefLabel, LangString('Node_B@en', 'Knoten_B@de', 'Noed_B@fr'))
        self.assertEqual(listnode.nodes[1].definition, LangString('Node B from list testlist@en', 'Knoten B von der Liste testliste@de'))
        self.assertEqual(len(listnode.nodes[1].nodes), 3)

        subnodes = listnode.nodes[1].nodes
        self.assertEqual(subnodes[0].oldapListNodeId, 'node_BA')
        self.assertEqual(subnodes[0].prefLabel, LangString('Node BA@en', 'Knoten BA@de', 'Noed BA@fr'))
        self.assertEqual(subnodes[0].definition, LangString('Node BA from list testlist@en', 'Knoten BA von der Liste testliste@de'))

        self.assertEqual(subnodes[1].oldapListNodeId, 'node_BB')
        self.assertEqual(subnodes[1].prefLabel, LangString('Node_BB@en', 'Knoten_BB@de', 'Noed_BB@fr'))
        self.assertEqual(subnodes[1].definition, LangString('Node BB from list testlist@en', 'Knoten BB von der Liste testliste@de'))

        self.assertEqual(subnodes[2].oldapListNodeId, 'node_BC')
        self.assertEqual(subnodes[2].prefLabel, LangString('Node_BC@en', 'Knoten_BC@de', 'Noed_BC@fr'))
        self.assertEqual(subnodes[2].definition, LangString('Node BC from list testlist@en', 'Knoten BC von der Liste testliste@de'))

        self.assertEqual(listnode.nodes[2].oldapListNodeId, 'node_C')
        self.assertEqual(listnode.nodes[2].prefLabel, LangString('Node_C@en', 'Knoten_C@de', 'Noed_C@fr'))
        self.assertEqual(listnode.nodes[2].definition, LangString('Node C from list testlist@en', 'Knoten C von der Liste testliste@de'))
        self.assertIsNone(listnode.nodes[2].nodes)

if __name__ == '__main__':
    unittest.main()
