import unittest
from pathlib import Path
from time import sleep

from oldaplib.src.ObjectFactory import ResourceInstanceFactory
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
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

class TestObjectFactory(unittest.TestCase):

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
        cls._context['test'] = 'http://oldap.org/test#'
        cls._context.use('test')

        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        cls._connection.clear_graph(Xsd_QName('oldap:admin'))

        file = project_root / 'oldaplib' / 'ontologies' / 'admin.trig'
        cls._connection.upload_turtle(file)
        sleep(1)  # upload may take a while...

        file = project_root / 'oldaplib' / 'testdata' / 'objectfactory_test.trig'
        cls._connection.upload_turtle(file)

        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(Xsd_QName('oldaplib:admin'))
        #cls._connection.upload_turtle("oldaplib/ontologies/admin.trig")
        #sleep(1)  # upload may take a while...
        pass


    def test_constructor(self):
        project = Project.read(con=self._connection, projectIri_SName='test')
        factory = ResourceInstanceFactory(con=self._connection, project=project)
        Book = factory.createObjectInstance(Iri('test:Book'), 'Book')
        b = Book(title="Hitchhiker's Guide to the Galaxy",
                 author=Iri('test:DouglasAdams'),
                 pubDate="1995-09-27")
        self.assertEqual(b.title, "Hitchhiker's Guide to the Galaxy")
        self.assertEqual(b.author, Iri('test:DouglasAdams'))
        self.assertEqual(b.pubDate, "1995-09-27")

        Page = factory.createObjectInstance(Iri('test:Page'), 'Page')
        p1 = Page(pageDesignation="Cover",
                 pageNum=1,
                 pageDescription=LangString("Cover page of book@en", "Vorderseite des Bucheinschlags@de"),
                 pageInBook="test:Hitchhiker")
        self.assertEqual(p1.pageDesignation, "Cover")
        self.assertEqual(p1.pageNum, 1)
        self.assertEqual(p1.pageDescription, LangString("Cover page of book@en", "Vorderseite des Bucheinschlags@de"))
        self.assertEqual(p1.pageInBook, "test:Hitchhiker")

if __name__ == '__main__':
    unittest.main()
