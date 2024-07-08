import unittest
from pathlib import Path
from pprint import pprint
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
from oldaplib.src.hasproperty import HasProperty


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
                              uniqueLang=Xsd_boolean(True),
                              languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        authors = PropertyClass(con=self._connection,
                                project=self._dmproject,
                                property_class_iri=Iri(f'{dm_name}:authors'),
                                toClass=Iri('oldap:Person'),
                                name=LangString(["Author(s)@en", "Autor(en)@de"]),
                                description=LangString(["Writers of the Book@en", "Schreiber*innen des Buchs@de"]))

        book = ResourceClass(con=self._connection,
                             project=self._dmproject,
                             owlclass_iri=Iri(f'{dm_name}:Book'),
                             label=LangString(["Book@en", "Buch@de"]),
                             comment=LangString("Ein Buch mit Seiten@en"),
                             closed=Xsd_boolean(True),
                             hasproperties=[
                                 HasProperty(con=self._connection, prop=title, minCount=Xsd_integer(1), order=1),
                                 HasProperty(con=self._connection, prop=authors, minCount=Xsd_integer(1), order=2),
                                 HasProperty(con=self._connection, prop=comment, order=3)])

        pagenum = PropertyClass(con=self._connection,
                                project=self._dmproject,
                                property_class_iri=Iri(f'{dm_name}:pagenum'),
                                datatype=XsdDatatypes.int,
                                name=LangString(["Pagenumber@en", "Seitennummer@de"]))

        inbook = PropertyClass(con=self._connection,
                               project=self._dmproject,
                               property_class_iri=Iri(f'{dm_name}:inbook'),
                               toClass=Iri(f'{dm_name}:Book'),
                               name=LangString(["Pagenumber@en", "Seitennummer@de"]))

        page = ResourceClass(con=self._connection,
                             project=self._dmproject,
                             owlclass_iri=Iri(f'{dm_name}:Page'),
                             label=LangString(["Page@en", "Seite@de"]),
                             comment=LangString("Page of a book@en"),
                             closed=Xsd_boolean(True),
                             hasproperties=[
                                 HasProperty(con=self._connection, prop=pagenum, maxCount=Xsd_integer(1), minCount=Xsd_integer(1), order=1),
                                 HasProperty(con=self._connection, prop=inbook, maxCount=Xsd_integer(1), minCount=Xsd_integer(1), order=2),
                                 HasProperty(con=self._connection, prop=comment, order=3)])

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
        self.assertEqual(r1p1.prop.internal, Iri(f'{dm_name}:Book'))
        self.assertEqual(r1p1.prop.datatype, XsdDatatypes.langString)
        self.assertEqual(r1p1.prop.name, LangString(["Title@en", "Titel@de"]))
        self.assertEqual(r1p1.prop.description, LangString(["Title of book@en", "Titel des Buches@de"]))
        self.assertEqual(r1p1.prop.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(r1p1.prop.uniqueLang)
        self.assertEqual(r1p1.minCount, Xsd_integer(1))
        self.assertEqual(r1p1.order, Xsd_decimal(1))

        r1p2 = r1[Iri(f'{dm_name}:authors')]
        self.assertEqual(r1p2.prop.internal, Iri(f'{dm_name}:Book'))
        self.assertEqual(r1p2.prop.toClass, Iri('oldap:Person'))
        self.assertEqual(r1p2.prop.name, LangString(["Author(s)@en", "Autor(en)@de"]))
        self.assertEqual(r1p2.prop.description, LangString(["Writers of the Book@en", "Schreiber*innen des Buchs@de"]))
        self.assertEqual(r1p2.minCount, Xsd_integer(1))
        self.assertEqual(r1p2.order, Xsd_decimal(2))

        r1p3 = r1[Iri(f'{dm_name}:comment')]
        self.assertIsNone(r1p3.prop.internal)
        self.assertEqual(r1p3.prop.datatype, XsdDatatypes.langString)
        self.assertEqual(r1p3.prop.name, LangString(["Comment@en", "Kommentar@de"]))
        self.assertTrue(r1p3.prop.uniqueLang, Xsd_boolean(True))
        self.assertEqual(r1p3.prop.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertEqual(r1p3.order, Xsd_decimal(3))

        r2 = dm2[Iri(f'{dm_name}:Page')]
        r2p1 = r2[Iri(f'{dm_name}:pagenum')]
        self.assertEqual(r2p1.prop.internal, Iri(f'{dm_name}:Page'))
        self.assertEqual(r2p1.prop.datatype, XsdDatatypes.int)
        self.assertEqual(r2p1.prop.name, LangString(["Pagenumber@en", "Seitennummer@de"]))
        self.assertEqual(r2p1.maxCount, Xsd_integer(1))
        self.assertEqual(r2p1.minCount, Xsd_integer(1))

        r2p2 = r2[Iri(f'{dm_name}:inbook')]
        self.assertEqual(r2p2.prop.internal, Iri(f'{dm_name}:Page'))
        self.assertEqual(r2p2.prop[PropClassAttr.CLASS], Iri(f'{dm_name}:Book'))
        self.assertEqual(r2p2.prop[PropClassAttr.NAME], LangString(["Pagenumber@en", "Seitennummer@de"]))
        self.assertEqual(r2p2.maxCount, Xsd_integer(1))
        self.assertEqual(r2p2.minCount, Xsd_integer(1))
        self.assertEqual(r2p2.order, Xsd_decimal(2))

        r2p3 = r1[Iri(f'{dm_name}:comment')]
        self.assertIsNone(r2p3.prop.internal)
        self.assertEqual(r2p3.prop.datatype, XsdDatatypes.langString)
        self.assertEqual(r2p3.prop.name, LangString(["Comment@en", "Kommentar@de"]))
        self.assertTrue(r2p3.prop.uniqueLang, Xsd_boolean(True))
        self.assertEqual(r2p3.prop.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

    # @unittest.skip('Work in progress')
    def test_datamodel_read(self):
        model = DataModel.read(self._connection, self._sysproject)
        self.assertEqual(set(model.get_propclasses()), {
            Iri("oldap:test"),
            Iri("dcterms:creator"),
            Iri("rdfs:label"),
            Iri("rdfs:comment"),
            Iri("dcterms:created"),
            Iri("dcterms:contributor"),
            Iri("dcterms:modified"),
            Iri("foaf:givenName"),
            Iri("foaf:familyName")
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
                                property_class_iri=Iri(f'{dm_name}:pubYear'),
                                datatype=XsdDatatypes.gYear,
                                name=LangString(["Publication Year@en", "Publicationsjahr@de"]))
        pubyear.force_external()
        dm[Iri(f'{dm_name}:pubYear')] = pubyear
        self.assertEqual({Iri(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE)}, dm.changeset)

        dm[Iri(f'{dm_name}:comment')].name[Language.FR] = 'Commentaire'
        self.assertEqual({
            Iri(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE),
            Iri(f'{dm_name}:comment'): PropertyClassChange(None, Action.MODIFY)
        }, dm.changeset)

        dm[Iri(f'{dm_name}:Book')][Iri(f'{dm_name}:authors')].prop.name[Language.FR] = "Ecrivain(s)"
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
                                 name=LangString(["Page name@en", "Seitenbezeichnung@de"]))

        dm[Iri(f'{dm_name}:Page')][Iri(f'{dm_name}:pageName')] = HasProperty(con=self._connection, prop=pagename, maxCount=1, minCount=1)
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
        # define a standalone property and add it to the datamodel
        #
        pubyear = PropertyClass(con=self._connection,
                                project=self._dmproject,
                                property_class_iri=Xsd_QName(f'{dm_name}:pubYear'),
                                datatype=XsdDatatypes.gYear,
                                name=LangString(["Publication Year@en", "Publicationsjahr@de"]))
        pubyear.force_external()
        dm[Iri(f'{dm_name}:pubYear')] = pubyear

        #
        # Modify a standalone property
        #
        dm[Iri(f'{dm_name}:comment')][PropClassAttr.NAME][Language.FR] = 'Commentaire'

        #
        # Modify an internal property
        #
        dm[Iri(f'{dm_name}:Book')][Iri(f'{dm_name}:authors')].prop.name[Language.FR] = "Ecrivain(s)"

        #
        # Add a new property as internal property
        #
        pagename = PropertyClass(con=self._connection,
                                 project=self._dmproject,
                                 property_class_iri=Iri(f'{dm_name}:pageName'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString(["Page name@en", "Seitenbezeichnung@de"]))

        dm[Iri(f'{dm_name}:Page')][Iri(f'{dm_name}:pageName')] = HasProperty(con=self._connection, prop=pagename)

        dm.update()

        del dm

        dm = DataModel.read(self._connection, self._dmproject)
        self.assertIsNotNone(dm.get(Iri(f'{dm_name}:pubYear')))
        self.assertEqual(dm[Iri(f'{dm_name}:pubYear')].datatype, XsdDatatypes.gYear)
        self.assertEqual(dm[Iri(f'{dm_name}:comment')].name[Language.FR], 'Commentaire')
        self.assertEqual(dm[Iri(f'{dm_name}:Book')][Iri(f'{dm_name}:authors')].prop.name[Language.FR], "Ecrivain(s)")
        self.assertIsNotNone(dm[Iri(f'{dm_name}:Page')][Iri(f'{dm_name}:pageName')])

    def test_datamodel_modify_C(self):
        dm_name = self._dmproject.projectShortName

        dm = self.generate_a_datamodel(self._dmproject)
        dm.create()
        del dm

        dm = DataModel.read(self._connection, self._dmproject)

        #
        # remove the comment property from the Page resource
        #
        del dm[Iri(f'{dm_name}:Page')][Iri(f'{dm_name}:comment')]

        dm.update()

        del dm

        dm = DataModel.read(self._connection, self._dmproject)
        print(str(dm[Iri(f'{dm_name}:Page')].get(Iri(f'{dm_name}:comment'))))
        self.assertIsNone(dm[Iri(f'{dm_name}:Page')].get(Iri(f'{dm_name}:comment')))  # TODO THIS TEST SHOULD PASS!!!!

    def test_incremental_generation(self):
        dm = DataModel(con=self._connection,
                       project=self._dmproject)
        dm.create()
        dm = DataModel.read(self._connection, self._dmproject)
        dm_name = self._dmproject.projectShortName

        #
        # add a standalone property
        #
        generic_comment = PropertyClass(con=self._connection,
                                 project=self._dmproject,
                                 property_class_iri=Iri(f'{dm_name}:genericComment'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString(["Generic comment@en", "Allgemeiner Kommentar@de"]))
        dm[Iri(f'{dm_name}:genericComment')] = generic_comment
        dm.update()
        dm = DataModel.read(self._connection, self._dmproject)
        p1 = dm[Iri(f'{dm_name}:genericComment')]
        self.assertEqual(p1.datatype, XsdDatatypes.string)

        #
        # Modifying the property
        #
        p1.description = LangString("For testing purposes only@en")
        dm.update()
        dm = DataModel.read(self._connection, self._dmproject)
        p1 = dm[Iri(f'{dm_name}:genericComment')]
        self.assertEqual(p1.datatype, XsdDatatypes.string)
        self.assertEqual(p1.description, LangString("For testing purposes only@en"))

        #
        # Add a resource
        #
        titleX = PropertyClass(con=self._connection,
                               project=self._dmproject,
                               property_class_iri=Iri(f'{dm_name}:titleX'),
                               datatype=XsdDatatypes.langString,
                               name=LangString(["TitleX@en", "TitelX@de"]),
                               description=LangString(["TitleX of book@en", "TitelX des Buches@de"]),
                               uniqueLang=Xsd_boolean(True),
                               languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        authorsX = PropertyClass(con=self._connection,
                                 project=self._dmproject,
                                 property_class_iri=Iri(f'{dm_name}:authorsX'),
                                 toClass=Iri('oldap:Person'),
                                 name=LangString(["Author(s)X@en", "Autor(en)X@de"]),
                                 description=LangString(["Writers of the BookX@en", "Schreiber*innen des BuchsX@de"]))

        bookX = ResourceClass(con=self._connection,
                              project=self._dmproject,
                              owlclass_iri=Iri(f'{dm_name}:BookX'),
                              label=LangString(["BookX@en", "BuchX@de"]),
                              comment=LangString("Ein Buch mit SeitenX@en"),
                              closed=Xsd_boolean(True),
                              hasproperties=[
                                  HasProperty(con=self._connection, prop=titleX, minCount=Xsd_integer(1), order=1),
                                  HasProperty(con=self._connection, prop=authorsX, minCount=Xsd_integer(1), order=2),
                                  HasProperty(con=self._connection, prop=Iri(f'{dm_name}:genericComment'), order=3)])
        dm[Iri(f'{dm_name}:BookX')] = bookX
        dm.update()

        dm = DataModel.read(self._connection, self._dmproject)

        p1 = dm[Iri(f'{dm_name}:genericComment')]
        self.assertEqual(p1.datatype, XsdDatatypes.string)
        self.assertEqual(p1.description, LangString("For testing purposes only@en"))

        r1 = dm[Iri(f'{dm_name}:BookX')]

        r1p1 = r1[Iri(f'{dm_name}:titleX')]
        self.assertEqual(r1p1.prop.internal, Iri(f'{dm_name}:BookX'))
        self.assertEqual(r1p1.prop.datatype, XsdDatatypes.langString)
        self.assertEqual(r1p1.prop.name, LangString(["TitleX@en", "TitelX@de"]))
        self.assertEqual(r1p1.prop.description, LangString(["TitleX of book@en", "TitelX des Buches@de"]))
        self.assertEqual(r1p1.prop.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(r1p1.prop.uniqueLang)
        self.assertEqual(r1p1.minCount, Xsd_integer(1))
        self.assertEqual(r1p1.order, Xsd_decimal(1))

        r1p2 = r1[Iri(f'{dm_name}:authorsX')]
        self.assertEqual(r1p2.prop.internal, Iri(f'{dm_name}:BookX'))
        self.assertEqual(r1p2.prop.toClass, Iri('oldap:Person'))
        self.assertEqual(r1p2.prop.name, LangString(["Author(s)X@en", "Autor(en)X@de"]))
        self.assertEqual(r1p2.prop.description, LangString(["Writers of the BookX@en", "Schreiber*innen des BuchsX@de"]))
        self.assertEqual(r1p2.minCount, Xsd_integer(1))
        self.assertEqual(r1p2.order, Xsd_decimal(2))

        r1p3 = r1[Iri(f'{dm_name}:genericComment')]
        self.assertIsNone(r1p3.prop.internal)
        self.assertEqual(r1p3.prop.datatype, XsdDatatypes.string)
        self.assertEqual(r1p3.prop.name, LangString(["Generic comment@en", "Allgemeiner Kommentar@de"]))
        self.assertEqual(r1p3.order, Xsd_decimal(3))


    def test_update_parts(self):
        dm_name = self._dmproject.projectShortName
        generic_commentY = PropertyClass(con=self._connection,
                                         project=self._dmproject,
                                         property_class_iri=Iri(f'{dm_name}:genericCommentY'),
                                         datatype=XsdDatatypes.string,
                                         name=LangString(["Generic commentY@en", "Allgemeiner KommentarY@de"]))
        generic_commentY.force_external()

        titleY = PropertyClass(con=self._connection,
                               project=self._dmproject,
                               property_class_iri=Iri(f'{dm_name}:titleY'),
                               datatype=XsdDatatypes.langString,
                               name=LangString(["TitleY@en", "TitelY@de"]),
                               description=LangString(["TitleY of book@en", "TitelY des Buches@de"]),
                               uniqueLang=Xsd_boolean(True),
                               languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        authorsY = PropertyClass(con=self._connection,
                                 project=self._dmproject,
                                 property_class_iri=Iri(f'{dm_name}:authorsY'),
                                 toClass=Iri('oldap:Person'),
                                 name=LangString(["Author(s)Y@en", "Autor(en)Y@de"]),
                                 description=LangString(["Writers of the BookY@en", "Schreiber*innen des BuchsY@de"]))

        bookY = ResourceClass(con=self._connection,
                              project=self._dmproject,
                              owlclass_iri=Iri(f'{dm_name}:BookY'),
                              label=LangString(["BookY@en", "BuchY@de"]),
                              comment=LangString("Ein Buch mit SeitenY@en"),
                              closed=Xsd_boolean(True),
                              hasproperties=[
                                  HasProperty(con=self._connection, prop=titleY, minCount=Xsd_integer(1), order=1),
                                  HasProperty(con=self._connection, prop=authorsY, minCount=Xsd_integer(1), order=2),
                                  HasProperty(con=self._connection, prop=generic_commentY, order=3)])

        dm = DataModel(con=self._connection,
                       project=self._dmproject,
                       propclasses=[generic_commentY],
                       resclasses=[bookY])
        dm.create()

        dm = DataModel.read(self._connection, self._dmproject)

        #
        # a few check's if the creation of the datamodel worked as expected...
        #
        p1 = dm[Iri(f'{dm_name}:genericCommentY')]
        self.assertEqual(p1.datatype, XsdDatatypes.string)
        self.assertEqual(p1.name, LangString(["Generic commentY@en", "Allgemeiner KommentarY@de"]))
        self.assertIsNone(p1.internal)

        r1 = dm[Iri(f'{dm_name}:BookY')]

        r1p1 = r1[Iri(f'{dm_name}:titleY')]
        self.assertEqual(r1p1.prop.internal, Iri(f'{dm_name}:BookY'))
        self.assertEqual(r1p1.prop.datatype, XsdDatatypes.langString)
        self.assertEqual(r1p1.prop.name, LangString(["TitleY@en", "TitelY@de"]))
        self.assertEqual(r1p1.prop.description, LangString(["TitleY of book@en", "TitelY des Buches@de"]))
        self.assertEqual(r1p1.prop.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(r1p1.prop.uniqueLang)
        self.assertEqual(r1p1.minCount, Xsd_integer(1))
        self.assertEqual(r1p1.order, Xsd_decimal(1))

        r1p2 = r1[Iri(f'{dm_name}:authorsY')]
        self.assertEqual(r1p2.prop.internal, Iri(f'{dm_name}:BookY'))
        self.assertEqual(r1p2.prop.toClass, Iri('oldap:Person'))
        self.assertEqual(r1p2.prop.name, LangString(["Author(s)Y@en", "Autor(en)Y@de"]))
        self.assertEqual(r1p2.prop.description, LangString(["Writers of the BookY@en", "Schreiber*innen des BuchsY@de"]))
        self.assertEqual(r1p2.minCount, Xsd_integer(1))
        self.assertEqual(r1p2.order, Xsd_decimal(2))

        r1p3 = r1[Iri(f'{dm_name}:genericCommentY')]
        self.assertIsNone(r1p3.prop.internal)
        self.assertEqual(r1p3.prop.datatype, XsdDatatypes.string)
        self.assertEqual(r1p3.prop.name, LangString(["Generic commentY@en", "Allgemeiner KommentarY@de"]))
        self.assertEqual(r1p3.order, Xsd_decimal(3))

        #
        # Change name of genericCommentY, accessed by resource BookY
        #
        dm[Iri(f'{dm_name}:genericCommentY')].name[Language.IT] = "Commentario"

        #
        # Add a field to standalone property
        #
        dm[Iri(f'{dm_name}:genericCommentY')].description = LangString("DescriptionY@en", "Beschreibung@de")


        #
        # Add a new property
        #
        pubDateY = PropertyClass(con=self._connection,
                                 project=self._project,
                                 property_class_iri=Iri(f'{dm_name}:pubDateY'),
                                 datatype=XsdDatatypes.date)
        dm[Iri(f'{dm_name}:BookY')][Iri(f'{dm_name}:pubDateY')] = HasProperty(con=self._connection, prop=pubDateY)

        #
        # Delete a property
        #
        del dm[Iri(f'{dm_name}:BookY')][Iri(f'{dm_name}:authorsY')]

        dm.update()
        dm = DataModel.read(self._connection, self._dmproject)
        r1 = dm[Iri(f'{dm_name}:BookY')]
        r1p3 = r1[Iri(f'{dm_name}:genericCommentY')]
        self.assertEqual(r1p3.prop.name, LangString(["Generic commentY@en", "Allgemeiner KommentarY@de", "Commentario@it"]))
        self.assertEqual(r1p3.prop.description, LangString("DescriptionY@en", "Beschreibung@de"))
        self.assertIsNotNone(dm[Iri(f'{dm_name}:BookY')][Iri(f'{dm_name}:pubDateY')])
        self.assertIsNone(dm[Iri(f'{dm_name}:BookY')][Iri(f'{dm_name}:authorsY')])

        #
        # delete a complete resource
        #
        del dm[Iri(f'{dm_name}:BookY')]
        dm.update()
        self.assertIsNone(dm.get(Iri(f'{dm_name}:BookY')))

        #
        # delete standalone property
        #
        del dm[Iri(f'{dm_name}:genericCommentY')]
        dm.update()
        self.assertIsNone(dm.get(Iri(f'{dm_name}:genericCommentY')))


    def test_write_trig(self):
        pagename = PropertyClass(con=self._connection,
                                 project=self._project,
                                 property_class_iri=Iri('test:pageDesignation'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString("Page designation@en", "Seitenbezeichnung@de"))
        pagenum = PropertyClass(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:pageNum'),
                                datatype=XsdDatatypes.positiveInteger,
                                name=LangString("Pagenumber@en", "Seitennummer@de"),
                                description=LangString("consecutive numbering of pages@en", "Konsekutive Nummerierung der Seiten@de"))
        pagedescription = PropertyClass(con=self._connection,
                                        project=self._project,
                                        property_class_iri=Iri('test:pageDescription'),
                                        datatype=XsdDatatypes.langString,
                                        languageIn=LanguageIn(Language.EN, Language.DE),
                                        uniqueLang=Xsd_boolean(True))
        content = PropertyClass(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:pageContent'),
                                datatype=XsdDatatypes.string)
        inBook = PropertyClass(con=self._connection,
                               project=self._project,
                               property_class_iri=Iri('test:pageInBook'),
                               toClass=Iri('test:Book'))
        page = ResourceClass(con=self._connection,
                             project=self._project,
                             owlclass_iri=Iri("test:Page"),
                             superclass=Iri('oldap:Thing'),
                             label=LangString(["Project@en", "Projekt@de"]),
                             comment=LangString(["A page of a book@en", "Seite eines Buches@de"]),
                             closed=Xsd_boolean(True),
                             hasproperties=[
                                 HasProperty(con=self._connection, prop=pagename, minCount=Xsd_integer(1), order=1),
                                 HasProperty(con=self._connection, prop=pagenum, minCount=Xsd_integer(1), maxCount=Xsd_integer(1), order=2),
                                 HasProperty(con=self._connection, prop=pagedescription, order=3),
                                 HasProperty(con=self._connection, prop=content, maxCount=Xsd_integer(1), order=4),
                                 HasProperty(con=self._connection, prop=inBook, minCount=Xsd_integer(1), maxCount=Xsd_integer(1), order=5)])

        title = PropertyClass(con=self._connection,
                              project=self._project,
                              property_class_iri=Iri('test:title'),
                              datatype=XsdDatatypes.string)
        author = PropertyClass(con=self._connection,
                               project=self._project,
                               property_class_iri=Iri('test:author'),
                               toClass=Iri('test:Person'))
        pubDate = PropertyClass(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:pubDate'),
                                datatype=XsdDatatypes.date)
        book = ResourceClass(con=self._connection,
                             project=self._project,
                             owlclass_iri=Iri('test:Book'),
                             superclass=Iri('oldap:Thing'),
                             label=LangString(["Book@en", "Buch@de"]),
                             closed=Xsd_boolean(True),
                             hasproperties=[
                                 HasProperty(con=self._connection, prop=title, order=1),
                                 HasProperty(con=self._connection, prop=author, order=2),
                                 HasProperty(con=self._connection, prop=pubDate, order=3)])

        person = ResourceClass(con=self._connection,
                               project=self._project,
                               owlclass_iri=Iri('test:Person'),
                               superclass=Iri('oldap:Thing'),
                               label=LangString(["Person@en", "Person@de"]),
                               hasproperties=[
                                   HasProperty(con=self._connection, prop=Iri('foaf:familyName'), minCount=Xsd_integer(1), maxCount=Xsd_integer(1), order=1),
                                   HasProperty(con=self._connection, prop=Iri('foaf:givenName'), minCount=Xsd_integer(1), order=2)])

        dm = DataModel(con=self._connection,
                       project=self._project,
                       resclasses=[page, book, person])
        dm.write_as_trig('gaga.trig')


