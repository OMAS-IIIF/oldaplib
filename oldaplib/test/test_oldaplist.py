import unittest
from pathlib import Path
from time import sleep

from oldaplib.src.connection import Connection
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.language import Language
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapErrorImmutable
from oldaplib.src.iconnection import IConnection
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.enums.oldaplistattr import OldapListAttr
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
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


class TestOldapList(unittest.TestCase):

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

    def test_constructor_project_shortname(self):
        oldaplist = OldapList(con=self._connection,
                              project="test",
                              oldapListId="TestList",
                              prefLabel="TestList",
                              definition="A list for testing...")
        self.assertEqual(Xsd_NCName('TestList'), oldaplist.oldapListId)
        self.assertEqual(LangString("TestList"), oldaplist.prefLabel)
        self.assertEqual(LangString("A list for testing..."), oldaplist.definition)

    def test_constructor_project_object(self):
        oldaplist = OldapList(con=self._connection,
                              project=self._project,
                              oldapListId="TestList2",
                              prefLabel="TestList2",
                              definition="A list for testing...")
        self.assertEqual(Xsd_NCName('TestList2'), oldaplist.oldapListId)
        self.assertEqual(LangString("TestList2"), oldaplist.prefLabel)
        self.assertEqual(LangString("A list for testing..."), oldaplist.definition)

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
        oldaplist.delete()
        with self.assertRaises(OldapErrorNotFound) as ex:
            oldaplist = OldapList.read(con=self._connection,
                                       project=self._project,
                                       oldapListId="TestDeleteList")


if __name__ == '__main__':
    unittest.main()
