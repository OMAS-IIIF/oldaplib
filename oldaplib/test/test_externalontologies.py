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

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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

        project = Project(con=cls._connection,
                          projectIri=Iri("http://extonto.test.org/test"),
                          projectShortName="testext",
                          namespaceIri=NamespaceIRI("http://extonto.test.org/test/ns/"))
        project.create()

        dm = DataModel(con=cls._connection, project=project)
        dm.create()


    @classmethod
    def tearDownClass(cls):
        cls._connection.clear_graph(Xsd_QName('testext:shacl'))
        cls._connection.clear_graph(Xsd_QName('testext:onto'))
        #cls._connection.upload_turtle("oldaplib/ontologies/admin.trig")
        #sleep(1)  # upload may take a while...
        pass

    def test_create(self):
        p = Project.read(con=self._connection, projectIri_SName="testext", ignore_cache=True)
        dm = DataModel.read(con=self._connection, project="testext", ignore_cache=True)

        eo1 = ExternalOntology(con=self._connection,
                               projectShortName="testext",
                               prefix="gagaA",
                               label=LangString("GAGA A ontology@en", "Gaga A Ontologie@de"),
                               namespaceIri=NamespaceIRI("http://gaga.org/ns/gagaA/"))
        eo1.create()
        del eo1

        eo1 = ExternalOntology.read(con=self._connection, projectShortName="testext", prefix="gagaA", ignore_cache=True)
        self.assertEqual(eo1.prefix, "gagaA")
        self.assertEqual(eo1.label, LangString("GAGA A ontology@en", "Gaga A Ontologie@de"))
        self.assertEqual(eo1.namespaceIri, NamespaceIRI("http://gaga.org/ns/gagaA/"))

        ExternalOntology.delete_all(con=self._connection, projectShortName="testext")
        pass


    def test_update(self):
        p = Project.read(con=self._connection, projectIri_SName="testext", ignore_cache=True)
        dm = DataModel.read(con=self._connection, project="testext", ignore_cache=True)

        eo1 = ExternalOntology(con=self._connection,
                               projectShortName="testext",
                               prefix="gagaB",
                               label=LangString("GAGA B ontology@en", "Gaga B Ontologie@de"),
                               namespaceIri=NamespaceIRI("http://gaga.org/ns/gagaB/"))
        eo1.create()

        del eo1
        eo1 = ExternalOntology.read(con=self._connection, projectShortName="testext", prefix="gagaB", ignore_cache=True)
        with self.assertRaises(OldapErrorImmutable):
            eo1.prefix = "gugus"
        eo1.comment = LangString("Gugus comment@en", "Gugus Kommentar@de")
        del eo1.label[Language.DE]
        eo1.label[Language.FR] = "GAGA B ontologie"
        eo1.update()

        del eo1
        eo1 = ExternalOntology.read(con=self._connection, projectShortName="testext", prefix="gagaB", ignore_cache=True)
        self.assertEqual(eo1.prefix, "gagaB")
        self.assertEqual(eo1.label, LangString("GAGA B ontology@en", "GAGA B ontologie@fr"))
        self.assertEqual(eo1.comment, LangString("Gugus comment@en", "Gugus Kommentar@de"))
        self.assertEqual(eo1.namespaceIri, NamespaceIRI("http://gaga.org/ns/gagaB/"))

        with self.assertRaises(OldapErrorImmutable):
            eo1.namespaceIri = NamespaceIRI("http://gaga.org/ns/gaga2/new/")

        ExternalOntology.delete_all(con=self._connection, projectShortName="testext")

    def test_search(self):
        p = Project.read(con=self._connection, projectIri_SName="testext", ignore_cache=True)
        dm = DataModel.read(con=self._connection, project="testext", ignore_cache=True)

        eo1 = ExternalOntology(con=self._connection,
                               projectShortName="testext",
                               prefix="gagaC",
                               label=LangString("GAGA C ontology@en", "Gaga C Ontologie@de"),
                               namespaceIri=NamespaceIRI("http://gaga.org/ns/gagaC/"))
        eo1.create()

        eo2 = ExternalOntology(con=self._connection,
                               projectShortName="testext",
                               prefix="gagaD",
                               label=LangString("GAGA D ontology@en", "Gaga D Ontologie@de"),
                               namespaceIri=NamespaceIRI("http://gaga.org/ns/gagaD/"))
        eo2.create()

        res = ExternalOntology.search(con=self._connection, projectShortName="testext")
        qnames = [x.extonto_qname for x in res]
        self.assertEqual(set(qnames), {Xsd_QName('testext:gagaC'), Xsd_QName('testext:gagaD')})

        ExternalOntology.delete_all(con=self._connection, projectShortName="testext")

    def test_delete(self):
        p = Project.read(con=self._connection, projectIri_SName="testext", ignore_cache=True)
        dm = DataModel.read(con=self._connection, project="testext", ignore_cache=True)

        eo1 = ExternalOntology(con=self._connection,
                               projectShortName="testext",
                               prefix="gagaE",
                               label=LangString("GAGA E ontology@en", "Gaga E Ontologie@de"),
                               namespaceIri=NamespaceIRI("http://gaga.org/ns/gagaE/"))
        eo1.create()

        eo2 = ExternalOntology(con=self._connection,
                               projectShortName="testext",
                               prefix="gagaF",
                               label=LangString("GAGA F ontology@en", "Gaga F Ontologie@de"),
                               namespaceIri=NamespaceIRI("http://gaga.org/ns/gagaF/"))
        eo2.create()
        res = ExternalOntology.search(con=self._connection, projectShortName="testext", prefix="gagaF")
        self.assertEqual(len(res), 1)
        res[0].delete()

        ExternalOntology.delete_all(con=self._connection, projectShortName="testext")




