import unittest
from pathlib import Path
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.dtypes.namespaceiri import NamespaceIRI
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.langstring import LangString
from omaslib.src.iconnection import IConnection
from omaslib.src.oldaplist import OldapList
from omaslib.src.xsd.xsd_qname import Xsd_QName


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
                                     repo="omas",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._connection.clear_graph(Xsd_QName('omas:admin'))
        file = project_root / 'omaslib' / 'ontologies' / 'admin.trig'
        cls._connection.upload_turtle(file)


        cls._connection.clear_graph(Xsd_QName('test:test'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        file = project_root / 'omaslib' / 'testdata' / 'connection_test.trig'
        cls._connection.upload_turtle(file)
        sleep(1)


    @classmethod
    def tearDownClass(cls):
        pass

    def test_constructor(self):
        oldaplist = OldapList(con=self._connection, prefLabel="TestList", definition="A list for testing...")
        iri = oldaplist.oldapListIri
        self.assertEqual(LangString("TestList"), oldaplist.prefLabel)
        self.assertEqual(LangString("A list for testing..."), oldaplist.definition)


if __name__ == '__main__':
    unittest.main()
