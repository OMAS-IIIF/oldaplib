import unittest
from datetime import date
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.enums.language import Language
from omaslib.src.helpers.context import Context
from omaslib.src.dtypes.namespaceiri import NamespaceIRI
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.xsd.xsd_date import Xsd_date
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.omaserror import OmasErrorNotFound
from omaslib.src.project import Project


class Testproject(unittest.TestCase):
    _connection: Connection
    _unpriv: Connection

    @classmethod
    def setUpClass(cls):
        cls._context = Context(name="DEFAULT")

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._unpriv = Connection(server='http://localhost:7200',
                                 repo="omas",
                                 userId="fornaro",
                                 credentials="RioGrande",
                                 context_name="DEFAULT")


        # cls._connection.clear_graph(QName('test:shacl'))
        # cls._connection.clear_graph(QName('test:onto'))
        # cls._connection.upload_turtle("omaslib/testdata/connection_test.trig")
        # sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        cls._connection.clear_graph(Xsd_QName('omas:admin'))
        cls._connection.upload_turtle("omaslib/ontologies/admin.trig")
        sleep(1)  # upload may take a while...

    def test_project_read(self):
        project = Project.read(con=self._connection, projectIri=Xsd_QName("omas:SystemProject"))
        self.assertEqual(Xsd_NCName("system"), project.projectShortName)
        self.assertEqual(LangString(["System@en",
                                     "System@de",
                                     "Système@fr",
                                     "Systema@it"]), project.label)
        self.assertEqual(NamespaceIRI("http://omas.org/base#"), project.namespaceIri)
        self.assertEqual(LangString(["Project for system administration@en"]), project.comment)
        self.assertEqual(Xsd_date("2024-01-01"), project.projectStart)

    # @unittest.skip('Work in progress')
    def test_project_search(self):
        projects = Project.search(con=self._connection, label="HyperHamlet")
        self.assertEqual(["omas:HyperHamlet"], projects)

    # @unittest.skip('Work in progress')
    def test_project_search_fail(self):
        with self.assertRaises(OmasErrorNotFound) as ex:
            projects = Project.search(con=self._connection, label="NoExisting")

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
        del project

        project2 = Project.read(con=self._connection, projectIri=projectIri)
        self.assertEqual("unittest", project2.projectShortName)
        self.assertEqual(LangString(["unittest@en", "unittest@de"]), project2.label)
        self.assertEqual(LangString(["For testing@en", "Für Tests@de"]), project2.comment)
        self.assertEqual(Xsd_date(2024, 1, 1), project2.projectStart)
        self.assertEqual(Xsd_date(2025, 12, 31), project2.projectEnd)

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

        project = Project.read(con=self._connection, projectIri=projectIri)
        project.comment[Language.FR] = "Pour les tests"
        project.comment[Language.DE] = "FÜR DAS TESTEN"
        project.label = LangString(["UPDATETEST@en", "UP-DATE-TEST@fr"])
        project.projectEnd = Xsd_date(date(2026, 6, 30))
        project.update()
        self.assertEqual(project.comment, LangString(["For testing@en", "FÜR DAS TESTEN@de", "Pour les tests@fr"]))
        self.assertEqual(project.label, LangString(["UPDATETEST@en", "UP-DATE-TEST@fr"]))
        self.assertEqual(project.projectEnd, Xsd_date(2026, 6, 30))

    # @unittest.skip('Work in progress')
    def test_project_delete(self):
        project = Project(con=self._connection,
                          projectShortName="deletetest",
                          label=LangString(["deletetest@en", "deletetest@de"]),
                          namespaceIri=NamespaceIRI("http://unitest.org/project/deletetest#"),
                          comment=LangString(["For deleting@en", "Für Löschung@de"]),
                          projectStart=Xsd_date(2024, 1, 1),
                          projectEnd=Xsd_date(2025, 12, 31)
                          )
        project.create()
        projectIri = project.projectIri
        del project

        project = Project.read(con=self._connection, projectIri=projectIri)
        project.delete()
        del project

        with self.assertRaises(OmasErrorNotFound) as ex:
            project = Project.read(con=self._connection, projectIri=projectIri)

if __name__ == '__main__':
    unittest.main()
