import unittest
from datetime import date
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.enums.language import Language
from omaslib.src.helpers.context import Context
from omaslib.src.dtypes.namespaceiri import NamespaceIRI
from omaslib.src.xsd.iri import Iri
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
        project = Project.read(con=self._connection, projectIri_SName=Iri("omas:SystemProject"))
        self.assertEqual(Xsd_NCName("system"), project.projectShortName)
        self.assertEqual(LangString(["System@en",
                                     "System@de",
                                     "Système@fr",
                                     "Systema@it"]), project.label)
        self.assertEqual(NamespaceIRI("http://omas.org/base#"), project.namespaceIri)
        self.assertEqual(LangString(["Project for system administration@en"]), project.comment)
        self.assertEqual(Xsd_date("2024-01-01"), project.projectStart)

        project = Project.read(con=self._connection, projectIri_SName='http://www.salsah.org/version/2.0/SwissBritNet')
        self.assertEqual(Xsd_NCName("britnet"), project.projectShortName)

        project2 = Project.read(con=self._connection, projectIri_SName='hyha')
        self.assertEqual(Xsd_NCName("hyha"), project2.projectShortName)

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

        project2 = Project.read(con=self._connection, projectIri_SName=projectIri)
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
        project3 = Project.read(con=self._connection, projectIri_SName=projectIri3)
        self.assertEqual("unittest3", project3.projectShortName)
        self.assertEqual(LangString(["unittest3@en", "unittest3@de"]), project3.label)
        self.assertEqual(LangString(["For testing3@en", "Für Tests3@de"]), project3.comment)
        self.assertEqual(Xsd_date(2024, 3, 3), project3.projectStart)

        project4 = Project(con=self._connection,
                           projectShortName="unittest4",
                           namespaceIri=NamespaceIRI("http://unitest.org/project/unittest4#"))
        project4.create()
        projectIri4 = project4.projectIri
        project4 = Project.read(con=self._connection, projectIri_SName=projectIri4)
        self.assertEqual("unittest4", project4.projectShortName)
        self.assertIsNone(project4.label)
        self.assertIsNone(project4.comment)
        self.assertIsNotNone(project4.projectStart)


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

        project = Project.read(con=self._connection, projectIri_SName=projectIri)
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
                          #projectEnd=Xsd_date(2025, 12, 31)
                          )
        project.create()
        projectIri = project.projectIri
        del project

        project = Project.read(con=self._connection, projectIri_SName=projectIri)
        project.delete()
        del project

        with self.assertRaises(OmasErrorNotFound) as ex:
            project = Project.read(con=self._connection, projectIri_SName=projectIri)

if __name__ == '__main__':
    unittest.main()
