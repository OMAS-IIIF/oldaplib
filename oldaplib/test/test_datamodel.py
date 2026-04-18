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
from oldaplib.src.enums.owlpropertytype import OwlPropertyType
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
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
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
        cls._context['dmtestJ'] = NamespaceIRI('http://oldap.org/dmtestJ#')
        cls._context.use('test', 'dmtest', 'dmtestA', 'dmtestB', 'dmtestC', 'dmtestE', 'dmtestF', 'dmtestG', 'dmtestH', 'dmtestI', 'dmtestJ')

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
        cls._connection.clear_graph(Xsd_QName('dmtestJ:shacl'))
        cls._connection.clear_graph(Xsd_QName('dmtestJ:onto'))
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
        cls._dmprojectJ = Project.read(cls._connection, "dmtestJ", ignore_cache=True)
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
                                appliesToProperty=Xsd_QName(f'{dm_name}:authors'),
                                datatype=XsdDatatypes.langString,
                                name=LangString(["Comment@en", "Kommentar@de"]),
                                uniqueLang=Xsd_boolean(True),
                                languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

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
                              languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                              minCount=Xsd_integer(1),
                              order=1)

        authors = PropertyClass(con=self._connection,
                                project=project,
                                property_class_iri=Xsd_QName(f'{dm_name}:authors'),
                                toClass=Iri('oldap:Person'),
                                name=LangString(["Author(s)@en", "Autor(en)@de"]),
                                description=LangString(["Writers of the Book@en", "Schreiber*innen des Buchs@de"]),
                                minCount=Xsd_integer(1),
                                order=2)

        book = ResourceClass(con=self._connection,
                             project=project,
                             owlclass_iri=Xsd_QName(f'{dm_name}:Book'),
                             label=LangString(["Book@en", "Buch@de"]),
                             comment=LangString("Ein Buch mit Seiten@en"),
                             closed=Xsd_boolean(True),
                             properties=[title, authors])

        pagenum = PropertyClass(con=self._connection,
                                project=project,
                                property_class_iri=Xsd_QName(f'{dm_name}:pagenum'),
                                datatype=XsdDatatypes.int,
                                name=LangString(["Pagenumber@en", "Seitennummer@de"]),
                                maxCount=Xsd_integer(1),
                                minCount=Xsd_integer(1),
                                order=1)

        inbook = PropertyClass(con=self._connection,
                               project=project,
                               property_class_iri=Xsd_QName(f'{dm_name}:inbook'),
                               toClass=Iri(f'{dm_name}:Book'),
                               name=LangString(["Pagenumber@en", "Seitennummer@de"]),
                               maxCount=Xsd_integer(1),
                               minCount=Xsd_integer(1),
                               order=2)

        page = ResourceClass(con=self._connection,
                             project=project,
                             owlclass_iri=Xsd_QName(f'{dm_name}:Page'),
                             label=LangString(["Page@en", "Seite@de"]),
                             comment=LangString("Page of a book@en"),
                             closed=Xsd_boolean(True),
                             properties=[pagenum, inbook])

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


        r1a = dma[Xsd_QName(f'{dm_name}:Book')]
        r1b = dmb[Xsd_QName(f'{dm_name}:Book')]
        self.assertFalse(r1a is r1b)

        r1p1a = r1a[Xsd_QName(f'{dm_name}:title')]
        r1p1b = r1b[Xsd_QName(f'{dm_name}:title')]
        self.assertFalse(r1p1a is r1p1b)
        self.assertEqual(r1p1a.datatype, r1p1b.datatype)
        self.assertEqual(r1p1a.name, r1p1b.name)
        self.assertFalse(r1p1a.name is r1p1b.name)
        self.assertEqual(r1p1a.description, r1p1b.description)
        self.assertFalse(r1p1a.description is r1p1b.description)
        self.assertEqual(r1p1a.languageIn, r1p1b.languageIn)
        self.assertFalse(r1p1a.languageIn is r1p1b.languageIn)
        self.assertTrue(r1p1b.uniqueLang)
        self.assertEqual(r1p1a.minCount, r1p1b.minCount)
        self.assertEqual(r1p1a.order, r1p1b.order)

        r1p2a = r1a[Xsd_QName(f'{dm_name}:authors')]
        r1p2b = r1b[Xsd_QName(f'{dm_name}:authors')]
        self.assertFalse(r1p2a is r1p2b)
        self.assertEqual(r1p2a.toClass, r1p2b.toClass)
        self.assertFalse(r1p2a.toClass is r1p2b.toClass)
        self.assertEqual(r1p2a.name, r1p2b.name)
        self.assertFalse(r1p2a.name is r1p2b.name)
        self.assertEqual(r1p2a.description, r1p2b.description)
        self.assertFalse(r1p2a.description is r1p2b.description)
        self.assertEqual(r1p2a.minCount, r1p2b.minCount)
        self.assertEqual(r1p2a.order, r1p2b.order)


        r2a = dma[Xsd_QName(f'{dm_name}:Page')]
        r2b = dmb[Xsd_QName(f'{dm_name}:Page')]
        self.assertFalse(r2a is r2b)
        r2p1a = r2a[Xsd_QName(f'{dm_name}:pagenum')]
        r2p1b = r2b[Xsd_QName(f'{dm_name}:pagenum')]
        self.assertFalse(r2p1a is r2p1b)
        self.assertEqual(r2p1a.datatype, r2p1b.datatype)
        self.assertEqual(r2p1a.name, r2p1b.name)
        self.assertFalse(r2p1a.name is r2p1b.name)
        self.assertEqual(r2p1a.maxCount, r2p1b.maxCount)
        self.assertEqual(r2p1a.minCount, r2p1b.minCount)

        r2p2a = r2a[Xsd_QName(f'{dm_name}:inbook')]
        r2p2b = r2b[Xsd_QName(f'{dm_name}:inbook')]
        self.assertFalse(r2p2a is r2p2b)
        self.assertEqual(r2p2a[PropClassAttr.CLASS], r2p2b[PropClassAttr.CLASS])
        self.assertFalse(r2p2a[PropClassAttr.CLASS] is r2p2b[PropClassAttr.CLASS])
        self.assertEqual(r2p2a[PropClassAttr.NAME], r2p2b[PropClassAttr.NAME])
        self.assertFalse(r2p2a[PropClassAttr.NAME] is r2p2b[PropClassAttr.NAME])
        self.assertEqual(r2p2a.maxCount, r2p2b.maxCount)
        self.assertEqual(r2p2a.minCount, r2p2b.minCount)
        self.assertEqual(r2p2a.order, r2p2b.order)


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
        self.assertEqual(r1p1.datatype, XsdDatatypes.langString)
        self.assertEqual(r1p1.name, LangString(["Title@en", "Titel@de"]))
        self.assertEqual(r1p1.description, LangString(["Title of book@en", "Titel des Buches@de"]))
        self.assertEqual(r1p1.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(r1p1.uniqueLang)
        self.assertEqual(r1p1.minCount, Xsd_integer(1))
        self.assertEqual(r1p1.order, Xsd_decimal(1))

        r1p2 = r1[Xsd_QName(f'{dm_name}:authors')]
        self.assertEqual(r1p2.toClass, Xsd_QName('oldap:Person'))
        self.assertEqual(r1p2.name, LangString(["Author(s)@en", "Autor(en)@de"]))
        self.assertEqual(r1p2.description, LangString(["Writers of the Book@en", "Schreiber*innen des Buchs@de"]))
        self.assertEqual(r1p2.minCount, Xsd_integer(1))
        self.assertEqual(r1p2.order, Xsd_decimal(2))

        r2 = dm2[Xsd_QName(f'{dm_name}:Page')]
        r2p1 = r2[Xsd_QName(f'{dm_name}:pagenum')]
        self.assertEqual(r2p1.datatype, XsdDatatypes.int)
        self.assertEqual(r2p1.name, LangString(["Pagenumber@en", "Seitennummer@de"]))
        self.assertEqual(r2p1.maxCount, Xsd_integer(1))
        self.assertEqual(r2p1.minCount, Xsd_integer(1))

        r2p2 = r2[Xsd_QName(f'{dm_name}:inbook')]
        self.assertEqual(r2p2[PropClassAttr.CLASS], Iri(f'{dm_name}:Book'))
        self.assertEqual(r2p2[PropClassAttr.NAME], LangString(["Pagenumber@en", "Seitennummer@de"]))
        self.assertEqual(r2p2.maxCount, Xsd_integer(1))
        self.assertEqual(r2p2.minCount, Xsd_integer(1))
        self.assertEqual(r2p2.order, Xsd_decimal(2))

    # @unittest.skip('Work in progress')
    def test_datamodel_read(self):
        model = DataModel.read(self._connection, self._sysproject, ignore_cache=True)
        self.assertEqual(set(model.get_propclasses()), {
            Xsd_QName("oldap:hasDefaultDataPermission"),
            Xsd_QName("oldap:hasAdminPermission"),
            Xsd_QName("oldap:hasDataPermission"),
        })
        self.assertEqual(model[Xsd_QName("oldap:hasDefaultDataPermission")].toClass, Xsd_QName("oldap:DataPermission"))
        self.assertEqual(model[Xsd_QName("oldap:hasDefaultDataPermission")].appliesToProperty, Xsd_QName("oldap:hasRole"))

        self.assertEqual(model[Xsd_QName("oldap:hasAdminPermission")].toClass, Xsd_QName('oldap:AdminPermission'))
        self.assertEqual(model[Xsd_QName("oldap:hasAdminPermission")].appliesToProperty, Xsd_QName('oldap:inProject'))

        self.assertEqual(model[Xsd_QName("oldap:hasDataPermission")].toClass, Xsd_QName('oldap:DataPermission'))
        self.assertEqual(model[Xsd_QName("oldap:hasDataPermission")].appliesToProperty, Xsd_QName("oldap:attachedToRole"))

        self.assertEqual(set(model.get_resclasses()), {
            Xsd_QName("oldap:Project"),
            Xsd_QName("oldap:User"),
            Xsd_QName("oldap:OldapList"),
            Xsd_QName("oldap:OldapListNode"),
            Xsd_QName("oldap:AdminPermission"),
            Xsd_QName("oldap:DataPermission"),
            Xsd_QName("oldap:Role"),
            Xsd_QName("oldap:Thing"),
            Xsd_QName("oldap:ExternalOntology"),
        })

        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectShortName')].name, LangString("Projekt ID@de", "Project ID@en"))
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectShortName')].description, LangString("A unique NCName identifying the project@en"))
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectShortName')].datatype, XsdDatatypes.NCName)
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectShortName')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectShortName')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectShortName')].order, 1.0)

        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectEnd')].datatype, XsdDatatypes.date)
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectEnd')].name, LangString("The date when the project wll end/has ended@en"))
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectEnd')].order, 6.0)
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectEnd')].maxCount, 1)

        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('rdfs:comment')].datatype, XsdDatatypes.langString)
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('rdfs:comment')].uniqueLang, Xsd_boolean(True))
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('rdfs:comment')].languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:namespaceIri')].name, LangString("Namespace IRI@en"))
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:namespaceIri')].description, LangString("Describes a namespace@en"))
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:namespaceIri')].nodeKind, Xsd_QName('sh:IRI'))
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:namespaceIri')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:namespaceIri')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:namespaceIri')].order, 2.0)

        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectStart')].datatype, XsdDatatypes.date)
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectStart')].name, LangString("Start date@en"))
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectStart')].description, LangString("The date when the project will start/has started"))
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectStart')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectStart')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Project")].properties[Xsd_QName('oldap:projectStart')].order, 5.0)

        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('oldap:userId')].datatype, XsdDatatypes.NCName)
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('oldap:userId')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('oldap:userId')].maxCount, 1)

        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:familyName')].datatype, XsdDatatypes.string)
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:familyName')].name, LangString("Family name@en", "Familiennamen@de", "Nom de famillie@fr", "Nome della famiglia@it"))
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:familyName')].description, LangString("The family name of some person.@en"))
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:familyName')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:familyName')].maxCount, 1)

        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:givenName')].datatype, XsdDatatypes.string)
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:givenName')].name, LangString("Given name@en", "Vornamen@de", "Prénom@fr", "Nome@it"))
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:givenName')].description, LangString("The given name of some person@en"))
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:givenName')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:givenName')].maxCount, 1)

        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:email')].datatype, XsdDatatypes.string)
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:email')].name, LangString("Email@en", "Email@de", "Courriel@fr", "E-mail@it"))
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:email')].description, LangString("Email address.@en"))
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:email')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('schema:email')].maxCount, 1)

        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('oldap:credentials')].datatype, XsdDatatypes.string)
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('oldap:credentials')].name, LangString("Password@en", "Passwort@de", "Mot de passe@fr", "Password@it"))
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('oldap:credentials')].description, LangString("Password for user.@en"))
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('oldap:credentials')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('oldap:credentials')].maxCount, 1)

        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('oldap:inProject')].toClass, Xsd_QName('oldap:Project'))
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('oldap:isActive')].datatype, XsdDatatypes.boolean)
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('oldap:isActive')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('oldap:isActive')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:User")].properties[Xsd_QName('oldap:hasRole')].toClass, Xsd_QName('oldap:Role'))

        self.assertTrue(model[Xsd_QName("oldap:OldapList")].closed)
        self.assertEqual(model[Xsd_QName("oldap:OldapList")].properties[Xsd_QName('skos:prefLabel')].datatype, XsdDatatypes.langString)
        self.assertEqual(model[Xsd_QName("oldap:OldapList")].properties[Xsd_QName('skos:prefLabel')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:OldapList")].properties[Xsd_QName('skos:prefLabel')].uniqueLang, Xsd_boolean(True))
        self.assertEqual(model[Xsd_QName("oldap:OldapList")].properties[Xsd_QName('skos:prefLabel')].order, 1.0)
        self.assertEqual(model[Xsd_QName("oldap:OldapList")].properties[Xsd_QName('skos:definition')].datatype, XsdDatatypes.langString)
        self.assertEqual(model[Xsd_QName("oldap:OldapList")].properties[Xsd_QName('skos:definition')].uniqueLang, Xsd_boolean(True))

        self.assertTrue(model[Xsd_QName("oldap:OldapListNode")].closed)
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('skos:inScheme')].toClass, Xsd_QName('oldap:OldapList'))
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('skos:inScheme')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('skos:inScheme')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('skos:broader')].toClass, Xsd_QName('oldap:OldapListNode'))
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('skos:broader')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('oldap:leftIndex')].datatype, XsdDatatypes.positiveInteger)
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('oldap:leftIndex')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('oldap:leftIndex')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('oldap:rightIndex')].datatype, XsdDatatypes.positiveInteger)
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('oldap:rightIndex')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('oldap:rightIndex')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('skos:prefLabel')].datatype, XsdDatatypes.langString)
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('skos:prefLabel')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('skos:prefLabel')].uniqueLang, Xsd_boolean(True))
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('skos:prefLabel')].order, 1.0)
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('skos:definition')].datatype, XsdDatatypes.langString)
        self.assertEqual(model[Xsd_QName("oldap:OldapListNode")].properties[Xsd_QName('skos:definition')].uniqueLang, Xsd_boolean(True))

        self.assertEqual(model[Xsd_QName("oldap:AdminPermission")].properties[Xsd_QName('rdfs:label')].datatype, XsdDatatypes.langString)
        self.assertEqual(model[Xsd_QName("oldap:AdminPermission")].properties[Xsd_QName('rdfs:label')].uniqueLang, Xsd_boolean(True))
        self.assertEqual(model[Xsd_QName("oldap:AdminPermission")].properties[Xsd_QName('rdfs:label')].languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertEqual(model[Xsd_QName("oldap:AdminPermission")].properties[Xsd_QName('rdfs:comment')].datatype, XsdDatatypes.langString)
        self.assertEqual(model[Xsd_QName("oldap:AdminPermission")].properties[Xsd_QName('rdfs:comment')].uniqueLang, Xsd_boolean(True))
        self.assertEqual(model[Xsd_QName("oldap:AdminPermission")].properties[Xsd_QName('rdfs:comment')].languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        self.assertEqual(model[Xsd_QName("oldap:DataPermission")].properties[Xsd_QName('oldap:permissionValue')].datatype, XsdDatatypes.integer)
        self.assertEqual(model[Xsd_QName("oldap:DataPermission")].properties[Xsd_QName('oldap:permissionValue')].name, LangString("Permission value@en", "Berechtigungswert@de", "Valeur de permission@fr", "Valore di autorizzazione@it"))
        self.assertEqual(model[Xsd_QName("oldap:DataPermission")].properties[Xsd_QName('oldap:permissionValue')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:DataPermission")].properties[Xsd_QName('oldap:permissionValue')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:DataPermission")].properties[Xsd_QName('rdfs:label')].datatype, XsdDatatypes.langString)
        self.assertEqual(model[Xsd_QName("oldap:DataPermission")].properties[Xsd_QName('rdfs:label')].uniqueLang, Xsd_boolean(True))
        self.assertEqual(model[Xsd_QName("oldap:DataPermission")].properties[Xsd_QName('rdfs:label')].languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertEqual(model[Xsd_QName("oldap:DataPermission")].properties[Xsd_QName('rdfs:comment')].datatype, XsdDatatypes.langString)
        self.assertEqual(model[Xsd_QName("oldap:DataPermission")].properties[Xsd_QName('rdfs:comment')].uniqueLang, Xsd_boolean(True))
        self.assertEqual(model[Xsd_QName("oldap:DataPermission")].properties[Xsd_QName('rdfs:comment')].languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        self.assertEqual(model[Xsd_QName("oldap:Role")].properties[Xsd_QName('oldap:definedByProject')].toClass, Xsd_QName('oldap:Project'))
        self.assertEqual(model[Xsd_QName("oldap:Role")].properties[Xsd_QName('oldap:definedByProject')].name, LangString("Defined by@en", "Definiert durch@de", "Défini par@fr", "Definito da@it"))
        self.assertEqual(model[Xsd_QName("oldap:Role")].properties[Xsd_QName('oldap:definedByProject')].description, LangString("Permission role is define by project@en",
                                                                                                                             "Der Berechtigungsrolle wird definiert durch das Projekt@de",
                                                                                                                             "Le rôle d'autorisation est défini par projet.@fr",
                                                                                                                             "Il ruolo di autorizzazione è definito dal progetto@it"))
        self.assertEqual(model[Xsd_QName("oldap:Role")].properties[Xsd_QName('oldap:definedByProject')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Role")].properties[Xsd_QName('oldap:definedByProject')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Role")].properties[Xsd_QName('rdfs:label')].datatype, XsdDatatypes.langString)
        self.assertEqual(model[Xsd_QName("oldap:Role")].properties[Xsd_QName('rdfs:label')].uniqueLang, Xsd_boolean(True))
        self.assertEqual(model[Xsd_QName("oldap:Role")].properties[Xsd_QName('rdfs:label')].languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertEqual(model[Xsd_QName("oldap:Role")].properties[Xsd_QName('rdfs:comment')].datatype, XsdDatatypes.langString)
        self.assertEqual(model[Xsd_QName("oldap:Role")].properties[Xsd_QName('rdfs:comment')].uniqueLang, Xsd_boolean(True))
        self.assertEqual(model[Xsd_QName("oldap:Role")].properties[Xsd_QName('rdfs:comment')].languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        self.assertEqual(model[Xsd_QName("oldap:Thing")].properties[Xsd_QName('oldap:createdBy')].toClass, Xsd_QName('oldap:User'))
        self.assertEqual(model[Xsd_QName("oldap:Thing")].properties[Xsd_QName('oldap:createdBy')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Thing")].properties[Xsd_QName('oldap:createdBy')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Thing")].properties[Xsd_QName('oldap:creationDate')].datatype, XsdDatatypes.dateTimeStamp)
        self.assertEqual(model[Xsd_QName("oldap:Thing")].properties[Xsd_QName('oldap:creationDate')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Thing")].properties[Xsd_QName('oldap:creationDate')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Thing")].properties[Xsd_QName('oldap:lastModifiedBy')].toClass, Xsd_QName('oldap:User'))
        self.assertEqual(model[Xsd_QName("oldap:Thing")].properties[Xsd_QName('oldap:lastModifiedBy')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Thing")].properties[Xsd_QName('oldap:lastModifiedBy')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Thing")].properties[Xsd_QName('oldap:lastModificationDate')].datatype, XsdDatatypes.dateTimeStamp)
        self.assertEqual(model[Xsd_QName("oldap:Thing")].properties[Xsd_QName('oldap:lastModificationDate')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Thing")].properties[Xsd_QName('oldap:lastModificationDate')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Thing")].properties[Xsd_QName('oldap:attachedToRole')].toClass, Xsd_QName('oldap:Role'))

        self.assertEqual(model[Xsd_QName("oldap:ExternalOntology")].properties[Xsd_QName('oldap:prefix')].datatype, XsdDatatypes.NCName)
        self.assertEqual(model[Xsd_QName("oldap:ExternalOntology")].properties[Xsd_QName('oldap:prefix')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:ExternalOntology")].properties[Xsd_QName('oldap:prefix')].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:ExternalOntology")].properties[Xsd_QName('oldap:namespaceIri')].name, LangString("Namespace IRI@en"))
        self.assertEqual(model[Xsd_QName("oldap:ExternalOntology")].properties[Xsd_QName('oldap:namespaceIri')].description, LangString("Describes a namespace@en"))
        self.assertEqual(model[Xsd_QName("oldap:ExternalOntology")].properties[Xsd_QName('oldap:namespaceIri')].nodeKind, Xsd_QName('sh:IRI'))
        self.assertEqual(model[Xsd_QName("oldap:ExternalOntology")].properties[Xsd_QName('oldap:namespaceIri')].minCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:ExternalOntology")].properties[Xsd_QName('oldap:namespaceIri')].maxCount, 1)


    def test_datamodel_read_shared(self):
        model = DataModel.read(self._connection, self._sharedproject, ignore_cache=True)
        self.assertEqual(set(model.get_resclasses()), {
            Xsd_QName("oldap:Dating"),
            Xsd_QName("shared:MediaObject"),
        })

        sc = set(model[Xsd_QName("oldap:Dating")].superclass.keys())
        self.assertEqual(sc, {Xsd_QName("oldap:Thing")})
        self.assertEqual(model[Xsd_QName("oldap:Dating")].creator, Iri("https://orcid.org/0000-0003-1681-4036"))
        self.assertEqual(model[Xsd_QName("oldap:Dating")].created, Xsd_dateTime("2025-01-01T00:00:00+02:00"))
        self.assertEqual(model[Xsd_QName("oldap:Dating")].contributor, Iri("https://orcid.org/0000-0003-1681-4036"))
        self.assertEqual(model[Xsd_QName("oldap:Dating")].modified, Xsd_dateTime("2025-01-01T00:00:00+02:00"))
        self.assertEqual(model[Xsd_QName("oldap:Dating")].label, LangString("Dating object@en", "Datumsobjekt@de", "Objet de date@fr", "Oggetto data@it"))
        self.assertTrue(model[Xsd_QName("oldap:Dating")].closed)

        props = model[Xsd_QName("oldap:Dating")].properties.keys()
        self.assertEqual(set(props), {Xsd_QName("oldap:normalizedBegin"),
                                      Xsd_QName("oldap:inCalendar"),
                                      Xsd_QName("oldap:before"),
                                      Xsd_QName("oldap:verbatimDate"),
                                      Xsd_QName("oldap:normalizedEnd"),
                                      Xsd_QName("oldap:datePrecision")})

        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:verbatimDate")].datatype, XsdDatatypes.string)
        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:verbatimDate")].name, LangString(
            "Verbatim date@en",
            "Wörtliche Zeitangabe@de",
            "Citation littérale@fr",
            "Tempo letterale@it"))
        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:verbatimDate")].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:verbatimDate")].order, 1.0)

        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:normalizedBegin")].datatype, XsdDatatypes.date)
        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:normalizedBegin")].name, LangString(
            "Normalized begin (ISO Gregorian)@en",
            "Normierter Beginn (ISO-Gregorian)@de",
            "Début normalisé (calendrier grégorien ISO)@fr",
            "Inizio normalizzato (calendario gregoriano ISO)@it"))
        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:normalizedBegin")].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:normalizedBegin")].order, 2.0)

        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:normalizedEnd")].datatype, XsdDatatypes.date)
        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:normalizedEnd")].name, LangString(
            "Normalized end (ISO Gregorian)@en",
            "Normalisiertes Ende (ISO-Gregorian)@de",
            "Fin normalisée (calendrier grégorien ISO)@fr",
            "Fine normalizzata (calendario gregoriano ISO)@it"))
        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:normalizedEnd")].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:normalizedEnd")].order, 3.0)

        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:datePrecision")].toClass, Xsd_QName("oldap:DatePrecision"))

        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:inCalendar")].toClass, Xsd_QName("oldap:Calendar"))
        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:inCalendar")].name, LangString(
            "Calendar of the original date@en",
            "Kalender des ursprünglichen Datums@de",
            "Calendrier de la date d'origine@fr",
            "Calendario della data originale@it"))
        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:inCalendar")].maxCount, 1)
        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:inCalendar")].order, 5.0)

        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:before")].toClass, Xsd_QName("oldap:Dating"))
        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:before")].name, LangString(
            "before other event@en",
            "vor einem anderen Ereignis@de",
            "avant un autre événement@fr",
            "prima di un altro evento@it"))
        self.assertEqual(model[Xsd_QName("oldap:Dating")].properties[Xsd_QName("oldap:before")].order, 6.0)


        sc = set(model[Xsd_QName("shared:MediaObject")].superclass.keys())
        self.assertEqual(sc, {Xsd_QName("oldap:Thing")})
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].creator, Iri("https://orcid.org/0000-0003-1681-4036"))
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].created, Xsd_dateTime("2025-01-01T00:00:00+02:00"))
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].contributor, Iri("https://orcid.org/0000-0003-1681-4036"))
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].modified, Xsd_dateTime("2025-01-01T00:00:00+02:00"))
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].label, LangString("MediaObject@en", "Medienobjekt@de", "MediaObject@fr", "MediaObject@it"))
        self.assertTrue(model[Xsd_QName("shared:MediaObject")].closed)


        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("dcterms:type")].inSet, {Xsd_QName("dcmitype:Image"),
                                                                                                              Xsd_QName("dcmitype:Collection"),
                                                                                                              Xsd_QName("dcmitype:MovingImage"),
                                                                                                              Xsd_QName("dcmitype:Dataset"),
                                                                                                              Xsd_QName("dcmitype:Sound"),
                                                                                                              Xsd_QName("dcmitype:StillImage"),
                                                                                                              Xsd_QName("dcmitype:Text")
                                                                                                              })
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("dcterms:type")].minCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("dcterms:type")].maxCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("dcterms:type")].order, 1.0)

        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:originalName")].datatype, XsdDatatypes.string)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:originalName")].name, LangString("Original Filename@en", "Nom orignal du fichier@fr", "Nome documento originale@it", "Originaler Dateiname@de"))
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:originalName")].maxCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:originalName")].minCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:originalName")].order, 2.0)

        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:originalMimeType")].datatype, XsdDatatypes.string)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:originalMimeType")].name, LangString("Mimetype original@fr", "Mimetype originale@it", "Originaler Mimetype@de", "Original mimetype@en"))
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:originalMimeType")].maxCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:originalMimeType")].minCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:originalMimeType")].order, 3.0)

        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:serverUrl")].datatype, XsdDatatypes.anyURI)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:serverUrl")].maxCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:serverUrl")].minCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:serverUrl")].order, 4.0)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:serverUrl")].name, LangString("Server URL@fr", "Server URL@en", "URL des servers@de", "Server URL@it"))

        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:assetId")].datatype, XsdDatatypes.string)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:assetId")].name, LangString("ID de l'immagine@it", "Image ID@en", "ID de l'image@fr", "ID des Bilder@de"))
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:assetId")].minCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:assetId")].maxCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:assetId")].order, 5.0)

        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:protocol")].datatype, XsdDatatypes.string)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:protocol")].inSet, {'iiif', 'custom', 'http'})
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:protocol")].minCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:protocol")].maxCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:protocol")].order, 6.0)

        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:derivativeName")].datatype, XsdDatatypes.string)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:derivativeName")].minCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:derivativeName")].maxCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:derivativeName")].order, 7.0)

        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:path")].datatype, XsdDatatypes.string)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:path")].minCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:path")].maxCount, 1)
        self.assertEqual(model[Xsd_QName("shared:MediaObject")].properties[Xsd_QName("shared:path")].order, 8.0)



    def test_datamodel_read_test(self):
        model = DataModel.read(self._connection, self._project, ignore_cache=True)
        ontos = model.get_extontos()
        crm = model[Xsd_QName('test:crm')]
        self.assertEqual(crm.prefix, 'crm')
        self.assertEqual(crm.namespaceIri, 'http://www.cidoc-crm.org/cidoc-crm/')
        context = model.context
        self.assertEqual(context['crm'], 'http://www.cidoc-crm.org/cidoc-crm/')

    def test_datamode_json(self):
        model = DataModel.read(self._connection, self._project, ignore_cache=True)
        jsonstr = json.dumps(model, default=serializer.encoder_default, indent=3)
        model2 = json.loads(jsonstr, object_hook=serializer.make_decoder_hook(self._connection))


    def test_datamodel_cache(self):
        start = time()
        model = DataModel.read(self._connection, self._sysproject, ignore_cache=True)
        end = time()
        print(f"No cache execution time: {end - start:.4f} seconds")

        start = time()
        model = DataModel.read(self._connection, self._sysproject, ignore_cache=False)
        end = time()
        print(f"With cache execution time: {end - start:.4f} seconds")

    def test_datamode_create_and_mod_A(self):

        dmname = self._dmprojectA.projectShortName

        p1 = PropertyClass(con=self._connection,
                           project=self._dmprojectA,
                           property_class_iri=Xsd_QName(self._dmprojectA.projectShortName, 'hasGaga'),
                           type=[OwlPropertyType.ReflexiveProperty, OwlPropertyType.TransitiveProperty],
                           datatype=XsdDatatypes.string,
                           minCount=1,
                           order=1)
        r1 = ResourceClass(con=self._connection,
                           owlclass_iri=Xsd_QName(self._dmprojectA.projectShortName, 'GAGA'),
                           project=self._dmprojectA,
                           properties=[p1])

        dm = DataModel(con=self._connection,
                       project=self._dmprojectA,
                       resclasses=[r1])
        dm.create()

        dm = DataModel.read(self._connection, self._dmprojectA, ignore_cache=True)
        dm[Xsd_QName(dmname, 'GAGA')][Xsd_QName(dmname, 'hasGaga')].type.add(OwlPropertyType.IrreflexiveProperty)
        dm[Xsd_QName(dmname, 'GAGA')][Xsd_QName(dmname, 'hasGaga')].type.discard(OwlPropertyType.ReflexiveProperty)
        dm.update()

        dm = DataModel.read(self._connection, self._dmprojectA, ignore_cache=True)

        self.assertEqual(dm[Xsd_QName(dmname, 'GAGA')][Xsd_QName(dmname, 'hasGaga')].type,
                         {OwlPropertyType.IrreflexiveProperty,
                          OwlPropertyType.OwlDataProperty,
                          OwlPropertyType.TransitiveProperty})

        dm.delete()

    def test_datamode_create_and_mod_B(self):

        dmname = self._dmprojectA.projectShortName

        p1 = PropertyClass(con=self._connection,
                           project=self._dmprojectA,
                           property_class_iri=Xsd_QName(self._dmprojectA.projectShortName, 'hasGaga'),
                           appliesToProperty=Xsd_QName(dmname, 'hasStar'),
                           type=[OwlPropertyType.ReflexiveProperty, OwlPropertyType.TransitiveProperty],
                           datatype=XsdDatatypes.string,
                           minCount=1,
                           order=1)

        dm = DataModel(con=self._connection,
                       project=self._dmprojectA,
                       propclasses=[p1])
        dm.create()

        dm = DataModel.read(self._connection, self._dmprojectA, ignore_cache=True)
        dm[Xsd_QName(dmname, 'hasGaga')].type.add(OwlPropertyType.IrreflexiveProperty)
        dm[Xsd_QName(dmname, 'hasGaga')].type.discard(OwlPropertyType.ReflexiveProperty)
        dm.update()

        dm = DataModel.read(self._connection, self._dmprojectA, ignore_cache=True)

        self.assertEqual(dm[Xsd_QName(dmname, 'hasGaga')].type,
                         {OwlPropertyType.IrreflexiveProperty,
                          OwlPropertyType.OwlDataProperty,
                          OwlPropertyType.TransitiveProperty})

        dm.delete()


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
                                property_class_iri=Xsd_QName(f'{dm_name}:commentToTitle'),
                                datatype=XsdDatatypes.string,
                                name=LangString(["Publication Year@en", "Publicationsjahr@de"]),
                                appliesToProperty=Xsd_QName(f'{dm_name}:title'))
        dm[Xsd_QName(f'{dm_name}:commentToTitle')] = pubyear
        self.assertEqual({Xsd_QName(f'{dm_name}:commentToTitle'): PropertyClassChange(None, Action.CREATE)}, dm.changeset)

        dm[Xsd_QName(f'{dm_name}:comment')].name[Language.FR] = 'Commentaire'
        self.assertEqual({
            Xsd_QName(f'{dm_name}:commentToTitle'): PropertyClassChange(None, Action.CREATE),
            Xsd_QName(f'{dm_name}:comment'): PropertyClassChange(None, Action.MODIFY)
        }, dm.changeset)

        dm[Xsd_QName(f'{dm_name}:Book')][Xsd_QName(f'{dm_name}:authors')].name[Language.FR] = "Ecrivain(s)"
        self.maxDiff = None
        self.assertEqual({
            Xsd_QName(f'{dm_name}:commentToTitle'): PropertyClassChange(None, Action.CREATE),
            Xsd_QName(f'{dm_name}:comment'): PropertyClassChange(None, Action.MODIFY),
            Xsd_QName(f'{dm_name}:Book'): ResourceClassChange(None, Action.MODIFY)
        }, dm.changeset)

        pagename = PropertyClass(con=self._connection,
                                 project=self._dmprojectA,
                                 property_class_iri=Xsd_QName(f'{dm_name}:pageName'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString(["Page name@en", "Seitenbezeichnung@de"]),
                                 maxCount=1,
                                 minCount=1)

        dm[Xsd_QName(f'{dm_name}:Page')][Xsd_QName(f'{dm_name}:pageName')] = pagename
        self.assertEqual({
            Xsd_QName(f'{dm_name}:commentToTitle'): PropertyClassChange(None, Action.CREATE),
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
                                appliesToProperty=Xsd_QName(f'{dm_name}:title'),
                                name=LangString(["Publication Year@en", "Publicationsjahr@de"]))
        dm[Xsd_QName(f'{dm_name}:pubYear')] = pubyear

        #
        # Modify an internal property
        #
        dm[Xsd_QName(f'{dm_name}:Book')][Xsd_QName(f'{dm_name}:authors')].name[Language.FR] = "Ecrivain(s)"


        #
        # Add a new property as internal property
        #
        pagename = PropertyClass(con=self._connection,
                                 project=self._dmprojectB,
                                 property_class_iri=Xsd_QName(f'{dm_name}:pageName'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString(["Page name@en", "Seitenbezeichnung@de"]))

        dm[Xsd_QName(f'{dm_name}:Page')][Xsd_QName(f'{dm_name}:pageName')] = pagename

        dm.update()

        del dm

        dm = DataModel.read(self._connection, self._dmprojectB, ignore_cache=True)
        self.assertIsNotNone(dm.get(Xsd_QName(f'{dm_name}:pubYear')))
        self.assertEqual(dm[Xsd_QName(f'{dm_name}:pubYear')].datatype, XsdDatatypes.gYear)
        self.assertEqual(dm[Xsd_QName(f'{dm_name}:Book')][Xsd_QName(f'{dm_name}:authors')].name[Language.FR], "Ecrivain(s)")
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
        del dm[Xsd_QName(f'{dm_name}:Page')][Xsd_QName(f'{dm_name}:pagenum')]

        dm.update()

        del dm

        dm = DataModel.read(self._connection, self._dmprojectC, ignore_cache=True)
        self.assertIsNone(dm[Xsd_QName(f'{dm_name}:Page')].get(Xsd_QName(f'{dm_name}:pagenum')))

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
                                appliesToProperty=Xsd_QName(f'{dm_name}:authors'),
                                name=LangString(["Publication YearE@en", "PublicationsjahrE@de"]))
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
        dm[Xsd_QName(f'{dm_name}:Book')].add_superclasses([Xsd_QName(dm_name, 'Page'), Xsd_QName('dcterms:Event')])

        dm.update()

        dm = DataModel.read(self._connection, self._dmprojectI, ignore_cache=True)
        tmp = set(dm[Xsd_QName(f'{dm_name}:Book')].superclass.keys())
        assert tmp == {Xsd_QName('oldap:Thing'), Xsd_QName(dm_name, 'Page'), Xsd_QName('dcterms:Event')}

        dm[Xsd_QName(f'{dm_name}:Book')].del_superclasses([f'{dm_name}:Page'])
        dm.update()
        dm = DataModel.read(self._connection, self._dmprojectI, ignore_cache=True)
        tmp = set([key for key, val in dm[Xsd_QName(f'{dm_name}:Book')].superclass.items()])
        assert tmp == {'oldap:Thing', 'dcterms:Event'}

    def test_datamode_modify_J(self):
        dm_name = self._dmprojectI.projectShortName
        dm = self.generate_a_datamodel(self._dmprojectI)
        dm.create()
        dm = DataModel.read(self._connection, self._dmprojectI, ignore_cache=True)
        dm[Xsd_QName(f'{dm_name}:Book')][Xsd_QName(f'{dm_name}:authors')].maxCount = Xsd_integer(42)
        dm.update()
        dm = DataModel.read(self._connection, self._dmprojectI, ignore_cache=True)
        assert dm[Xsd_QName(f'{dm_name}:Book')][Xsd_QName(f'{dm_name}:authors')].maxCount == Xsd_integer(42)

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
                                        appliesToProperty=Xsd_QName(f'{dm_name}:allowsAssertion'),
                                        name=LangString(["Generic comment@en", "Allgemeiner Kommentar@de"]))
        dm[Xsd_QName(f'{dm_name}:genericComment')] = generic_comment
        dm.update()
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        p1 = dm[Xsd_QName(f'{dm_name}:genericComment')]
        self.assertEqual(p1.datatype, XsdDatatypes.string)

        #
        # Modifying the property
        #
        p1.description = LangString("For testing purposes only@en")
        dm.update()
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
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
                               languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                               minCount=Xsd_integer(1),
                               order=1)

        authorsX = PropertyClass(con=self._connection,
                                 project=self._dmproject,
                                 property_class_iri=Xsd_QName(f'{dm_name}:authorsX'),
                                 toClass=Xsd_QName('oldap:Person'),
                                 name=LangString(["Author(s)X@en", "Autor(en)X@de"]),
                                 description=LangString(["Writers of the BookX@en", "Schreiber*innen des BuchsX@de"]),
                                 minCount=Xsd_integer(1),
                                 order=2)

        bookX = ResourceClass(con=self._connection,
                              project=self._dmproject,
                              owlclass_iri=Xsd_QName(f'{dm_name}:BookX'),
                              label=LangString(["BookX@en", "BuchX@de"]),
                              comment=LangString("Ein Buch mit SeitenX@en"),
                              closed=Xsd_boolean(True),
                              properties=[titleX, authorsX])
        dm[Xsd_QName(f'{dm_name}:BookX')] = bookX
        dm.update()

        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)

        p1 = dm[Xsd_QName(f'{dm_name}:genericComment')]
        self.assertEqual(p1.datatype, XsdDatatypes.string)
        self.assertEqual(p1.description, LangString("For testing purposes only@en"))

        r1 = dm[Xsd_QName(f'{dm_name}:BookX')]

        r1p1 = r1[Xsd_QName(f'{dm_name}:titleX')]
        self.assertEqual(r1p1.datatype, XsdDatatypes.langString)
        self.assertEqual(r1p1.name, LangString(["TitleX@en", "TitelX@de"]))
        self.assertEqual(r1p1.description, LangString(["TitleX of book@en", "TitelX des Buches@de"]))
        self.assertEqual(r1p1.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(r1p1.uniqueLang)
        self.assertEqual(r1p1.minCount, Xsd_integer(1))
        self.assertEqual(r1p1.order, Xsd_decimal(1))

        r1p2 = r1[Xsd_QName(f'{dm_name}:authorsX')]
        self.assertEqual(r1p2.toClass, Xsd_QName('oldap:Person'))
        self.assertEqual(r1p2.name, LangString(["Author(s)X@en", "Autor(en)X@de"]))
        self.assertEqual(r1p2.description, LangString(["Writers of the BookX@en", "Schreiber*innen des BuchsX@de"]))
        self.assertEqual(r1p2.minCount, Xsd_integer(1))
        self.assertEqual(r1p2.order, Xsd_decimal(2))

    def test_datamodel_standalone_link_property(self):
        dm = DataModel(con=self._connection,
                       project=self._dmprojectJ)
        dm.create()
        dm = DataModel.read(self._connection, self._dmprojectJ, ignore_cache=True)
        dm_name = self._dmprojectJ.projectShortName

        bookX = ResourceClass(con=self._connection,
                              project=self._dmprojectJ,
                              owlclass_iri=Xsd_QName(f'{dm_name}:BookZ'),
                              label=LangString(["BookZ@en", "BuchZ@de"]),
                              comment=LangString("Ein Buch mit SeitenZ@en"))
        dm[Xsd_QName(f'{dm_name}:BookZ')] = bookX
        dm.update()
        dm = DataModel.read(self._connection, self._dmprojectJ, ignore_cache=True)

        #
        # add a standalone property
        #
        generic_comment = PropertyClass(con=self._connection,
                                        project=self._dmprojectJ,
                                        property_class_iri=Xsd_QName(f'{dm_name}:bookLink'),
                                        toClass=Xsd_QName(f'{dm_name}:BookZ'),
                                        appliesToProperty=Xsd_QName(f'{dm_name}:rdfStar2'),
                                        name=LangString(["Generic comment@en", "Allgemeiner Kommentar@de"]))
        dm[Xsd_QName(f'{dm_name}:bookLink')] = generic_comment
        dm.update()
        dm = DataModel.read(self._connection, self._dmprojectJ, ignore_cache=True)
        self.assertEqual(dm[Xsd_QName(f'{dm_name}:bookLink')].toClass, Xsd_QName(f'{dm_name}:BookZ'))

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
                                        appliesToProperty=Xsd_QName(f'{dm_name}:rdfStar3'),
                                        name=LangString(["Generic comment@en", "Allgemeiner Kommentar@de"]))
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
                                        appliesToProperty=Xsd_QName(f'{dm_name}:rdfStar3'),
                                        name=LangString(["Generic comment@en", "Allgemeiner Kommentar@de"]))
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
                              languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                              minCount=Xsd_integer(1),
                              order=1)


        dm[Xsd_QName(f'{dm_name}:Book')][Xsd_QName(f'{dm_name}:title')] = title

        with self.assertRaises(OldapErrorAlreadyExists):
            dm.update()

    def test_update_parts(self):
        dm_name = self._dmproject.projectShortName
        generic_commentY = PropertyClass(con=self._connection,
                                         project=self._dmproject,
                                         property_class_iri=Xsd_QName(f'{dm_name}:genericCommentY'),
                                         datatype=XsdDatatypes.string,
                                         appliesToProperty=Xsd_QName(f'{dm_name}:rdfStar4'),
                                         name=LangString(["Generic commentY@en", "Allgemeiner KommentarY@de"]))

        titleY = PropertyClass(con=self._connection,
                               project=self._dmproject,
                               property_class_iri=Xsd_QName(f'{dm_name}:titleY'),
                               datatype=XsdDatatypes.langString,
                               name=LangString(["TitleY@en", "TitelY@de"]),
                               description=LangString(["TitleY of book@en", "TitelY des Buches@de"]),
                               uniqueLang=Xsd_boolean(True),
                               languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                               minCount=Xsd_integer(1),
                               order=1)

        authorsY = PropertyClass(con=self._connection,
                                 project=self._dmproject,
                                 property_class_iri=Xsd_QName(f'{dm_name}:authorsY'),
                                 toClass=Iri('oldap:Person'),
                                 name=LangString(["Author(s)Y@en", "Autor(en)Y@de"]),
                                 description=LangString(["Writers of the BookY@en", "Schreiber*innen des BuchsY@de"]),
                                 minCount=Xsd_integer(1),
                                 order=2)

        bookY = ResourceClass(con=self._connection,
                              project=self._dmproject,
                              owlclass_iri=Xsd_QName(f'{dm_name}:BookY'),
                              label=LangString(["BookY@en", "BuchY@de"]),
                              comment=LangString("Ein Buch mit SeitenY@en"),
                              closed=Xsd_boolean(True),
                              properties=[titleY, authorsY])

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

        r1 = dm[Xsd_QName(f'{dm_name}:BookY')]

        r1p1 = r1[Xsd_QName(f'{dm_name}:titleY')]
        self.assertEqual(r1p1.datatype, XsdDatatypes.langString)
        self.assertEqual(r1p1.name, LangString(["TitleY@en", "TitelY@de"]))
        self.assertEqual(r1p1.description, LangString(["TitleY of book@en", "TitelY des Buches@de"]))
        self.assertEqual(r1p1.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(r1p1.uniqueLang)
        self.assertEqual(r1p1.minCount, Xsd_integer(1))
        self.assertEqual(r1p1.order, Xsd_decimal(1))

        r1p2 = r1[Xsd_QName(f'{dm_name}:authorsY')]
        self.assertEqual(r1p2.toClass, Xsd_QName('oldap:Person'))
        self.assertEqual(r1p2.name, LangString(["Author(s)Y@en", "Autor(en)Y@de"]))
        self.assertEqual(r1p2.description, LangString(["Writers of the BookY@en", "Schreiber*innen des BuchsY@de"]))
        self.assertEqual(r1p2.minCount, Xsd_integer(1))
        self.assertEqual(r1p2.order, Xsd_decimal(2))

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
        dm[Xsd_QName(f'{dm_name}:BookY')][Xsd_QName(f'{dm_name}:pubDateY')] = pubDateY

        #
        # Delete a property
        #
        del dm[Xsd_QName(f'{dm_name}:BookY')][Xsd_QName(f'{dm_name}:authorsY')]

        dm.update()
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        r1 = dm[Xsd_QName(f'{dm_name}:BookY')]

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

    def test_update_mincount(self):
        dm_name = self._dmproject.projectShortName
        generic_commentZ = PropertyClass(con=self._connection,
                                         project=self._dmproject,
                                         property_class_iri=Xsd_QName(f'{dm_name}:genericCommentZ'),
                                         datatype=XsdDatatypes.string,
                                         appliesToProperty=Xsd_QName(f'{dm_name}:starProp5'),
                                         name=LangString(["Generic commentZ@en", "Allgemeiner KommentarZ@de"]))

        titleZ = PropertyClass(con=self._connection,
                               project=self._dmproject,
                               property_class_iri=Xsd_QName(f'{dm_name}:titleZ'),
                               datatype=XsdDatatypes.langString,
                               name=LangString(["TitleZ@en", "TitelZ@de"]),
                               description=LangString(["TitleZ of book@en", "TitelZ des Buches@de"]),
                               uniqueLang=Xsd_boolean(True),
                               languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                               minCount=Xsd_integer(1),
                               order=1)

        authorsZ = PropertyClass(con=self._connection,
                                 project=self._dmproject,
                                 property_class_iri=Xsd_QName(f'{dm_name}:authorsZ'),
                                 toClass=Iri('oldap:Person'),
                                 name=LangString(["Author(s)Z@en", "Autor(en)Z@de"]),
                                 description=LangString(["Writers of the BookZ@en", "Schreiber*innen des BuchsZ@de"]),
                                 minCount=Xsd_integer(1),
                                 order=2)

        bookZ = ResourceClass(con=self._connection,
                              project=self._dmproject,
                              owlclass_iri=Xsd_QName(f'{dm_name}:BookZ'),
                              label=LangString(["BookZ@en", "BuchZ@de"]),
                              comment=LangString("Ein Buch mit SeitenZ@en"),
                              closed=Xsd_boolean(True),
                              properties=[titleZ, authorsZ])

        dm = DataModel(con=self._connection,
                       project=self._dmproject,
                       propclasses=[generic_commentZ],
                       resclasses=[bookZ])
        dm.create()

        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        dm[Xsd_QName(f'{dm_name}:BookZ')][Xsd_QName(f'{dm_name}:authorsZ')].minCount = None
        dm.update()
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        self.assertIsNone(dm[Xsd_QName(f'{dm_name}:BookZ')][Xsd_QName(f'{dm_name}:authorsZ')].minCount)


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
                                  lessThanOrEquals="hyha:testProp",
                                  minCount=Xsd_integer(1),
                                  maxCount=3,
                                  order=1)

        Sheep = ResourceClass(con=self._connection,
                              project=proj,
                              owlclass_iri=Xsd_QName("hyha:Sheep"),
                              label=["Eine Buchseite@de", "A page of a book@en"],
                              comment=["Eine Buchseite@de","A page of a book@en"],
                              closed=Xsd_boolean(True),
                              properties=[testProp2])
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
        dm[Xsd_QName(f'{dm_name}:BookZZ')][Xsd_QName(f'{dm_name}:pubDateZ')] = pubDateZ
        dm.update()
        dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)
        test_res = dm[Xsd_QName(f'{dm_name}:BookZZ')]
        self.assertEqual(test_res.label, LangString(["BookZZ@en", "BuchZZ@de"]))
        self.assertIsInstance(test_res[Xsd_QName(f'{dm_name}:pubDateZ')], PropertyClass)
        self.assertEqual(test_res[Xsd_QName(f'{dm_name}:pubDateZ')].property_class_iri, Xsd_QName(f'{dm_name}:pubDateZ'))

        dm.delete()
        with self.assertRaises(OldapErrorNotFound):
            dm = DataModel.read(self._connection, self._dmproject, ignore_cache=True)


    def test_delete_label_from_resource(self):
        pagename = PropertyClass(con=self._connection,
                                 project=self._dmprojectF,
                                 property_class_iri=Xsd_QName('test:testPropGaga'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString("Page designation@en", "Seitenbezeichnung@de"),
                                 minCount=Xsd_integer(1),
                                 order=1)
        page = ResourceClass(con=self._connection,
                             project=self._dmprojectF,
                             owlclass_iri=Xsd_QName("test:PageGaga"),
                             label=LangString(["Project@en", "Projekt@de"]),
                             comment=LangString(["A page of a book@en", "Seite eines Buches@de"]),
                             closed=Xsd_boolean(True),
                             properties=[pagename])
        dm = DataModel(con=self._connection,
                       project=self._dmprojectF,
                       resclasses=[page])
        dm.create()
        dm = DataModel.read(self._connection, self._dmprojectF, ignore_cache=True)
        #del dm[Iri('test:PageGaga')][ResClassAttribute.from_name('label')]
        delattr(dm[Xsd_QName('test:PageGaga')], 'label')
        dm.update()
        dm = DataModel.read(self._connection, self._dmprojectF, ignore_cache=True)
        self.assertIsNone(dm[Xsd_QName('test:PageGaga')].label)


    def test_write_trig(self):
        pagename = PropertyClass(con=self._connection,
                                 project=self._project,
                                 property_class_iri=Xsd_QName('test:pageDesignation'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString("Page designation@en", "Seitenbezeichnung@de"),
                                 minCount=Xsd_integer(1),
                                 order=1)
        pagenum = PropertyClass(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:pageNum'),
                                datatype=XsdDatatypes.positiveInteger,
                                name=LangString("Pagenumber@en", "Seitennummer@de"),
                                description=LangString("consecutive numbering of pages@en", "Konsekutive Nummerierung der Seiten@de"),
                                minCount=Xsd_integer(1),
                                maxCount=Xsd_integer(1),
                                order=2)
        pagedescription = PropertyClass(con=self._connection,
                                        project=self._project,
                                        property_class_iri=Xsd_QName('test:pageDescription'),
                                        datatype=XsdDatatypes.langString,
                                        languageIn=LanguageIn(Language.EN, Language.DE),
                                        uniqueLang=Xsd_boolean(True),
                                        order=3)
        content = PropertyClass(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:pageContent'),
                                datatype=XsdDatatypes.string,
                                maxCount=Xsd_integer(1),
                                order=4)
        inBook = PropertyClass(con=self._connection,
                               project=self._project,
                               property_class_iri=Xsd_QName('test:pageInBook'),
                               toClass=Xsd_QName('test:Book'),
                               minCount=Xsd_integer(1),
                               maxCount=Xsd_integer(1),
                               order=5)
        page = ResourceClass(con=self._connection,
                             project=self._project,
                             owlclass_iri=Xsd_QName("test:Page"),
                             #superclass=Iri('oldap:Thing'),  # no longer necessary TODO: Test it!!!!
                             label=LangString(["Project@en", "Projekt@de"]),
                             comment=LangString(["A page of a book@en", "Seite eines Buches@de"]),
                             closed=Xsd_boolean(True),
                             properties=[pagename, pagenum, pagedescription, content, inBook])

        title = PropertyClass(con=self._connection,
                              project=self._project,
                              property_class_iri=Xsd_QName('test:title'),
                              datatype=XsdDatatypes.string,
                              order=1)
        author = PropertyClass(con=self._connection,
                               project=self._project,
                               property_class_iri=Xsd_QName('test:author'),
                               toClass=Iri('test:Person'),
                               order=2)
        pubDate = PropertyClass(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:pubDate'),
                                datatype=XsdDatatypes.date,
                                order=3)
        book = ResourceClass(con=self._connection,
                             project=self._project,
                             owlclass_iri=Xsd_QName('test:Book'),
                             #superclass=Iri('oldap:Thing'),
                             label=LangString(["Book@en", "Buch@de"]),
                             closed=Xsd_boolean(True),
                             properties=[title, author, pubDate])

        familyname = PropertyClass(con=self._connection,
                                   project=self._project,
                                   property_class_iri=Xsd_QName('schema:familyName'),
                                   datatype=XsdDatatypes.string,
                                   maxCount=Xsd_integer(1),
                                   minCount=Xsd_integer(1),
                                   order=1.0)
        givenname = PropertyClass(con=self._connection,
                                   project=self._project,
                                   property_class_iri=Xsd_QName('schema:givenName'),
                                   datatype=XsdDatatypes.string,
                                   maxCount=Xsd_integer(1),
                                   minCount=Xsd_integer(1),
                                   order=2.0)


        person = ResourceClass(con=self._connection,
                               project=self._project,
                               owlclass_iri=Xsd_QName('test:Person'),
                               label=LangString(["Person@en", "Person@de"]),
                               properties=[familyname, givenname])

        dm = DataModel(con=self._connection,
                       project=self._project,
                       resclasses=[page, book, person])
        dm.write_as_trig('gaga.trig')

    @unittest.skip('Only during development....')
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

    @unittest.skip('Only during development....')
    def test_datamodel_read_fasnacht(self):
        connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        fasnacht = Project.read(connection, "fasnacht")

        model = DataModel.read(connection, fasnacht, ignore_cache=True)
        print(model)

    @unittest.skip('Only during development....')
    def test_datamodel_read_shared_TEST(self):
        connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")


        model = DataModel.read(connection, 'oldap')
        model = DataModel.read(connection, 'shared')
        print(model.get_propclasses())
