import unittest
from pathlib import Path
from time import sleep

from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel, PropertyClassChange, ResourceClassChange
from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.action import Action
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.enums.language import Language
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass


def find_project_root(current_path):
    # Climb up the directory hierarchy and check for a marker file
    path = Path(current_path).absolute()
    while not (path / 'pyproject.toml').exists():
        if path.parent == path:
            # Root of the filesystem, file not found
            raise RuntimeError('Project root not found')
        path = path.parent
    return path


class TestDataModel(unittest.TestCase):
    _context: Context
    _connection: Connection
    _project: Project
    _dmproject: Project
    _sysproject: Project

    @classmethod
    def setUp(cls):
        super().setUpClass()
        project_root = find_project_root(__file__)

        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://oldap.org/test#")
        cls._context['dmtest'] = NamespaceIRI('http://oldap.org/dmtest#')
        cls._context.use('test', 'dmtest')

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="oldap",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        cls._connection.clear_graph(Xsd_QName('dmtest:shacl'))
        cls._connection.clear_graph(Xsd_QName('dmtest:onto'))

        file = project_root / 'oldaplib' / 'testdata' / 'connection_test.trig'
        cls._connection.upload_turtle(file)


        sleep(1)  # upload may take a while...

        cls._project = Project.read(cls._connection, "test")
        cls._dmproject = Project.read(cls._connection, "dmtest")
        cls._sysproject = Project.read(cls._connection, "oldap")


    def tearDown(self):
        pass

    def generate_a_datamodel(self, project: Project) -> DataModel:
        dm_name = project.projectShortName
        #
        # define an external standalone property
        #
        comment = PropertyClass(con=self._connection,
                                project=self._dmproject,
                                property_class_iri=Iri(f'{dm_name}:comment'),
                                datatype=XsdDatatypes.langString,
                                name=LangString(["Comment@en", "Kommentar@de"]),
                                uniqueLang=Xsd_boolean(True),
                                languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        comment.force_external()

        #
        # Define the properties for the "Book"
        #
        title = PropertyClass(con=self._connection,
                              project=self._dmproject,
                              property_class_iri=Iri(f'{dm_name}:title'),
                              datatype=XsdDatatypes.langString,
                              name=LangString(["Title@en", "Titel@de"]),
                              description=LangString(["Title of book@en", "Titel des Buches@de"]),
                              minCount=Xsd_integer(1),
                              uniqueLang=Xsd_boolean(True),
                              languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                              order=Xsd_decimal(1))

        authors = PropertyClass(con=self._connection,
                                project=self._dmproject,
                                property_class_iri=Iri(f'{dm_name}:authors'),
                                toNodeIri=Iri('oldap:Person'),
                                name=LangString(["Author(s)@en", "Autor(en)@de"]),
                                description=LangString(["Writers of the Book@en", "Schreiber*innen des Buchs@de"]),
                                minCount=Xsd_integer(1),
                                order=Xsd_decimal(2))

        book = ResourceClass(con=self._connection,
                             project=self._dmproject,
                             owlclass_iri=Iri(f'{dm_name}:Book'),
                             label=LangString(["Book@en", "Buch@de"]),
                             comment=LangString("Ein Buch mit Seiten@en"),
                             closed=Xsd_boolean(True),
                             properties=[title, authors, comment])

        pagenum = PropertyClass(con=self._connection,
                                project=self._dmproject,
                                property_class_iri=Iri(f'{dm_name}:pagenum'),
                                datatype=XsdDatatypes.int,
                                name=LangString(["Pagenumber@en", "Seitennummer@de"]),
                                maxCount=Xsd_integer(1),
                                minCount=Xsd_integer(1),
                                order=Xsd_decimal(1))

        inbook = PropertyClass(con=self._connection,
                               project=self._dmproject,
                               property_class_iri=Iri(f'{dm_name}:inbook'),
                               toNodeIri=Iri(f'{dm_name}:Book'),
                               name=LangString(["Pagenumber@en", "Seitennummer@de"]),
                               maxCount=Xsd_integer(1),
                               minCount=Xsd_integer(1),
                               order=Xsd_decimal(1))

        page = ResourceClass(con=self._connection,
                             project=self._dmproject,
                             owlclass_iri=Iri(f'{dm_name}:Page'),
                             label=LangString(["Page@en", "Seite@de"]),
                             comment=LangString("Page of a book@en"),
                             closed=Xsd_boolean(True),
                             properties=[pagenum, inbook, comment])

        dm = DataModel(con=self._connection,
                       project=self._dmproject,
                       propclasses=[comment],
                       resclasses=[book, page])
        return dm

    # @unittest.skip('Work in progress')
    def test_datamodel_constructor(self):
        dm_name = self._dmproject.projectShortName

        dm = self.generate_a_datamodel(self._dmproject)
        dm.create()

        del dm

        dm2 = DataModel.read(con=self._connection, project=self._dmproject)
        p1 = dm2[Iri(f'{dm_name}:comment')]
        self.assertEqual(p1.datatype, XsdDatatypes.langString)
        self.assertEqual(p1.name, LangString(["Comment@en", "Kommentar@de"]))
        self.assertEqual(p1.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(p1.uniqueLang)

        r1 = dm2[Iri(f'{dm_name}:Book')]

        r1p1 = r1[Iri(f'{dm_name}:title')]
        self.assertEqual(r1p1.internal, Iri(f'{dm_name}:Book'))
        self.assertEqual(r1p1.datatype, XsdDatatypes.langString)
        self.assertEqual(r1p1.name, LangString(["Title@en", "Titel@de"]))
        self.assertEqual(r1p1.description, LangString(["Title of book@en", "Titel des Buches@de"]))
        self.assertEqual(r1p1.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(r1p1.uniqueLang)
        self.assertEqual(r1p1.minCount, Xsd_integer(1))
        self.assertEqual(r1p1.order, Xsd_decimal(1))

        r1p2 = r1[Iri(f'{dm_name}:authors')]
        self.assertEqual(r1p2.internal, Iri(f'{dm_name}:Book'))
        self.assertEqual(r1p2.toNodeIri, Iri('oldap:Person'))
        self.assertEqual(r1p2.name, LangString(["Author(s)@en", "Autor(en)@de"]))
        self.assertEqual(r1p2.description, LangString(["Writers of the Book@en", "Schreiber*innen des Buchs@de"]))
        self.assertEqual(r1p2.minCount, Xsd_integer(1))
        self.assertEqual(r1p2.order, Xsd_decimal(2))

        r1p3 = r1[Iri(f'{dm_name}:comment')]
        self.assertIsNone(r1p3.internal)
        self.assertEqual(r1p3.datatype, XsdDatatypes.langString)
        self.assertEqual(r1p3.name, LangString(["Comment@en", "Kommentar@de"]))
        self.assertTrue(r1p3.uniqueLang, Xsd_boolean(True))
        self.assertEqual(r1p3.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        r2 = dm2[Iri(f'{dm_name}:Page')]
        r2p1 = r2[Iri(f'{dm_name}:pagenum')]
        self.assertEqual(r2p1.internal, Iri(f'{dm_name}:Page'))
        self.assertEqual(r2p1.datatype, XsdDatatypes.int)
        self.assertEqual(r2p1.name, LangString(["Pagenumber@en", "Seitennummer@de"]))
        self.assertEqual(r2p1.maxCount, Xsd_integer(1))
        self.assertEqual(r2p1.minCount, Xsd_integer(1))

        r2p2 = r2[Iri(f'{dm_name}:inbook')]
        self.assertEqual(r2p2.internal, Iri(f'{dm_name}:Page'))
        self.assertEqual(r2p2[PropClassAttr.TO_NODE_IRI], Iri(f'{dm_name}:Book'))
        self.assertEqual(r2p2[PropClassAttr.NAME], LangString(["Pagenumber@en", "Seitennummer@de"]))
        self.assertEqual(r2p2[PropClassAttr.MAX_COUNT], Xsd_integer(1))
        self.assertEqual(r2p2[PropClassAttr.MIN_COUNT], Xsd_integer(1))
        self.assertEqual(r2p2[PropClassAttr.ORDER], Xsd_decimal(1))

        r2p3 = r1[Iri(f'{dm_name}:comment')]
        self.assertIsNone(r2p3.internal)
        self.assertEqual(r2p3.datatype, XsdDatatypes.langString)
        self.assertEqual(r2p3.name, LangString(["Comment@en", "Kommentar@de"]))
        self.assertTrue(r2p3.uniqueLang, Xsd_boolean(True))
        self.assertEqual(r2p3.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

    # @unittest.skip('Work in progress')
    def test_datamodel_read(self):
        model = DataModel.read(self._connection, self._sysproject)
        print(model.get_propclasses())
        self.assertEqual(set(model.get_propclasses()), {
            Iri("oldap:test"),
            Iri("dcterms:creator"),
            Iri("rdfs:label"),
            Iri("rdfs:comment"),
            Iri("dcterms:created"),
            Iri("dcterms:contributor"),
            Iri("dcterms:modified")
        })
        self.assertTrue(set(model.get_resclasses()) == {
            Iri("oldap:Project"),
            Iri("oldap:User"),
            Iri("oldap:OldapList"),
            Iri("oldap:OldapListNode"),
            Iri("oldap:AdminPermission"),
            Iri("oldap:DataPermission"),
            Iri("oldap:PermissionSet"),
            Iri("oldap:Thing")
        })

    # @unittest.skip('Work in progress')
    def test_datamodel_modify_A(self):
        dm_name = self._dmproject.projectShortName

        dm = self.generate_a_datamodel(self._dmproject)
        dm.create()
        dm = DataModel.read(self._connection, self._dmproject)

        #
        # define an external standalone property
        #
        pubyear = PropertyClass(con=self._connection,
                                project=self._dmproject,
                                property_class_iri=Xsd_QName(f'{dm_name}:pubYear'),
                                datatype=XsdDatatypes.gYear,
                                name=LangString(["Publication Year@en", "Publicationsjahr@de"]),
                                maxCount=Xsd_integer(1))
        pubyear.force_external()
        dm[Iri(f'{dm_name}:pubYear')] = pubyear
        self.assertEqual({Iri(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE)}, dm.changeset)

        dm[Iri(f'{dm_name}:comment')].name[Language.FR] = 'Commentaire'
        self.assertEqual({
            Iri(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE),
            Iri(f'{dm_name}:comment'): PropertyClassChange(None, Action.MODIFY)
        }, dm.changeset)

        dm[Iri(f'{dm_name}:Book')][Iri(f'{dm_name}:authors')].name[Language.FR] = "Ecrivain(s)"
        self.assertEqual({
            Iri(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE),
            Iri(f'{dm_name}:comment'): PropertyClassChange(None, Action.MODIFY),
            Iri(f'{dm_name}:Book'): ResourceClassChange(None, Action.MODIFY)
        }, dm.changeset)

        del dm[Iri(f'{dm_name}:Page')][Iri(f'{dm_name}:comment')]

        self.assertEqual({
            Iri(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE),
            Iri(f'{dm_name}:comment'): PropertyClassChange(None, Action.MODIFY),
            Iri(f'{dm_name}:Book'): ResourceClassChange(None, Action.MODIFY),
            Iri(f'{dm_name}:Page'): ResourceClassChange(None, Action.MODIFY)
        }, dm.changeset)

        pagename = PropertyClass(con=self._connection,
                                 #graph=dm_name,
                                 project=self._dmproject,
                                 property_class_iri=Xsd_QName(f'{dm_name}:pageName'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString(["Page name@en", "Seitenbezeichnung@de"]),
                                 maxCount=Xsd_integer(1),
                                 minCount=Xsd_integer(1))

        dm[Iri(f'{dm_name}:Page')][Iri(f'{dm_name}:pageName')] = pagename
        self.assertEqual({
            Iri(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE),
            Iri(f'{dm_name}:comment'): PropertyClassChange(None, Action.MODIFY),
            Iri(f'{dm_name}:Book'): ResourceClassChange(None, Action.MODIFY),
            Iri(f'{dm_name}:Page'): ResourceClassChange(None, Action.MODIFY)
        }, dm.changeset)

    # @unittest.skip('Work in progress')
    def test_datamodel_modify_B(self):
        dm_name = self._dmproject.projectShortName

        dm = self.generate_a_datamodel(self._dmproject)
        dm.create()
        del dm

        dm = DataModel.read(self._connection, self._dmproject)

        #
        # define an external standalone property
        #
        pubyear = PropertyClass(con=self._connection,
                                project=self._dmproject,
                                property_class_iri=Xsd_QName(f'{dm_name}:pubYear'),
                                datatype=XsdDatatypes.gYear,
                                name=LangString(["Publication Year@en", "Publicationsjahr@de"]),
                                maxCount=Xsd_integer(1))
        pubyear.force_external()

        dm[Iri(f'{dm_name}:pubYear')] = pubyear
        dm[Iri(f'{dm_name}:comment')][PropClassAttr.NAME][Language.FR] = 'Commentaire'
        dm[Iri(f'{dm_name}:Book')][Iri(f'{dm_name}:authors')].name[Language.FR] = "Ecrivain(s)"
        del dm[Iri(f'{dm_name}:Page')][Iri(f'{dm_name}:comment')]

        pagename = PropertyClass(con=self._connection,
                                 #graph=dm_name,
                                 project=self._dmproject,
                                 property_class_iri=Xsd_QName(f'{dm_name}:pageName'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString(["Page name@en", "Seitenbezeichnung@de"]),
                                 maxCount=Xsd_integer(1),
                                 minCount=Xsd_integer(1))

        dm[Iri(f'{dm_name}:Page')][Iri(f'{dm_name}:pageName')] = pagename

        dm.update()

        del dm

        dm = DataModel.read(self._connection, self._dmproject)
        self.assertIsNotNone(dm.get(Iri(f'{dm_name}:pubYear')))
        self.assertEqual(dm[Iri(f'{dm_name}:pubYear')].datatype, XsdDatatypes.gYear)
        self.assertEqual(dm[Iri(f'{dm_name}:pubYear')].maxCount, 1)
        self.assertEqual(dm[Iri(f'{dm_name}:comment')].name[Language.FR], 'Commentaire')
        self.assertEqual(dm[Iri(f'{dm_name}:Book')][Iri(f'{dm_name}:authors')].name[Language.FR], "Ecrivain(s)")
        self.assertIsNotNone(dm[Iri(f'{dm_name}:Page')][Iri(f'{dm_name}:pageName')])
        self.assertIsNone(dm[Iri(f'{dm_name}:Page')].get(Iri(f'{dm_name}:comment')))

    def test_write_trig(self):
        pagename = PropertyClass(con=self._connection,
                                 project=self._project,
                                 property_class_iri=Iri('test:pageDesignation'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString("Page designation@en", "Seitenbezeichnung@de"),
                                 minCount=Xsd_integer(1),
                                 order=Xsd_decimal(1))
        pagenum = PropertyClass(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:pageNum'),
                                datatype=XsdDatatypes.positiveInteger,
                                name=LangString("Pagenumber@en", "Seitennummer@de"),
                                description=LangString("consecutive numbering of pages@en", "Konsekutive Nummerierung der Seiten@de"),
                                minCount=Xsd_integer(1),
                                maxCount=Xsd_integer(1),
                                order=Xsd_decimal(2))
        pagedescription = PropertyClass(con=self._connection,
                                        project=self._project,
                                        property_class_iri=Iri('test:pageDescription'),
                                        datatype=XsdDatatypes.langString,
                                        languageIn=LanguageIn(Language.EN, Language.DE),
                                        uniqueLang=Xsd_boolean(True),
                                        order=Xsd_decimal(3))
        content = PropertyClass(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:pageContent'),
                                datatype=XsdDatatypes.string,
                                maxCount=Xsd_integer(1),
                                order=Xsd_decimal(4))
        inBook = PropertyClass(con=self._connection,
                               project=self._project,
                               property_class_iri=Iri('test:pageInBook'),
                               toNodeIri=Iri('test:Book'),
                               minCount=Xsd_integer(1),
                               maxCount=Xsd_integer(1),
                               order=Xsd_decimal(5))
        page = ResourceClass(con=self._connection,
                             project=self._project,
                             owlclass_iri=Iri("test:Page"),
                             superclass=Iri('oldap:Thing'),
                             label=LangString(["Project@en", "Projekt@de"]),
                             comment=LangString(["A page of a book@en", "Seite eines Buches@de"]),
                             closed=Xsd_boolean(True),
                             properties=[pagename, pagenum, pagedescription, content, inBook])

        title = PropertyClass(con=self._connection,
                              project=self._project,
                              property_class_iri=Iri('test:title'),
                              datatype=XsdDatatypes.string,
                              minCount=Xsd_integer(1),
                              maxCount=Xsd_integer(1),
                              order=Xsd_decimal(1))
        author = PropertyClass(con=self._connection,
                               project=self._project,
                               property_class_iri=Iri('test:author'),
                               toNodeIri=Iri('test:Person'),
                               order=Xsd_decimal(2))
        pubDate = PropertyClass(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:pubDate'),
                                datatype=XsdDatatypes.date,
                                minCount=Xsd_integer(1),
                                maxCount=Xsd_integer(1),
                                order=Xsd_decimal(3))
        book = ResourceClass(con=self._connection,
                             project=self._project,
                             owlclass_iri=Iri('test:Book'),
                             superclass=Iri('oldap:Thing'),
                             label=LangString(["Book@en", "Buch@de"]),
                             closed=Xsd_boolean(True),
                             properties=[title, author, pubDate])

        person = ResourceClass(con=self._connection,
                               project=self._project,
                               owlclass_iri=Iri('test:Person'),
                               superclass=Iri('oldap:Thing'),
                               label=LangString(["Person@en", "Person@de"]),
                               properties=[title, author, pubDate])

        dm = DataModel(con=self._connection,
                       project=self._project,
                       resclasses=[page, book])
        dm.write_as_trig('gaga.trig')


