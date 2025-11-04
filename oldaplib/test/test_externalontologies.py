import unittest
from pathlib import Path
from time import sleep
from tkinter.font import names

from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.language import Language
from oldaplib.src.externalontology import ExternalOntology
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapError, OldapErrorImmutable
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


class TestexternalOntologies(unittest.TestCase):

    _connection: Connection
    _unpriv: Connection

    #@classmethod
    def setUp(cls):
        super().setUp()
        project_root = find_project_root(__file__)
        cls._context = Context(name="DEFAULT")

        cls._connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._unpriv = Connection(userId="fornaro",
                                 credentials="RioGrande",
                                 context_name="DEFAULT")


        cls._connection.clear_graph(Xsd_QName('oldap:admin'))
        file = project_root / 'oldaplib' / 'ontologies' / 'admin.trig'
        cls._connection.upload_turtle(file)
        file = project_root / 'oldaplib' / 'ontologies' / 'admin-testing.trig'
        cls._connection.upload_turtle(file)
        sleep(1)  # upload may take a while...

        project = Project(con=cls._connection,
                          projectIri=Iri("http://extonto.test.org/test"),
                          projectShortName="test",
                          namespaceIri=NamespaceIRI("http://extonto.test.org/test/ns/"))
        project.create()

        dm = DataModel(con=cls._connection, project=project)
        dm.create()


    #@classmethod
    def tearDown(cls):
        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        #cls._connection.upload_turtle("oldaplib/ontologies/admin.trig")
        #sleep(1)  # upload may take a while...
        pass

    def test_create(self):
        p = Project.read(con=self._connection, projectIri_SName="test", ignore_cache=True)
        dm = DataModel.read(con=self._connection, project="test", ignore_cache=True)

        eo1 = ExternalOntology(con=self._connection,
                               graph="test",
                               prefix="gaga",
                               label=LangString("GAGA ontology@en", "Gaga Ontologie@de"),
                               namespaceIri=NamespaceIRI("http://gaga.org/ns/gaga/"))
        eo1.create()
        del eo1

        eo1 = ExternalOntology.read(con=self._connection, graph="test", prefix="gaga", ignore_cache=True)
        self.assertEqual(eo1.prefix, "gaga")
        self.assertEqual(eo1.label, LangString("GAGA ontology@en", "Gaga Ontologie@de"))
        self.assertEqual(eo1.namespaceIri, NamespaceIRI("http://gaga.org/ns/gaga/"))

    def test_update(self):
        p = Project.read(con=self._connection, projectIri_SName="test", ignore_cache=True)
        dm = DataModel.read(con=self._connection, project="test", ignore_cache=True)

        eo1 = ExternalOntology(con=self._connection,
                               graph="test",
                               prefix="gaga2",
                               label=LangString("GAGA ontology2@en", "Gaga Ontologie2@de"),
                               namespaceIri=NamespaceIRI("http://gaga.org/ns/gaga2/"))
        eo1.create()

        del eo1
        eo1 = ExternalOntology.read(con=self._connection, graph="test", prefix="gaga2", ignore_cache=True)
        eo1.prefix = "gugus"
        eo1.comment = LangString("Gugus comment@en", "Gugus Kommentar@de")
        del eo1.label[Language.DE]
        eo1.label[Language.FR] = "GAGA ontologie2"
        eo1.update()


        del eo1
        eo1 = ExternalOntology.read(con=self._connection, graph="test", prefix="gaga2", ignore_cache=True)
        self.assertEqual(eo1.prefix, "gugus")
        self.assertEqual(eo1.label, LangString("GAGA ontology2@en", "GAGA ontologie2@fr"))
        self.assertEqual(eo1.comment, LangString("Gugus comment@en", "Gugus Kommentar@de"))
        self.assertEqual(eo1.namespaceIri, NamespaceIRI("http://gaga.org/ns/gaga2/"))

        with self.assertRaises(OldapErrorImmutable):
            eo1.namespaceIri = NamespaceIRI("http://gaga.org/ns/gaga2/new/")

    def test_search(self):
        p = Project.read(con=self._connection, projectIri_SName="test", ignore_cache=True)
        dm = DataModel.read(con=self._connection, project="test", ignore_cache=True)

        eo1 = ExternalOntology(con=self._connection,
                               graph="test",
                               prefix="gaga1",
                               label=LangString("GAGA1 ontology@en", "Gaga1 Ontologie@de"),
                               namespaceIri=NamespaceIRI("http://gaga.org/ns/gaga1/"))
        eo1.create()

        eo2 = ExternalOntology(con=self._connection,
                               graph="test",
                               prefix="gaga2",
                               label=LangString("GAGA2 ontology@en", "Gaga2 Ontologie@de"),
                               namespaceIri=NamespaceIRI("http://gaga.org/ns/gaga2/"))
        eo2.create()

        res = ExternalOntology.search(con=self._connection, graph="test")
        self.assertEqual(set(res.keys()), {Xsd_QName('test:gaga1'), Xsd_QName('test:gaga2')})
