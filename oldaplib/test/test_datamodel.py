import json
import unittest
from copy import deepcopy
from pathlib import Path
from pprint import pprint
from time import sleep, time

from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel, PropertyClassChange, ResourceClassChange
from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.externalontology import ExternalOntology
from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.action import Action
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapError, OldapErrorAlreadyExists
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.enums.language import Language
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.enums.resourceclassattr import ResClassAttribute
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
    _sharedproject: Project

    @classmethod
    def setUp(cls):
        cache = CacheSingletonRedis()
        cache.clear()

        super().setUpClass()
        project_root = find_project_root(__file__)

        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://oldap.org/test#")
        cls._context['dmtest'] = NamespaceIRI('http://oldap.org/dmtest#')
        cls._context['dmtestA'] = NamespaceIRI('http://oldap.org/dmtestA#')
        cls._context['dmtestB'] = NamespaceIRI('http://oldap.org/dmtestB#')
        cls._context['dmtestC'] = NamespaceIRI('http://oldap.org/dmtestC#')
        cls._context['dmtestE'] = NamespaceIRI('http://oldap.org/dmtestE#')
        cls._context['dmtestF'] = NamespaceIRI('http://oldap.org/dmtestF#')
        cls._context['dmtestG'] = NamespaceIRI('http://oldap.org/dmtestG#')
        cls._context['dmtestH'] = NamespaceIRI('http://oldap.org/dmtestH#')
        cls._context['dmtestI'] = NamespaceIRI('http://oldap.org/dmtestI#')
        cls._context.use('test', 'dmtest', 'dmtestA', 'dmtestB', 'dmtestC', 'dmtestE', 'dmtestF', 'dmtestG', 'dmtestH', 'dmtestI')

        cls._connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        cls._connection.clear_graph(Xsd_QName('dmtest:shacl'))
        cls._connection.clear_graph(Xsd_QName('dmtest:onto'))
        cls._connection.clear_graph(Xsd_QName('dmtestA:shacl'))
        cls._connection.clear_graph(Xsd_QName('dmtestA:onto'))
        cls._connection.clear_graph(Xsd_QName('dmtestB:shacl'))
        cls._connection.clear_graph(Xsd_QName('dmtestB:onto'))
        cls._connection.clear_graph(Xsd_QName('dmtestC:shacl'))
        cls._connection.clear_graph(Xsd_QName('dmtestC:onto'))
        cls._connection.clear_graph(Xsd_QName('dmtestE:shacl'))
        cls._connection.clear_graph(Xsd_QName('dmtestE:onto'))
        cls._connection.clear_graph(Xsd_QName('dmtestF:shacl'))
        cls._connection.clear_graph(Xsd_QName('dmtestF:onto'))
        cls._connection.clear_graph(Xsd_QName('dmtestG:shacl'))
        cls._connection.clear_graph(Xsd_QName('dmtestG:onto'))
        cls._connection.clear_graph(Xsd_QName('dmtestH:shacl'))
        cls._connection.clear_graph(Xsd_QName('dmtestH:onto'))
        cls._connection.clear_graph(Xsd_QName('dmtestI:shacl'))
        cls._connection.clear_graph(Xsd_QName('dmtestI:onto'))
        cls._connection.clear_graph(Xsd_QName('hyha:shacl'))
        cls._connection.clear_graph(Xsd_QName('hyha:onto'))

        file = project_root / 'oldaplib' / 'testdata' / 'connection_test.trig'
        cls._connection.upload_turtle(file)

        cls._project = Project.read(cls._connection, "test", ignore_cache=True)
        cls._dmproject = Project.read(cls._connection, "dmtest", ignore_cache=True)
        cls._dmprojectA = Project.read(cls._connection, "dmtestA", ignore_cache=True)
        cls._dmprojectB = Project.read(cls._connection, "dmtestB", ignore_cache=True)
        cls._dmprojectC = Project.read(cls._connection, "dmtestC", ignore_cache=True)
        cls._dmprojectE = Project.read(cls._connection, "dmtestE", ignore_cache=True)
        cls._dmprojectF = Project.read(cls._connection, "dmtestF", ignore_cache=True)
        cls._dmprojectG = Project.read(cls._connection, "dmtestG", ignore_cache=True)
        cls._dmprojectH = Project.read(cls._connection, "dmtestH", ignore_cache=True)
        cls._dmprojectI = Project.read(cls._connection, "dmtestI", ignore_cache=True)
        cls._sysproject = Project.read(cls._connection, "oldap", ignore_cache=True)
        cls._sharedproject = Project.read(cls._connection, "shared", ignore_cache=True)


    def tearDown(self):
        pass

    def generate_a_datamodel(self, project: Project) -> DataModel:
        dm_name = project.projectShortName
        #
        # define an external standalone property
        #
        comment = PropertyClass(con=self._connection,
                                project=project,
                                property_class_iri=Xsd_QName(f'{dm_name}:comment'),
                                datatype=XsdDatatypes.langString,
                                name=LangString(["Comment@en", "Kommentar@de"]),
                                uniqueLang=Xsd_boolean(True),
                                languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        comment.force_external()

        #
        # Define the properties for the "Book"
        #
        title = PropertyClass(con=self._connection,
                              project=project,
                              property_class_iri=Xsd_QName(f'{dm_name}:title'),
                              datatype=XsdDatatypes.langString,
                              name=LangString(["Title@en", "Titel@de"]),
                              description=LangString(["Title of book@en", "Titel des Buches@de"]),
                              uniqueLang=Xsd_boolean(True),
                              languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        authors = PropertyClass(con=self._connection,
                                project=project,
                                property_class_iri=Xsd_QName(f'{dm_name}:authors'),
                                toClass=Iri('oldap:Person'),
                                name=LangString(["Author(s)@en", "Autor(en)@de"]),
                                description=LangString(["Writers of the Book@en", "Schreiber*innen des Buchs@de"]))

        book = ResourceClass(con=self._connection,
                             project=project,
                             owlclass_iri=Xsd_QName(f'{dm_name}:Book'),
                             label=LangString(["Book@en", "Buch@de"]),
                             comment=LangString("Ein Buch mit Seiten@en"),
                             closed=Xsd_boolean(True),
                             hasproperties=[
                                 HasProperty(con=self._connection, project=self._project, prop=title, minCount=Xsd_integer(1), order=1),
                                 HasProperty(con=self._connection, project=self._project, prop=authors, minCount=Xsd_integer(1), order=2),
                                 HasProperty(con=self._connection, project=self._project, prop=comment, order=3)])

        pagenum = PropertyClass(con=self._connection,
                                project=project,
                                property_class_iri=Xsd_QName(f'{dm_name}:pagenum'),
                                datatype=XsdDatatypes.int,
                                name=LangString(["Pagenumber@en", "Seitennummer@de"]))

        inbook = PropertyClass(con=self._connection,
                               project=project,
                               property_class_iri=Xsd_QName(f'{dm_name}:inbook'),
                               toClass=Iri(f'{dm_name}:Book'),
                               name=LangString(["Pagenumber@en", "Seitennummer@de"]))

        page = ResourceClass(con=self._connection,
                             project=project,
                             owlclass_iri=Xsd_QName(f'{dm_name}:Page'),
                             label=LangString(["Page@en", "Seite@de"]),
                             comment=LangString("Page of a book@en"),
                             closed=Xsd_boolean(True),
                             hasproperties=[
                                 HasProperty(con=self._connection, project=self._project, prop=pagenum, maxCount=Xsd_integer(1), minCount=Xsd_integer(1), order=1),
                                 HasProperty(con=self._connection, project=self._project, prop=inbook, maxCount=Xsd_integer(1), minCount=Xsd_integer(1), order=2),
                                 HasProperty(con=self._connection, project=self._project, prop=comment, order=3)])

        dm = DataModel(con=self._connection,
                       project=project,
                       propclasses=[comment],
                       resclasses=[book, page])
        return dm

    def test_datamodel_serialize_deserialize(self):
        dm_name = self._dmproject.projectShortName
        dma = self.generate_a_datamodel(self._dmproject)
        dma.create()

        dmb = DataModel.read(con=self._connection, project=self._dmproject)

        self.assertFalse(dma is dmb)

        p1a = dma[Xsd_QName(f'{dm_name}:comment')]
        p1b = dmb[Xsd_QName(f'{dm_name}:comment')]
        self.assertEqual(p1a.datatype, p1b.datatype)
        self.assertEqual(p1a.name, p1b.name)
        self.assertFalse(p1a.name is p1b.name)
        self.assertEqual(p1a.languageIn, p1b.languageIn)
        self.assertFalse(p1a.languageIn is p1b.languageIn)
        self.assertTrue(p1b.uniqueLang)

        r1a = dma[Xsd_QName(f'{dm_name}:Book')]
        r1b = dmb[Xsd_QName(f'{dm_name}:Book')]
        self.assertFalse(r1a is r1b)

        r1p1a = r1a[Xsd_QName(f'{dm_name}:title')]
        r1p1b = r1b[Xsd_QName(f'{dm_name}:title')]
        self.assertFalse(r1p1a is r1p1b)
        self.assertEqual(r1p1a.prop.internal, r1p1b.prop.internal)
        self.assertFalse(r1p1a.prop.internal is r1p1b.prop.internal)
        self.assertEqual(r1p1a.prop.datatype, r1p1b.prop.datatype)
        self.assertEqual(r1p1a.prop.name, r1p1b.prop.name)
        self.assertFalse(r1p1a.prop.name is r1p1b.prop.name)
        self.assertEqual(r1p1a.prop.description, r1p1b.prop.description)
        self.assertFalse(r1p1a.prop.description is r1p1b.prop.description)
        self.assertEqual(r1p1a.prop.languageIn, r1p1b.prop.languageIn)
        self.assertFalse(r1p1a.prop.languageIn is r1p1b.prop.languageIn)
        self.assertTrue(r1p1b.prop.uniqueLang)
        self.assertEqual(r1p1a.minCount, r1p1b.minCount)
        self.assertEqual(r1p1a.order, r1p1b.order)

        r1p2a = r1a[Xsd_QName(f'{dm_name}:authors')]
        r1p2b = r1b[Xsd_QName(f'{dm_name}:authors')]
        self.assertFalse(r1p2a is r1p2b)
        self.assertEqual(r1p2a.prop.internal, r1p2b.prop.internal)
        self.assertFalse(r1p2a.prop.internal is r1p2b.prop.internal)
        self.assertEqual(r1p2a.prop.toClass, r1p2b.prop.toClass)
        self.assertFalse(r1p2a.prop.toClass is r1p2b.prop.toClass)
        self.assertEqual(r1p2a.prop.name, r1p2b.prop.name)
        self.assertFalse(r1p2a.prop.name is r1p2b.prop.name)
        self.assertEqual(r1p2a.prop.description, r1p2b.prop.description)
        self.assertFalse(r1p2a.prop.description is r1p2b.prop.description)
        self.assertEqual(r1p2a.minCount, r1p2b.minCount)
        self.assertEqual(r1p2a.order, r1p2b.order)

        r1p3a = r1a[Xsd_QName(f'{dm_name}:comment')]
        r1p3b = r1b[Xsd_QName(f'{dm_name}:comment')]
        self.assertFalse(r1p3a is r1p3b)
        self.assertIsNone(r1p3b.prop.internal)
        self.assertEqual(r1p3a.prop.datatype, r1p3b.prop.datatype)
        self.assertEqual(r1p3a.prop.name, r1p3b.prop.name)
        self.assertFalse(r1p3a.prop.name is r1p3b.prop.name)
        self.assertTrue(r1p3a.prop.uniqueLang, r1p3b.prop.uniqueLang)
        self.assertFalse(r1p3a.prop.uniqueLang is r1p3b.prop.uniqueLang)
        self.assertEqual(r1p3a.prop.languageIn, r1p3b.prop.languageIn)
        self.assertFalse(r1p3a.prop.languageIn is r1p3b.prop.languageIn)
        self.assertEqual(r1p3a.order, r1p3b.order)

        r2a = dma[Xsd_QName(f'{dm_name}:Page')]
        r2b = dmb[Xsd_QName(f'{dm_name}:Page')]
        self.assertFalse(r2a is r2b)
        r2p1a = r2a[Xsd_QName(f'{dm_name}:pagenum')]
        r2p1b = r2b[Xsd_QName(f'{dm_name}:pagenum')]
        self.assertFalse(r2p1a is r2p1b)
        self.assertEqual(r2p1a.prop.internal, r2p1b.prop.internal)
        self.assertFalse(r2p1a.prop.internal is r2p1b.prop.internal)
        self.assertEqual(r2p1a.prop.datatype, r2p1b.prop.datatype)
        self.assertEqual(r2p1a.prop.name, r2p1b.prop.name)
        self.assertFalse(r2p1a.prop.name is r2p1b.prop.name)
        self.assertEqual(r2p1a.maxCount, r2p1b.maxCount)
        self.assertEqual(r2p1a.minCount, r2p1b.minCount)

        r2p2a = r2a[Xsd_QName(f'{dm_name}:inbook')]
        r2p2b = r2b[Xsd_QName(f'{dm_name}:inbook')]
        self.assertFalse(r2p2a is r2p2b)
        self.assertEqual(r2p2a.prop.internal, r2p2b.prop.internal)
        self.assertFalse(r2p2a.prop.internal is r2p2b.prop.internal)
        self.assertEqual(r2p2a.prop[PropClassAttr.CLASS], r2p2b.prop[PropClassAttr.CLASS])
        self.assertFalse(r2p2a.prop[PropClassAttr.CLASS] is r2p2b.prop[PropClassAttr.CLASS])
        self.assertEqual(r2p2a.prop[PropClassAttr.NAME], r2p2b.prop[PropClassAttr.NAME])
        self.assertFalse(r2p2a.prop[PropClassAttr.NAME] is r2p2b.prop[PropClassAttr.NAME])
        self.assertEqual(r2p2a.maxCount, r2p2b.maxCount)
        self.assertEqual(r2p2a.minCount, r2p2b.minCount)
        self.assertEqual(r2p2a.order, r2p2b.order)

        r2p3a = r1a[Xsd_QName(f'{dm_name}:comment')]
        r2p3b = r1b[Xsd_QName(f'{dm_name}:comment')]
        self.assertFalse(r2p3a is r2p3b)
        self.assertIsNone(r2p3b.prop.internal)
        self.assertEqual(r2p3a.prop.datatype, r2p3b.prop.datatype)
        self.assertEqual(r2p3a.prop.name, r2p3b.prop.name)
        self.assertFalse(r2p3a.prop.name is r2p3b.prop.name)
        self.assertTrue(r2p3b.prop.uniqueLang)
        self.assertEqual(r2p3a.prop.languageIn, r2p3b.prop.languageIn)
        self.assertFalse(r2p3a.prop.languageIn is r2p3b.prop.languageIn)



    # @unittest.skip('Work in progress')
    def test_datamodel_constructor(self):
        dm_name = self._dmproject.projectShortName

        dm = self.generate_a_datamodel(self._dmproject)
        dm.create()

        del dm

        dm2 = DataModel.read(con=self._connection, project=self._dmproject)
        p1 = dm2[Xsd_QName(f'{dm_name}:comment')]
        self.assertEqual(p1.datatype, XsdDatatypes.langString)
        self.assertEqual(p1.name, LangString(["Comment@en", "Kommentar@de"]))
        self.assertEqual(p1.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(p1.uniqueLang)

        r1 = dm2[Xsd_QName(f'{dm_name}:Book')]

        r1p1 = r1[Xsd_QName(f'{dm_name}:title')]
        self.assertEqual(r1p1.prop.internal, Xsd_QName(f'{dm_name}:Book'))
        self.assertEqual(r1p1.prop.datatype, XsdDatatypes.langString)
        self.assertEqual(r1p1.prop.name, LangString(["Title@en", "Titel@de"]))
        self.assertEqual(r1p1.prop.description, LangString(["Title of book@en", "Titel des Buches@de"]))
        self.assertEqual(r1p1.prop.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(r1p1.prop.uniqueLang)
        self.assertEqual(r1p1.minCount, Xsd_integer(1))
        self.assertEqual(r1p1.order, Xsd_decimal(1))

        r1p2 = r1[Xsd_QName(f'{dm_name}:authors')]
        self.assertEqual(r1p2.prop.internal, Xsd_QName(f'{dm_name}:Book'))
        self.assertEqual(r1p2.prop.toClass, Xsd_QName('oldap:Person'))
        self.assertEqual(r1p2.prop.name, LangString(["Author(s)@en", "Autor(en)@de"]))
        self.assertEqual(r1p2.prop.description, LangString(["Writers of the Book@en", "Schreiber*innen des Buchs@de"]))
        self.assertEqual(r1p2.minCount, Xsd_integer(1))
        self.assertEqual(r1p2.order, Xsd_decimal(2))

        r1p3 = r1[Xsd_QName(f'{dm_name}:comment')]
        self.assertIsNone(r1p3.prop.internal)
        self.assertEqual(r1p3.prop.datatype, XsdDatatypes.langString)
        self.assertEqual(r1p3.prop.name, LangString(["Comment@en", "Kommentar@de"]))
        self.assertTrue(r1p3.prop.uniqueLang, Xsd_boolean(True))
        self.assertEqual(r1p3.prop.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertEqual(r1p3.order, Xsd_decimal(3))

        r2 = dm2[Xsd_QName(f'{dm_name}:Page')]
        r2p1 = r2[Xsd_QName(f'{dm_name}:pagenum')]
        self.assertEqual(r2p1.prop.internal, Xsd_QName(f'{dm_name}:Page'))
        self.assertEqual(r2p1.prop.datatype, XsdDatatypes.int)
        self.assertEqual(r2p1.prop.name, LangString(["Pagenumber@en", "Seitennummer@de"]))
        self.assertEqual(r2p1.maxCount, Xsd_integer(1))
        self.assertEqual(r2p1.minCount, Xsd_integer(1))

        r2p2 = r2[Xsd_QName(f'{dm_name}:inbook')]
        self.assertEqual(r2p2.prop.internal, Xsd_QName(f'{dm_name}:Page'))
        self.assertEqual(r2p2.prop[PropClassAttr.CLASS], Iri(f'{dm_name}:Book'))
        self.assertEqual(r2p2.prop[PropClassAttr.NAME], LangString(["Pagenumber@en", "Seitennummer@de"]))
        self.assertEqual(r2p2.maxCount, Xsd_integer(1))
        self.assertEqual(r2p2.minCount, Xsd_integer(1))
        self.assertEqual(r2p2.order, Xsd_decimal(2))

        r2p3 = r1[Xsd_QName(f'{dm_name}:comment')]
        self.assertIsNone(r2p3.prop.internal)
        self.assertEqual(r2p3.prop.datatype, XsdDatatypes.langString)
        self.assertEqual(r2p3.prop.name, LangString(["Comment@en", "Kommentar@de"]))
        self.assertTrue(r2p3.prop.uniqueLang, Xsd_boolean(True))
        self.assertEqual(r2p3.prop.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

    # @unittest.skip('Work in progress')
    def test_datamodel_read(self):
        model = DataModel.read(self._connection, self._sysproject, ignore_cache=True)
        self.assertEqual(set(model.get_propclasses()), {
            Xsd_QName("oldap:hasAdminPermission"),
            Xsd_QName("oldap:statementProperty"),
            Xsd_QName("oldap:namespaceIri"),
        })
        self.assertEqual(set(model.get_resclasses()), {
            Xsd_QName("oldap:Project"),
            Xsd_QName("oldap:User"),
            Xsd_QName("oldap:OldapList"),
            Xsd_QName("oldap:OldapListNode"),
            Xsd_QName("oldap:AdminPermission"),
            Xsd_QName("oldap:DataPermission"),
            Xsd_QName("oldap:PermissionSet"),
            Xsd_QName("oldap:Thing"),
            Xsd_QName("oldap:ExternalOntology"),
            Xsd_QName("oldap:inProjectStatement")
        })

    def test_datamodel_read_shared(self):
        model = DataModel.read(self._connection, self._sharedproject, ignore_cache=True)
        pass

    def test_datamodel_read_system(self):
        model = DataModel.read(self._connection, self._sysproject, ignore_cache=True)

    def test_datamodel_read_test(self):
        model = DataModel.read(self._connection, self._project, ignore_cache=True)
        ontos = model.get_extontos()
        crm = model[Xsd_QName('test:crm')]
        self.assertEqual(crm.prefix, 'crm')
        self.assertEqual(crm.namespaceIri, 'http://www.cidoc-crm.org/cidoc-crm/')
        context = model.context
        self.assertEqual(context['crm'], 'http://www.cidoc-crm.org/cidoc-crm/')


    def test_datamodel_cache(self):
        start = time()
        model = DataModel.read(self._connection, self._sysproject, ignore_cache=True)
        end = time()
        print(f"No cache execution time: {end - start:.4f} seconds")

        start = time()
        model = DataModel.read(self._connection, self._sysproject, ignore_cache=False)
        end = time()
        print(f"With cache execution time: {end - start:.4f} seconds")

    # @unittest.skip('Work in progress')
    def test_datamodel_modify_A(self):
        dm_name = self._dmprojectA.projectShortName

        dm = self.generate_a_datamodel(self._dmprojectA)
        dm.create()
        dm = DataModel.read(self._connection, self._dmprojectA, ignore_cache=True)

        #
        # define an external standalone property
        #
        pubyear = PropertyClass(con=self._connection,
                                project=self._dmprojectA,
                                property_class_iri=Xsd_QName(f'{dm_name}:pubYear'),
                                datatype=XsdDatatypes.gYear,
                                name=LangString(["Publication Year@en", "Publicationsjahr@de"]))
        pubyear.force_external()
        dm[Xsd_QName(f'{dm_name}:pubYear')] = pubyear
        self.assertEqual({Xsd_QName(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE)}, dm.changeset)

        dm[Xsd_QName(f'{dm_name}:comment')].name[Language.FR] = 'Commentaire'
        self.assertEqual({
            Xsd_QName(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE),
            Xsd_QName(f'{dm_name}:comment'): PropertyClassChange(None, Action.MODIFY)
        }, dm.changeset)

        dm[Xsd_QName(f'{dm_name}:Book')][Xsd_QName(f'{dm_name}:authors')].prop.name[Language.FR] = "Ecrivain(s)"
        self.maxDiff = None
        self.assertEqual({
            Xsd_QName(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE),
            Xsd_QName(f'{dm_name}:comment'): PropertyClassChange(None, Action.MODIFY),
            Xsd_QName(f'{dm_name}:Book'): ResourceClassChange(None, Action.MODIFY)
        }, dm.changeset)

        del dm[Xsd_QName(f'{dm_name}:Page')][Xsd_QName(f'{dm_name}:comment')]

        self.assertEqual({
            Xsd_QName(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE),
            Xsd_QName(f'{dm_name}:comment'): PropertyClassChange(None, Action.MODIFY),
            Xsd_QName(f'{dm_name}:Book'): ResourceClassChange(None, Action.MODIFY),
            Xsd_QName(f'{dm_name}:Page'): ResourceClassChange(None, Action.MODIFY)
        }, dm.changeset)

        pagename = PropertyClass(con=self._connection,
                                 project=self._dmprojectA,
                                 property_class_iri=Xsd_QName(f'{dm_name}:pageName'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString(["Page name@en", "Seitenbezeichnung@de"]))

        dm[Xsd_QName(f'{dm_name}:Page')][Xsd_QName(f'{dm_name}:pageName')] = HasProperty(con=self._connection, project=self._project, prop=pagename, maxCount=1, minCount=1)
        self.assertEqual({
            Xsd_QName(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE),
            Xsd_QName(f'{dm_name}:comment'): PropertyClassChange(None, Action.MODIFY),
            Xsd_QName(f'{dm_name}:Book'): ResourceClassChange(None, Action.MODIFY),
            Xsd_QName(f'{dm_name}:Page'): ResourceClassChange(None, Action.MODIFY)
        }, dm.changeset)

    # @unittest.skip('Work in progress')
    def test_datamodel_modify_B(self):
        dm_name = self._dmprojectB.projectShortName

        dm = self.generate_a_datamodel(self._dmprojectB)
        dm.create()
        del dm

        dm = DataModel.read(self._connection, self._dmprojectB, ignore_cache=True)

        #
        # define a standalone property and add it to the datamodel
        #
        pubyear = PropertyClass(con=self._connection,
                                project=self._dmprojectB,
                                property_class_iri=Xsd_QName(f'{dm_name}:pubYear'),
                                datatype=XsdDatatypes.gYear,
                                name=LangString(["Publication Year@en", "Publicationsjahr@de"]))
        pubyear.force_external()
        dm[Xsd_QName(f'{dm_name}:pubYear')] = pubyear

        #
        # Modify a standalone property
        #
        dm[Xsd_QName(f'{dm_name}:comment')][PropClassAttr.NAME][Language.FR] = 'Commentaire'

        #
        # Modify an internal property
        #
        dm[Xsd_QName(f'{dm_name}:Book')][Xsd_QName(f'{dm_name}:authors')].prop.name[Language.FR] = "Ecrivain(s)"


        #
        # Add a new property as internal property
        #
        pagename = PropertyClass(con=self._connection,
                                 project=self._dmprojectB,
                                 property_class_iri=Xsd_QName(f'{dm_name}:pageName'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString(["Page name@en", "Seitenbezeichnung@de"]))

        dm[Xsd_QName(f'{dm_name}:Page')][Xsd_QName(f'{dm_name}:pageName')] = HasProperty(con=self._connection, project=self._project, prop=pagename)

        dm.update()

        del dm

        dm = DataModel.read(self._connection, self._dmprojectB, ignore_cache=True)
        self.assertIsNotNone(dm.get(Xsd_QName(f'{dm_name}:pubYear')))
        self.assertEqual(dm[Xsd_QName(f'{dm_name}:pubYear')].datatype, XsdDatatypes.gYear)
        self.assertEqual(dm[Xsd_QName(f'{dm_name}:comment')].name[Language.FR], 'Commentaire')
        self.assertEqual(dm[Xsd_QName(f'{dm_name}:Book')][Xsd_QName(f'{dm_name}:authors')].prop.name[Language.FR], "Ecrivain(s)")
        self.assertIsNotNone(dm[Xsd_QName(f'{dm_name}:Page')][Xsd_QName(f'{dm_name}:pageName')])

    def test_datamodel_modify_C(self):
        dm_name = self._dmprojectC.projectShortName

        dm = self.generate_a_datamodel(self._dmprojectC)
        dm.create()
        del dm

        dm = DataModel.read(self._connection, self._dmprojectC, ignore_cache=True)

        #
        # remove the comment property from the Page resource
        #
        del dm[Xsd_QName(f'{dm_name}:Page')][Xsd_QName(f'{dm_name}:comment')]

        dm.update()

        del dm

        dm = DataModel.read(self._connection, self._dmprojectC, ignore_cache=True)
        self.assertIsNone(dm[Xsd_QName(f'{dm_name}:Page')].get(Xsd_QName(f'{dm_name}:comment')))  # TODO THIS TEST SHOULD PASS!!!!

    def test_datamodel_modify_D(self):
        dm_name = self._dmproject.projectShortName

        dm = self.generate_a_datamodel(self._dmproject)
        dm.create()
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        dm[Xsd_QName(f'{dm_name}:comment')].name = LangString("Waseliwas@zu")
        dm.update()
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        self.assertEqual(dm[Xsd_QName(f'{dm_name}:comment')].name, LangString("Waseliwas@zu"))

    def test_datamodel_modify_E(self):
        dm_name = self._dmprojectE.projectShortName

        dm = self.generate_a_datamodel(self._dmprojectE)
        dm.create()
        del dm
        dm = DataModel.read(self._connection, self._dmprojectE, ignore_cache=True)

        #
        # Add a new standalone property without name/description
        #
        pubyear = PropertyClass(con=self._connection,
                                project=self._dmprojectE,
                                property_class_iri=Xsd_QName(f'{dm_name}:pubYearE'),
                                datatype=XsdDatatypes.gYear,
                                name=LangString(["Publication YearE@en", "PublicationsjahrE@de"]))
        pubyear.force_external()
        dm[Xsd_QName(f'{dm_name}:pubYearE')] = pubyear

        dm.update()
        dm = DataModel.read(self._connection, self._dmprojectE, ignore_cache=True)
        self.assertIsNotNone(dm.get(Xsd_QName(f'{dm_name}:pubYearE')))

    def test_datamodel_modify_I(self):
        dm_name = self._dmprojectI.projectShortName
        dm = self.generate_a_datamodel(self._dmprojectI)
        dm.create()
        del dm
        dm = DataModel.read(self._connection, self._dmprojectI, ignore_cache=True)
        dm[Xsd_QName(f'{dm_name}:Book')].add_superclasses([f'{dm_name}:Page', 'dcterms:Event'])
        dm.update()

        dm = DataModel.read(self._connection, self._dmprojectI, ignore_cache=True)
        tmp = set([key for key, val in dm[Xsd_QName(f'{dm_name}:Book')].superclass.items()])
        assert tmp == {'oldap:Thing', f'{dm_name}:Page', 'dcterms:Event'}

        dm[Xsd_QName(f'{dm_name}:Book')].del_superclasses([f'{dm_name}:Page'])
        dm.update()
        dm = DataModel.read(self._connection, self._dmprojectI, ignore_cache=True)
        tmp = set([key for key, val in dm[Xsd_QName(f'{dm_name}:Book')].superclass.items()])
        assert tmp == {'oldap:Thing', 'dcterms:Event'}

    def test_datamodel_extonto_motify(self):
        model = DataModel.read(self._connection, self._project, ignore_cache=True)
        model[Xsd_QName('test:crm')].label['it'] = 'CIDOC-CRM (it)'
        model.update()
        model = DataModel.read(self._connection, self._project, ignore_cache=True)

        crm = model[Xsd_QName('test:crm')]
        self.assertEqual(crm.prefix, 'crm')
        self.assertEqual(crm.namespaceIri, 'http://www.cidoc-crm.org/cidoc-crm/')
        self.assertEqual(crm.label, LangString("CIDOC-CRM@en", "CIDOC-CRM@de", "CIDOC-CRM@fr", "CIDOC-CRM (it)@it"))

    def test_datamodel_extonto_delete(self):
        model = DataModel.read(self._connection, self._project, ignore_cache=True)
        self.assertIsInstance(model.get(Xsd_QName('test:edm')), ExternalOntology)
        del model[Xsd_QName('test:edm')]
        model.update()
        model = DataModel.read(self._connection, self._project, ignore_cache=True)
        self.assertIsNone(model.get(Xsd_QName('test:edm')))

    def test_datamodel_extonto_add(self):
        model = DataModel.read(self._connection, self._project, ignore_cache=True)
        eo = ExternalOntology(con=self._connection,
                              projectShortName=self._project.projectShortName,
                              prefix='testonto',
                              namespaceIri='http://www.example.org/ns/testonto#',
                              label=LangString("Test ontology@en", "Test ontology@de"))
        model[Xsd_QName('test:testonto')] = eo
        model.update()
        model = DataModel.read(self._connection, self._project, ignore_cache=True)
        self.assertIsInstance(model.get(Xsd_QName('test:testonto')), ExternalOntology)

        context = model.context
        self.assertEqual(context['testonto'], 'http://www.example.org/ns/testonto#')

    def test_incremental_generation(self):
        dm = DataModel(con=self._connection,
                       project=self._dmproject)
        dm.create()
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        dm_name = self._dmproject.projectShortName

        #
        # add a standalone property
        #
        generic_comment = PropertyClass(con=self._connection,
                                 project=self._dmproject,
                                 property_class_iri=Xsd_QName(f'{dm_name}:genericComment'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString(["Generic comment@en", "Allgemeiner Kommentar@de"]))
        dm[Xsd_QName(f'{dm_name}:genericComment')] = generic_comment
        dm.update()
        #dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        p1 = dm[Xsd_QName(f'{dm_name}:genericComment')]
        self.assertEqual(p1.datatype, XsdDatatypes.string)

        #
        # Modifying the property
        #
        p1.description = LangString("For testing purposes only@en")
        dm.update()
        #dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        p1 = dm[Xsd_QName(f'{dm_name}:genericComment')]
        self.assertEqual(p1.datatype, XsdDatatypes.string)
        self.assertEqual(p1.description, LangString("For testing purposes only@en"))

        #
        # Add a resource
        #
        titleX = PropertyClass(con=self._connection,
                               project=self._dmproject,
                               property_class_iri=Xsd_QName(f'{dm_name}:titleX'),
                               datatype=XsdDatatypes.langString,
                               name=LangString(["TitleX@en", "TitelX@de"]),
                               description=LangString(["TitleX of book@en", "TitelX des Buches@de"]),
                               uniqueLang=Xsd_boolean(True),
                               languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        authorsX = PropertyClass(con=self._connection,
                                 project=self._dmproject,
                                 property_class_iri=Xsd_QName(f'{dm_name}:authorsX'),
                                 toClass=Xsd_QName('oldap:Person'),
                                 name=LangString(["Author(s)X@en", "Autor(en)X@de"]),
                                 description=LangString(["Writers of the BookX@en", "Schreiber*innen des BuchsX@de"]))

        bookX = ResourceClass(con=self._connection,
                              project=self._dmproject,
                              owlclass_iri=Xsd_QName(f'{dm_name}:BookX'),
                              label=LangString(["BookX@en", "BuchX@de"]),
                              comment=LangString("Ein Buch mit SeitenX@en"),
                              closed=Xsd_boolean(True),
                              hasproperties=[
                                  HasProperty(con=self._connection, project=self._project, prop=titleX, minCount=Xsd_integer(1), order=1),
                                  HasProperty(con=self._connection, project=self._project, prop=authorsX, minCount=Xsd_integer(1), order=2),
                                  HasProperty(con=self._connection, project=self._project, prop=Xsd_QName(f'{dm_name}:genericComment'), order=3)])
        dm[Xsd_QName(f'{dm_name}:BookX')] = bookX
        dm.update()

        #dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)

        p1 = dm[Xsd_QName(f'{dm_name}:genericComment')]
        self.assertEqual(p1.datatype, XsdDatatypes.string)
        self.assertEqual(p1.description, LangString("For testing purposes only@en"))

        r1 = dm[Xsd_QName(f'{dm_name}:BookX')]

        r1p1 = r1[Xsd_QName(f'{dm_name}:titleX')]
        self.assertEqual(r1p1.prop.internal, Xsd_QName(f'{dm_name}:BookX'))
        self.assertEqual(r1p1.prop.datatype, XsdDatatypes.langString)
        self.assertEqual(r1p1.prop.name, LangString(["TitleX@en", "TitelX@de"]))
        self.assertEqual(r1p1.prop.description, LangString(["TitleX of book@en", "TitelX des Buches@de"]))
        self.assertEqual(r1p1.prop.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(r1p1.prop.uniqueLang)
        self.assertEqual(r1p1.minCount, Xsd_integer(1))
        self.assertEqual(r1p1.order, Xsd_decimal(1))

        r1p2 = r1[Xsd_QName(f'{dm_name}:authorsX')]
        self.assertEqual(r1p2.prop.internal, Xsd_QName(f'{dm_name}:BookX'))
        self.assertEqual(r1p2.prop.toClass, Xsd_QName('oldap:Person'))
        self.assertEqual(r1p2.prop.name, LangString(["Author(s)X@en", "Autor(en)X@de"]))
        self.assertEqual(r1p2.prop.description, LangString(["Writers of the BookX@en", "Schreiber*innen des BuchsX@de"]))
        self.assertEqual(r1p2.minCount, Xsd_integer(1))
        self.assertEqual(r1p2.order, Xsd_decimal(2))

        r1p3 = r1[Xsd_QName(f'{dm_name}:genericComment')]
        self.assertIsNone(r1p3.prop.internal)
        self.assertEqual(r1p3.prop.datatype, XsdDatatypes.string)
        self.assertEqual(r1p3.prop.name, LangString(["Generic comment@en", "Allgemeiner Kommentar@de"]))
        self.assertEqual(r1p3.order, Xsd_decimal(3))


    def test_datamodel_duplicate_standalone_property(self):
        dm = DataModel(con=self._connection,
                       project=self._dmprojectG)
        dm.create()
        dm = DataModel.read(self._connection, self._dmprojectG, ignore_cache=True)
        dm_name = self._dmprojectG.projectShortName

        #
        # add a standalone property
        #
        generic_comment = PropertyClass(con=self._connection,
                                 project=self._dmprojectG,
                                 property_class_iri=Xsd_QName(f'{dm_name}:genericComment'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString(["Generic comment@en", "Allgemeiner Kommentar@de"]))
        generic_comment.force_external()
        dm[Xsd_QName(f'{dm_name}:genericComment')] = generic_comment
        dm.update()

        dm = DataModel.read(self._connection, self._dmprojectG, ignore_cache=True)
        p1 = dm[Xsd_QName(f'{dm_name}:genericComment')]
        self.assertEqual(p1.datatype, XsdDatatypes.string)

        #
        # add a duplicate standalone property
        #
        generic_comment = PropertyClass(con=self._connection,
                                 project=self._dmprojectG,
                                 property_class_iri=Xsd_QName(f'{dm_name}:genericComment'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString(["Generic comment@en", "Allgemeiner Kommentar@de"]))
        generic_comment.force_external()
        with self.assertRaises(OldapErrorAlreadyExists):
            dm[Xsd_QName(f'{dm_name}:genericComment')] = generic_comment

    def test_datamodel_duplicate_resource_property(self):
        dm_name = self._dmprojectH.projectShortName

        dm = self.generate_a_datamodel(self._dmprojectH)
        dm.create()
        del dm

        dm = DataModel.read(self._connection, self._dmprojectH, ignore_cache=True)

        title = PropertyClass(con=self._connection,
                              project=self._dmprojectH,
                              property_class_iri=Xsd_QName(f'{dm_name}:title'),
                              datatype=XsdDatatypes.langString,
                              name=LangString(["Title@en", "Titel@de"]),
                              description=LangString(["Title of book@en", "Titel des Buches@de"]),
                              uniqueLang=Xsd_boolean(True),
                              languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        hasprop = HasProperty(con=self._connection, project=self._project, prop=title, minCount=Xsd_integer(1), order=1)

        dm[Xsd_QName(f'{dm_name}:Book')][Xsd_QName(f'{dm_name}:title')] = hasprop

        with self.assertRaises(OldapErrorAlreadyExists):
            dm.update()

    def test_update_parts(self):
        dm_name = self._dmproject.projectShortName
        generic_commentY = PropertyClass(con=self._connection,
                                         project=self._dmproject,
                                         property_class_iri=Xsd_QName(f'{dm_name}:genericCommentY'),
                                         datatype=XsdDatatypes.string,
                                         name=LangString(["Generic commentY@en", "Allgemeiner KommentarY@de"]))
        generic_commentY.force_external()

        titleY = PropertyClass(con=self._connection,
                               project=self._dmproject,
                               property_class_iri=Xsd_QName(f'{dm_name}:titleY'),
                               datatype=XsdDatatypes.langString,
                               name=LangString(["TitleY@en", "TitelY@de"]),
                               description=LangString(["TitleY of book@en", "TitelY des Buches@de"]),
                               uniqueLang=Xsd_boolean(True),
                               languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        authorsY = PropertyClass(con=self._connection,
                                 project=self._dmproject,
                                 property_class_iri=Xsd_QName(f'{dm_name}:authorsY'),
                                 toClass=Iri('oldap:Person'),
                                 name=LangString(["Author(s)Y@en", "Autor(en)Y@de"]),
                                 description=LangString(["Writers of the BookY@en", "Schreiber*innen des BuchsY@de"]))

        bookY = ResourceClass(con=self._connection,
                              project=self._dmproject,
                              owlclass_iri=Xsd_QName(f'{dm_name}:BookY'),
                              label=LangString(["BookY@en", "BuchY@de"]),
                              comment=LangString("Ein Buch mit SeitenY@en"),
                              closed=Xsd_boolean(True),
                              hasproperties=[
                                  HasProperty(con=self._connection, project=self._project, prop=titleY, minCount=Xsd_integer(1), order=1),
                                  HasProperty(con=self._connection, project=self._project, prop=authorsY, minCount=Xsd_integer(1), order=2),
                                  HasProperty(con=self._connection, project=self._project, prop=generic_commentY, order=3)])

        dm = DataModel(con=self._connection,
                       project=self._dmproject,
                       propclasses=[generic_commentY],
                       resclasses=[bookY])
        dm.create()

        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)

        #
        # a few check's if the creation of the datamodel worked as expected...
        #
        p1 = dm[Xsd_QName(f'{dm_name}:genericCommentY')]
        self.assertEqual(p1.datatype, XsdDatatypes.string)
        self.assertEqual(p1.name, LangString(["Generic commentY@en", "Allgemeiner KommentarY@de"]))
        self.assertIsNone(p1.internal)

        r1 = dm[Xsd_QName(f'{dm_name}:BookY')]

        r1p1 = r1[Xsd_QName(f'{dm_name}:titleY')]
        self.assertEqual(r1p1.prop.internal, Xsd_QName(f'{dm_name}:BookY'))
        self.assertEqual(r1p1.prop.datatype, XsdDatatypes.langString)
        self.assertEqual(r1p1.prop.name, LangString(["TitleY@en", "TitelY@de"]))
        self.assertEqual(r1p1.prop.description, LangString(["TitleY of book@en", "TitelY des Buches@de"]))
        self.assertEqual(r1p1.prop.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(r1p1.prop.uniqueLang)
        self.assertEqual(r1p1.minCount, Xsd_integer(1))
        self.assertEqual(r1p1.order, Xsd_decimal(1))

        r1p2 = r1[Xsd_QName(f'{dm_name}:authorsY')]
        self.assertEqual(r1p2.prop.internal, Xsd_QName(f'{dm_name}:BookY'))
        self.assertEqual(r1p2.prop.toClass, Xsd_QName('oldap:Person'))
        self.assertEqual(r1p2.prop.name, LangString(["Author(s)Y@en", "Autor(en)Y@de"]))
        self.assertEqual(r1p2.prop.description, LangString(["Writers of the BookY@en", "Schreiber*innen des BuchsY@de"]))
        self.assertEqual(r1p2.minCount, Xsd_integer(1))
        self.assertEqual(r1p2.order, Xsd_decimal(2))

        r1p3 = r1[Xsd_QName(f'{dm_name}:genericCommentY')]
        self.assertIsNone(r1p3.prop.internal)
        self.assertEqual(r1p3.prop.datatype, XsdDatatypes.string)
        self.assertEqual(r1p3.prop.name, LangString(["Generic commentY@en", "Allgemeiner KommentarY@de"]))
        self.assertEqual(r1p3.order, Xsd_decimal(3))

        #
        # Change name of genericCommentY, accessed by resource BookY
        #
        dm[Xsd_QName(f'{dm_name}:genericCommentY')].name[Language.IT] = "Commentario"

        #
        # Add a field to standalone property
        #
        dm[Xsd_QName(f'{dm_name}:genericCommentY')].description = LangString("DescriptionY@en", "Beschreibung@de")


        #
        # Add a new property
        #
        pubDateY = PropertyClass(con=self._connection,
                                 project=self._project,
                                 property_class_iri=Xsd_QName(f'{dm_name}:pubDateY'),
                                 datatype=XsdDatatypes.date)
        dm[Xsd_QName(f'{dm_name}:BookY')][Xsd_QName(f'{dm_name}:pubDateY')] = HasProperty(con=self._connection, project=self._project, prop=pubDateY)

        #
        # Delete a property
        #
        del dm[Xsd_QName(f'{dm_name}:BookY')][Xsd_QName(f'{dm_name}:authorsY')]

        dm.update()
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        r1 = dm[Xsd_QName(f'{dm_name}:BookY')]
        r1p3 = r1[Xsd_QName(f'{dm_name}:genericCommentY')]
        self.assertEqual(r1p3.prop.name, LangString(["Generic commentY@en", "Allgemeiner KommentarY@de", "Commentario@it"]))
        self.assertEqual(r1p3.prop.description, LangString("DescriptionY@en", "Beschreibung@de"))
        self.assertIsNotNone(dm[Xsd_QName(f'{dm_name}:BookY')][Xsd_QName(f'{dm_name}:pubDateY')])
        self.assertIsNone(dm[Xsd_QName(f'{dm_name}:BookY')][Xsd_QName(f'{dm_name}:authorsY')])

        #
        # delete a complete resource
        #
        del dm[Xsd_QName(f'{dm_name}:BookY')]
        dm.update()
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        self.assertIsNone(dm.get(Xsd_QName(f'{dm_name}:BookY')))

        #
        # delete standalone property
        #
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        del dm[Xsd_QName(f'{dm_name}:genericCommentY')]
        dm.update()
        self.assertIsNone(dm.get(Xsd_QName(f'{dm_name}:genericCommentY')))


    def test_update2(self):
        proj = Project.read(self._connection, "hyha")
        testProp2 = PropertyClass(con=self._connection,
                                  project=proj,
                                  property_class_iri="hyha:testProp2",
                                  subPropertyOf="hyha:testProp",
                                  datatype= XsdDatatypes.langString,
                                  name=["Test Property@en", "Test Feld@de"],
                                  description=["Test Feld Beschreibung@de"],
                                  languageIn=["en", "fr", "it", "de"],
                                  uniqueLang=True,
                                  inSet=["Kappa", "Gaga", "gugus"],
                                  minLength=1,
                                  maxLength=50,
                                  pattern=r"^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$",
                                  minExclusive=5.5,
                                  minInclusive=5.5,
                                  maxExclusive=5.5,
                                  maxInclusive=5.5,
                                  lessThan="hyha:testProp",
                                  lessThanOrEquals="hyha:testProp")

        Sheep = ResourceClass(con=self._connection,
                              project=proj,
                              owlclass_iri=Xsd_QName("hyha:Sheep"),
                              label=["Eine Buchseite@de", "A page of a book@en"],
                              comment=["Eine Buchseite@de","A page of a book@en"],
                              closed=Xsd_boolean(True),
                              hasproperties=[
                                  HasProperty(con=self._connection, project=self._project, prop=testProp2, minCount=Xsd_integer(1), maxCount=3, order=1)])
        dm = DataModel(con=self._connection,
                       project=proj,
                       resclasses=[Sheep])
        dm.create()
        dm = DataModel.read(self._connection, proj, ignore_cache=True)

        del dm[Xsd_QName('hyha:Sheep')][Xsd_QName('hyha:testProp2')]
        dm.update()

        dm = DataModel.read(self._connection, proj, ignore_cache=True)
        self.assertIsNone(dm[Xsd_QName('hyha:Sheep')][Xsd_QName('hyha:testProp2')])

        dm = DataModel(con=self._connection,
                       project=proj)
        with self.assertRaises(OldapErrorAlreadyExists):
            dm.create()

    def test_incremental_and_del(self):
        dm = DataModel(con=self._connection,
                       project=self._dmproject)
        dm.create()
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=False)
        dm_name = self._dmproject.projectShortName

        bookZZ = ResourceClass(con=self._connection,
                               project=self._dmproject,
                               owlclass_iri=Xsd_QName(f'{dm_name}:BookZZ'),
                               label=LangString(["BookZZ@en", "BuchZZ@de"]),
                               comment=LangString("Ein Buch mit SeitenZZ@en"),
                               closed=Xsd_boolean(True))

        dm[Xsd_QName(f'{dm_name}:BookZZ')] = bookZZ
        dm.update()
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)

        pubDateZ = PropertyClass(con=self._connection,
                                 project=self._project,
                                 property_class_iri=Xsd_QName(f'{dm_name}:pubDateZ'),
                                 datatype=XsdDatatypes.date)
        dm[Xsd_QName(f'{dm_name}:BookZZ')][Xsd_QName(f'{dm_name}:pubDateZ')] = HasProperty(con=self._connection, project=self._project, prop=pubDateZ)
        dm.update()
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        test_res = dm[Xsd_QName(f'{dm_name}:BookZZ')]
        self.assertEqual(test_res.label, LangString(["BookZZ@en", "BuchZZ@de"]))
        self.assertIsInstance(test_res[Xsd_QName(f'{dm_name}:pubDateZ')], HasProperty)
        self.assertEqual(test_res[Xsd_QName(f'{dm_name}:pubDateZ')].prop.property_class_iri, Xsd_QName(f'{dm_name}:pubDateZ'))

        dm.delete()
        with self.assertRaises(OldapErrorNotFound):
            dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)


    def test_delete_label_from_resource(self):
        pagename = PropertyClass(con=self._connection,
                                 project=self._dmprojectF,
                                 property_class_iri=Xsd_QName('test:testPropGaga'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString("Page designation@en", "Seitenbezeichnung@de"))
        page = ResourceClass(con=self._connection,
                             project=self._dmprojectF,
                             owlclass_iri=Xsd_QName("test:PageGaga"),
                             #superclass=Iri('oldap:Thing'),  # no longer necessary TODO: Test it!!!!
                             label=LangString(["Project@en", "Projekt@de"]),
                             comment=LangString(["A page of a book@en", "Seite eines Buches@de"]),
                             closed=Xsd_boolean(True),
                             hasproperties=[
                                 HasProperty(con=self._connection, project=self._project, prop=pagename, minCount=Xsd_integer(1), order=1)])
        dm = DataModel(con=self._connection,
                       project=self._dmprojectF,
                       resclasses=[page])
        dm.create()
        dm = DataModel.read(self._connection, self._dmprojectF, ignore_cache=True)
        #del dm[Iri('test:Page')][ResClassAttribute.from_name('label')]
        delattr(dm[Xsd_QName('test:PageGaga')], 'label')
        dm.update()
        dm = DataModel.read(self._connection, self._dmprojectF, ignore_cache=True)


    def test_write_trig(self):
        pagename = PropertyClass(con=self._connection,
                                 project=self._project,
                                 property_class_iri=Xsd_QName('test:pageDesignation'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString("Page designation@en", "Seitenbezeichnung@de"))
        pagenum = PropertyClass(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:pageNum'),
                                datatype=XsdDatatypes.positiveInteger,
                                name=LangString("Pagenumber@en", "Seitennummer@de"),
                                description=LangString("consecutive numbering of pages@en", "Konsekutive Nummerierung der Seiten@de"))
        pagedescription = PropertyClass(con=self._connection,
                                        project=self._project,
                                        property_class_iri=Xsd_QName('test:pageDescription'),
                                        datatype=XsdDatatypes.langString,
                                        languageIn=LanguageIn(Language.EN, Language.DE),
                                        uniqueLang=Xsd_boolean(True))
        content = PropertyClass(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:pageContent'),
                                datatype=XsdDatatypes.string)
        inBook = PropertyClass(con=self._connection,
                               project=self._project,
                               property_class_iri=Xsd_QName('test:pageInBook'),
                               toClass=Xsd_QName('test:Book'))
        page = ResourceClass(con=self._connection,
                             project=self._project,
                             owlclass_iri=Xsd_QName("test:Page"),
                             #superclass=Iri('oldap:Thing'),  # no longer necessary TODO: Test it!!!!
                             label=LangString(["Project@en", "Projekt@de"]),
                             comment=LangString(["A page of a book@en", "Seite eines Buches@de"]),
                             closed=Xsd_boolean(True),
                             hasproperties=[
                                 HasProperty(con=self._connection, project=self._project, prop=pagename, minCount=Xsd_integer(1), order=1),
                                 HasProperty(con=self._connection, project=self._project, prop=pagenum, minCount=Xsd_integer(1), maxCount=Xsd_integer(1), order=2),
                                 HasProperty(con=self._connection, project=self._project, prop=pagedescription, order=3),
                                 HasProperty(con=self._connection, project=self._project, prop=content, maxCount=Xsd_integer(1), order=4),
                                 HasProperty(con=self._connection, project=self._project, prop=inBook, minCount=Xsd_integer(1), maxCount=Xsd_integer(1), order=5)])

        title = PropertyClass(con=self._connection,
                              project=self._project,
                              property_class_iri=Xsd_QName('test:title'),
                              datatype=XsdDatatypes.string)
        author = PropertyClass(con=self._connection,
                               project=self._project,
                               property_class_iri=Xsd_QName('test:author'),
                               toClass=Iri('test:Person'))
        pubDate = PropertyClass(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:pubDate'),
                                datatype=XsdDatatypes.date)
        book = ResourceClass(con=self._connection,
                             project=self._project,
                             owlclass_iri=Xsd_QName('test:Book'),
                             #superclass=Iri('oldap:Thing'),
                             label=LangString(["Book@en", "Buch@de"]),
                             closed=Xsd_boolean(True),
                             hasproperties=[
                                 HasProperty(con=self._connection, project=self._project, prop=title, order=1),
                                 HasProperty(con=self._connection, project=self._project, prop=author, order=2),
                                 HasProperty(con=self._connection, project=self._project, prop=pubDate, order=3)])

        person = ResourceClass(con=self._connection,
                               project=self._project,
                               owlclass_iri=Xsd_QName('test:Person'),
                               #superclass=Iri('oldap:Thing'),  # no longer necessary TODO: Test it!!!!
                               label=LangString(["Person@en", "Person@de"]),
                               hasproperties=[
                                   HasProperty(con=self._connection, project=self._project, prop=Xsd_QName('schema:familyName'), minCount=Xsd_integer(1), maxCount=Xsd_integer(1), order=1),
                                   HasProperty(con=self._connection, project=self._project, prop=Xsd_QName('schema:givenName'), minCount=Xsd_integer(1), order=2)])

        dm = DataModel(con=self._connection,
                       project=self._project,
                       resclasses=[page, book, person])
        dm.write_as_trig('gaga.trig')

    unittest.skip('Only during development....')
    def test_cache(self):
        project_root = find_project_root(__file__)
        self._connection.clear_graph(Xsd_QName('test:shacl'))
        self._connection.clear_graph(Xsd_QName('test:onto'))
        self._connection.clear_graph(Xsd_QName('test:data'))

        file = project_root / 'oldaplib' / 'testdata' / 'objectfactory_test.trig'
        self._connection.upload_turtle(file)

        cache = CacheSingletonRedis()
        cache.clear()
        dm1 = DataModel.read(self._connection, self._project, ignore_cache=False)
        in_cache = cache.exists(Xsd_QName(self._project.projectShortName, 'shacl'))
        dm2 = DataModel.read(self._connection, self._project, ignore_cache=False)

        pass

