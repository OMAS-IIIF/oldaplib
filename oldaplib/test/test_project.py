import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path
from time import sleep

from oldaplib.src.cachesingleton import CacheSingleton
from oldaplib.src.connection import Connection
from oldaplib.src.enums.language import Language
from oldaplib.src.helpers.context import Context
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapErrorInconsistency, OldapErrorNoPermission
from oldaplib.src.project import Project


def find_project_root(current_path):
    # Climb up the directory hierarchy and check for a marker file
    path = Path(current_path).absolute()
    while not (path / 'pyproject.toml').exists():
        if path.parent == path:
            # Root of the filesystem, file not found
            raise RuntimeError('Project root not found')
        path = path.parent
    return path


class Testproject(unittest.TestCase):
    _connection: Connection
    _unpriv: Connection

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


        cls._connection.clear_graph(Xsd_QName('oldap:admin'))
        file = project_root / 'oldaplib' / 'ontologies' / 'admin.trig'
        cls._connection.upload_turtle(file)
        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(Xsd_QName('oldap:admin'))
        #cls._connection.upload_turtle("oldaplib/ontologies/admin.trig")
        #sleep(1)  # upload may take a while...
        pass

    def test_project_deepcopy(self):
        project = Project(con=self._connection,
                          projectShortName="unittest",
                          label=LangString(["unittest@en", "unittest@de"]),
                          namespaceIri=NamespaceIRI("http://unitest.org/project/unittest#"),
                          comment=LangString(["For testing@en", "Für Tests@de"]),
                          projectStart=Xsd_date(2024, 1, 1),
                          projectEnd=Xsd_date(2025, 12, 31)
                          )
        project2 = deepcopy(project)
        self.assertFalse(project is project2)
        self.assertEqual(project.projectIri, project2.projectIri)
        self.assertEqual(project.projectShortName, project2.projectShortName)
        self.assertEqual(project.label, project2.label)
        self.assertEqual(project.comment, project2.comment)
        self.assertEqual(project.projectStart, project2.projectStart)
        self.assertEqual(project.projectEnd, project2.projectEnd)


    # @unittest.skip('Work in progress')
    def test_project_read(self):
        project = Project.read(con=self._connection, projectIri_SName=Iri("oldap:SystemProject"), ignore_cache=True)
        self.assertEqual(Xsd_NCName("oldap"), project.projectShortName)
        self.assertEqual(LangString(["System@en",
                                     "System@de",
                                     "Système@fr",
                                     "Systema@it"]), project.label)
        self.assertEqual(NamespaceIRI("http://oldap.org/base#"), project.namespaceIri)
        self.assertEqual(LangString(["Project for system administration@en"]), project.comment)
        self.assertEqual(Xsd_date("2024-01-01"), project.projectStart)

        project = Project.read(con=self._connection, projectIri_SName='http://www.salsah.org/version/2.0/SwissBritNet', ignore_cache=True)
        self.assertEqual(Xsd_NCName("britnet"), project.projectShortName)

        project2 = Project.read(con=self._connection, projectIri_SName='britnet', ignore_cache=True)
        self.assertEqual(Xsd_NCName("britnet"), project2.projectShortName)
        self.assertEqual(Iri('http://www.salsah.org/version/2.0/SwissBritNet'), project2.projectIri)

    def test_project_read_from_cache(self):
        project = Project.read(con=self._connection, projectIri_SName='britnet', ignore_cache=True)
        project2 = Project.read(con=self._connection, projectIri_SName='britnet')
        self.assertFalse(project is project2)
        self.assertEqual(project.projectShortName, project2.projectShortName)
        self.assertFalse(project.projectShortName is project2.projectShortName)

    def test_project_read_unknown(self):
        with self.assertRaises(OldapErrorNotFound):
            project = Project.read(con=self._connection, projectIri_SName='http://www.gaga.org/version/2.0/GAGA', ignore_cache=True)


    # @unittest.skip('Work in progress')
    def test_project_search(self):
        projects = Project.search(con=self._connection, label="HyperHamlet")
        self.assertEqual(["oldap:HyperHamlet"], projects)

    # @unittest.skip('Work in progress')
    def test_project_search_fail(self):
        projects = Project.search(con=self._connection, label="NoExisting")
        self.assertEqual([], projects)

    def test_project_create_simplest(self):
        project = Project(con=self._connection,
                          projectShortName="simpleproj",
                          namespaceIri=NamespaceIRI("http://unitest.org/project/simpleproj#"),
                          projectStart=Xsd_date(2024, 1, 1),
                          projectEnd=Xsd_date(2025, 12, 31)
                          )
        project.create()
        self.assertIsNotNone(project.created)
        self.assertIsNotNone(project.creator)
        self.assertIsNotNone(project.modified)
        self.assertIsNotNone(project.contributor)
        self.assertEqual("simpleproj", project.projectShortName)
        self.assertEqual("http://unitest.org/project/simpleproj#", project.namespaceIri)

    # @unittest.skip('Work in progress')
    def test_project_create(self):
        project = Project(con=self._connection,
                          projectShortName="unittest",
                          label=LangString(["unittest@en", "unittest@de"]),
                          namespaceIri=NamespaceIRI("http://unitest.org/project/unittest#"),
                          comment=LangString(["For testing@en", "Für Tests@de"]),
                          projectStart=Xsd_date(2024, 1, 1),
                          projectEnd=Xsd_date(2025, 12, 31)
                          )
        project.create()
        projectIri = project.projectIri
        self.assertIsNotNone(project.created)
        self.assertIsNotNone(project.creator)
        self.assertIsNotNone(project.modified)
        self.assertIsNotNone(project.contributor)
        del project

        project2 = Project.read(con=self._connection, projectIri_SName=projectIri, ignore_cache=True)
        self.assertEqual("unittest", project2.projectShortName)
        self.assertEqual(LangString(["unittest@en", "unittest@de"]), project2.label)
        self.assertEqual(LangString(["For testing@en", "Für Tests@de"]), project2.comment)
        self.assertEqual(Xsd_date(2024, 1, 1), project2.projectStart)
        self.assertEqual(Xsd_date(2025, 12, 31), project2.projectEnd)

        project3 = Project(con=self._connection,
                           projectShortName="unittest3",
                           label=LangString(["unittest3@en", "unittest3@de"]),
                           namespaceIri=NamespaceIRI("http://unitest.org/project/unittest3#"),
                           comment=LangString(["For testing3@en", "Für Tests3@de"]),
                           projectStart=Xsd_date(2024, 3, 3),
                           projectEnd=None)
        project3.create()
        projectIri3 = project3.projectIri
        project3 = Project.read(con=self._connection, projectIri_SName=projectIri3, ignore_cache=True)
        self.assertEqual("unittest3", project3.projectShortName)
        self.assertEqual(LangString(["unittest3@en", "unittest3@de"]), project3.label)
        self.assertEqual(LangString(["For testing3@en", "Für Tests3@de"]), project3.comment)
        self.assertEqual(Xsd_date(2024, 3, 3), project3.projectStart)

        project4 = Project(con=self._connection,
                           projectShortName="unittest4",
                           namespaceIri=NamespaceIRI("http://unitest.org/project/unittest4#"),
                           label=LangString("For testing4@en"))
        project4.create()
        projectIri4 = project4.projectIri
        project4 = Project.read(con=self._connection, projectIri_SName=projectIri4, ignore_cache=True)
        self.assertEqual("unittest4", project4.projectShortName)
        self.assertIsNone(project4.comment)
        self.assertIsNotNone(project4.projectStart)

        with self.assertRaises(OldapErrorInconsistency) as ex:
            project5 = Project(con=self._connection,
                               projectShortName="unittest5",
                               label=LangString(["unittest5@en", "unittest5@de"]),
                               namespaceIri=NamespaceIRI("http://unitest.org/project/unittest3#"),
                               comment=LangString(["For testing3@en", "Für Tests3@de"]),
                               projectStart=Xsd_date(2024, 3, 3),
                               projectEnd=Xsd_date(2024, 3, 2))

        project6 = Project(con=self._connection,
                           projectShortName="unittest6",
                           label=LangString("unittest\"; SELECT * WHERE {?s ?p ?o}"),
                           namespaceIri=NamespaceIRI("http://unitest.org/project/unittest6#"),
                           comment=LangString(["For testing6@en", "Für Tests6@de"]),
                           projectStart=Xsd_date(2024, 3, 3),
                           projectEnd=None)
        project6.create()
        projectIri = project6.projectIri
        del project6

        project6 = Project.read(con=self._connection, projectIri_SName=projectIri, ignore_cache=True)
        self.assertEqual(project6.label, LangString("unittest\"; SELECT * WHERE {?s ?p ?o}"))

        with self.assertRaises(OldapErrorInconsistency) as ex:
            project7 = Project(con=self._connection,
                               projectShortName="unittest7",
                               label=LangString("date"),
                               namespaceIri=NamespaceIRI("http://unitest.org/project/unittest3#"),
                               comment=LangString(["For testing3@en", "Für Tests3@de"]),
                               projectStart=Xsd_date(2024, 3, 3),
                               projectEnd=Xsd_date(2024, 3, 2))

        project8 = Project(con=self._connection,
                           projectShortName="unittest8",
                           label=LangString("unittes\"; SELECT * WHERE {?s ?p ?o}"),
                           namespaceIri=NamespaceIRI("http://unitest.org/project/unittest8#"),
                           comment=LangString(["For testing8@en", "Für Tests3@de"]),
                           projectEnd=Xsd_date(2028, 3, 3))
        self.assertEqual(project8.projectStart, date.today())

    def test_project_create_without_label_comment(self):
        project = Project(con=self._connection,
                          projectShortName="emptyfieldsXX",
                          namespaceIri=NamespaceIRI("http://unitest.org/project/unittest#"),
                          projectStart=Xsd_date(2024, 1, 1),
                          projectEnd=Xsd_date(2025, 12, 31)
                          )
        project.create()

    def test_project_create_empty_fields(self):
        project = Project(con=self._connection,
                          projectShortName="emptyfields1",
                          label=LangString(["unittest@en", "unittest@de"]),
                          namespaceIri=NamespaceIRI("http://unitest.org/project/unittest#"),
                          projectStart=Xsd_date(2024, 1, 1),
                          projectEnd=Xsd_date(2025, 12, 31)
                          )
        project.create()
        projectIri = project.projectIri
        del project
        project = Project.read(con=self._connection, projectIri_SName=projectIri, ignore_cache=True)
        self.assertIsNone(project.comment)

        project = Project(con=self._connection,
                          projectShortName="emptyfields2",
                          label=LangString(["unittest@en", "unittest@de"]),
                          namespaceIri=NamespaceIRI("http://unitest.org/project/unittest#"),
                          projectStart=Xsd_date(2024, 1, 1),
                          projectEnd=Xsd_date(2025, 12, 31)
                          )
        project.create()
        projectIri = project.projectIri
        del project
        project = Project.read(con=self._connection, projectIri_SName=projectIri, ignore_cache=True)
        project.comment = LangString("Comment for unittest@en", "Kommentar für unittest@de")
        self.assertEqual(project.comment[Language.EN], "Comment for unittest")
        self.assertEqual(project.comment[Language.DE], "Kommentar für unittest")
        project.update()
        del project
        project = Project.read(con=self._connection, projectIri_SName=projectIri, ignore_cache=True)
        self.assertEqual(project.comment[Language.EN], "Comment for unittest")
        self.assertEqual(project.comment[Language.DE], "Kommentar für unittest")

        project = Project(con=self._connection,
                          projectShortName="emptyfields3",
                          label=LangString(["unittest@en", "unittest@de"]),
                          comment=[],
                          namespaceIri=NamespaceIRI("http://unitest.org/project/unittest#"),
                          projectStart=Xsd_date(2024, 1, 1),
                          projectEnd=Xsd_date(2025, 12, 31)
                          )
        self.assertIsNone(project.comment)


    # @unittest.skip('Work in progress')
    def test_project_modify(self):
        project = Project(con=self._connection,
                          projectShortName="updatetest",
                          label=LangString(["updatetest@en", "updatetest@de"]),
                          namespaceIri=NamespaceIRI("http://unitest.org/project/updatetest#"),
                          comment=LangString(["For testing@en", "Für Tests@de"]),
                          projectStart=Xsd_date(2024, 1, 1),
                          projectEnd=Xsd_date(2025, 12, 31)
                          )
        project.create()

        projectIri = project.projectIri
        del project

        project = Project.read(con=self._connection, projectIri_SName=projectIri, ignore_cache=True)
        project.comment[Language.FR] = "Pour les tests"
        project.comment[Language.DE] = "FÜR DAS TESTEN"
        project.label = LangString(["UPDATETEST@en", "UP-DATE-TEST@fr"])
        project.projectEnd = Xsd_date(date(2026, 6, 30))
        project.update()
        self.assertEqual(project.comment, LangString(["For testing@en", "FÜR DAS TESTEN@de", "Pour les tests@fr"]))
        self.assertEqual(project.label, LangString(["UPDATETEST@en", "UP-DATE-TEST@fr"]))
        self.assertEqual(project.projectEnd, Xsd_date(2026, 6, 30))

    def test_project_update_B(self):
        project = Project(con=self._connection,
                          projectShortName="updatetestB",
                          label=LangString(["updatetest@en", "updatetest@de"]),
                          namespaceIri=NamespaceIRI("http://unitest.org/project/updatetestB#"),
                          comment=LangString(["For testing@en", "Für Tests@de"]),
                          projectStart=Xsd_date(2024, 1, 1),
                          projectEnd=Xsd_date(2025, 12, 31)
                          )
        project.create()

        projectIri = project.projectIri
        del project

        project = Project.read(con=self._connection, projectIri_SName="updatetestB", ignore_cache=True)
        project.comment[Language.IT] = "per i test"
        del project.comment[Language.EN]
        project.update()

        project = Project.read(con=self._connection, projectIri_SName="updatetestB", ignore_cache=True)
        self.assertEqual(project.comment, LangString(["Für Tests@de", "per i test@it"]))

    def test_project_start_end_consistency(self):
        project = Project(con=self._connection,
                          projectShortName="startendtest",
                          label=LangString(["startendtest@en", "startendtest@de"]),
                          namespaceIri=NamespaceIRI("http://unitest.org/project/startendtest#"),
                          comment=LangString(["For testing@en", "Für Tests@de"]),
                          projectStart=Xsd_date(2024, 1, 1),
                          projectEnd=Xsd_date(2025, 12, 31)
                          )
        with self.assertRaises(OldapErrorInconsistency):
            project.projectStart = Xsd_date(2026, 1, 1)
        with self.assertRaises(OldapErrorInconsistency):
            project.projectEnd = Xsd_date(2023, 12, 31)


    # @unittest.skip('Work in progress')
    def test_project_delete(self):
        project = Project(con=self._connection,
                          projectShortName="deletetest",
                          label=LangString(["deletetest@en", "deletetest@de"]),
                          namespaceIri=NamespaceIRI("http://unitest.org/project/deletetest#"),
                          comment=LangString(["For deleting@en", "Für Löschung@de"]),
                          projectStart=Xsd_date(2024, 1, 1),
                          #projectEnd=Xsd_date(2025, 12, 31)
                          )
        project.create()
        projectIri = project.projectIri

        project = Project.read(con=self._connection, projectIri_SName="deletetest", ignore_cache=True)
        project.delete()

        with self.assertRaises(OldapErrorNotFound) as ex:
            project = Project.read(con=self._connection, projectIri_SName=projectIri, ignore_cache=True)

    def test_unauthorized_access(self):
        project = Project(con=self._unpriv,
                          projectShortName="unauthorized",
                          label=LangString(["unauthorized@en", "unauthorized@de"]),
                          namespaceIri=NamespaceIRI("http://unitest.org/project/unauthorized#"),
                          comment=LangString(["For unauthorized access@en", "Für nicht authorisierten Zugang@de"]),
                          projectStart=Xsd_date(2024, 1, 1),
                          )
        cache = CacheSingleton()
        with self.assertRaises(OldapErrorNoPermission) as ex:
            project.create()

        project = Project(con=self._connection,
                          projectShortName="unauthorized",
                          label=LangString(["unauthorized@en", "unauthorized@de"]),
                          namespaceIri=NamespaceIRI("http://unitest.org/project/unauthorized#"),
                          comment=LangString(["For unauthorized access@en", "Für nicht authorisierten Zugang@de"]),
                          projectStart=Xsd_date(2024, 1, 1),
                          )
        project.create()

        project = Project.read(con=self._unpriv, projectIri_SName="unauthorized", ignore_cache=True)
        project.projectEnd = Xsd_date(2025, 12, 31)
        with self.assertRaises(OldapErrorNoPermission) as ex:
            project.update()
        with self.assertRaises(OldapErrorNoPermission) as ex:
            project.delete()


if __name__ == '__main__':
    unittest.main()
