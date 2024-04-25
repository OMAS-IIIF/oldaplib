import unittest

from omaslib.src.connection import Connection
from omaslib.src.datamodel import DataModel, PropertyClassChange, ResourceClassChange
from omaslib.src.dtypes.languagein import LanguageIn
from omaslib.src.helpers.context import Context
from omaslib.src.enums.action import Action
from omaslib.src.dtypes.namespaceiri import NamespaceIRI
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_boolean import Xsd_boolean
from omaslib.src.xsd.xsd_decimal import Xsd_decimal
from omaslib.src.xsd.xsd_integer import Xsd_integer
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.helpers.langstring import LangString
from omaslib.src.enums.language import Language
from omaslib.src.enums.propertyclassattr import PropClassAttr
from omaslib.src.enums.resourceclassattr import ResourceClassAttribute
from omaslib.src.enums.xsd_datatypes import XsdDatatypes
from omaslib.src.propertyclass import PropClassAttrContainer, PropertyClass
from omaslib.src.resourceclass import ResourceClass


class TestDataModel(unittest.TestCase):
    _context: Context
    _connection: Connection

    @classmethod
    def setUp(cls):
        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://omas.org/test#")
        cls._context['dmtest'] = NamespaceIRI('http://omas.org/dmtest#')

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        cls._connection.clear_graph(Xsd_QName('dmtest:shacl'))
        cls._connection.clear_graph(Xsd_QName('dmtest:onto'))

    def tearDown(self):
        pass

    def generate_a_datamodel(self, dm_name: Xsd_NCName) -> DataModel:
        #
        # define an external standalone property
        #
        comment = PropertyClass(con=self._connection,
                                graph=dm_name,
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
                              graph=dm_name,
                              property_class_iri=Iri(f'{dm_name}:title'),
                              datatype=XsdDatatypes.langString,
                              name=LangString(["Title@en", "Titel@de"]),
                              description=LangString(["Title of book@en", "Titel des Buches@de"]),
                              minCount=Xsd_integer(1),
                              uniqueLang=Xsd_boolean(True),
                              languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                              order=Xsd_decimal(1))

        authors = PropertyClass(con=self._connection,
                                graph=dm_name,
                                property_class_iri=Iri(f'{dm_name}:authors'),
                                toNodeIri=Iri('omas:Person'),
                                name=LangString(["Author(s)@en", "Autor(en)@de"]),
                                description=LangString(["Writers of the Book@en", "Schreiber*innen des Buchs@de"]),
                                minCount=Xsd_integer(1),
                                order=Xsd_decimal(2))

        book = ResourceClass(con=self._connection,
                             graph=dm_name,
                             owlclass_iri=Iri(f'{dm_name}:Book'),
                             label=LangString(["Book@en", "Buch@de"]),
                             comment=LangString("Ein Buch mit Seiten@en"),
                             closed=Xsd_boolean(True),
                             properties=[title, authors, comment])

        pagenum = PropertyClass(con=self._connection,
                                graph=dm_name,
                                property_class_iri=Iri(f'{dm_name}:pagenum'),
                                datatype=XsdDatatypes.int,
                                name=LangString(["Pagenumber@en", "Seitennummer@de"]),
                                maxCount=Xsd_integer(1),
                                minCount=Xsd_integer(1),
                                order=Xsd_decimal(1))

        inbook = PropertyClass(con=self._connection,
                               graph=dm_name,
                               property_class_iri=Iri(f'{dm_name}:inbook'),
                               toNodeIri=Iri(f'{dm_name}:Book'),
                               name=LangString(["Pagenumber@en", "Seitennummer@de"]),
                               maxCount=Xsd_integer(1),
                               minCount=Xsd_integer(1),
                               order=Xsd_decimal(1))

        page = ResourceClass(con=self._connection,
                             graph=dm_name,
                             owlclass_iri=Iri(f'{dm_name}:Page'),
                             label=LangString(["Page@en", "Seite@de"]),
                             comment=LangString("Page of a book@en"),
                             closed=Xsd_boolean(True),
                             properties=[pagenum, inbook, comment])

        dm = DataModel(con=self._connection,
                       graph=dm_name,
                       propclasses=[comment],
                       resclasses=[book, page])
        return dm

    # @unittest.skip('Work in progress')
    def test_datamodel_constructor(self):
        dm_name = Xsd_NCName("dmtest")

        dm = self.generate_a_datamodel(dm_name)
        dm.create()

        del dm

        dm2 = DataModel.read(con=self._connection, graph=dm_name)
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
        self.assertEqual(r1p2.toNodeIri, Iri('omas:Person'))
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
        model = DataModel.read(self._connection, "omas")
        self.assertTrue(set(model.get_propclasses()) == {
            Iri("omas:test"),
            Iri("dcterms:creator"),
            Iri("rdfs:label"),
            Iri("rdfs:comment"),
            Iri("dcterms:created"),
            Iri("dcterms:contributor"),
            Iri("dcterms:modified")
        })
        self.assertTrue(set(model.get_resclasses()) == {
            Iri("omas:Project"),
            Iri("omas:User"),
            Iri("omas:List"),
            Iri("omas:ListNode"),
            Iri("omas:AdminPermission"),
            Iri("omas:DataPermission"),
            Iri("omas:PermissionSet")
        })

    # @unittest.skip('Work in progress')
    def test_datamodel_modify_A(self):
        dm_name = Xsd_NCName("dmtest")
        dm = self.generate_a_datamodel(dm_name)
        dm.create()
        dm = DataModel.read(self._connection, dm_name)

        #
        # define an external standalone property
        #
        pubyear = PropertyClass(con=self._connection,
                                graph=dm_name,
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
                                 graph=dm_name,
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
        dm_name = Xsd_NCName("dmtest")
        dm = self.generate_a_datamodel(dm_name)
        dm.create()
        del dm

        dm_name = Xsd_NCName("dmtest")
        dm = DataModel.read(self._connection, dm_name)

        #
        # define an external standalone property
        #
        pubyear = PropertyClass(con=self._connection,
                                graph=dm_name,
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
                                 graph=dm_name,
                                 property_class_iri=Xsd_QName(f'{dm_name}:pageName'),
                                 datatype=XsdDatatypes.string,
                                 name=LangString(["Page name@en", "Seitenbezeichnung@de"]),
                                 maxCount=Xsd_integer(1),
                                 minCount=Xsd_integer(1))

        dm[Iri(f'{dm_name}:Page')][Iri(f'{dm_name}:pageName')] = pagename

        dm.update()

        del dm

        dm = DataModel.read(self._connection, dm_name)
        self.assertIsNotNone(dm.get(Iri(f'{dm_name}:pubYear')))
        self.assertEqual(dm[Iri(f'{dm_name}:pubYear')].datatype, XsdDatatypes.gYear)
        self.assertEqual(dm[Iri(f'{dm_name}:pubYear')].maxCount, 1)
        self.assertEqual(dm[Iri(f'{dm_name}:comment')].name[Language.FR], 'Commentaire')
        self.assertEqual(dm[Iri(f'{dm_name}:Book')][Iri(f'{dm_name}:authors')].name[Language.FR], "Ecrivain(s)")
        self.assertIsNotNone(dm[Iri(f'{dm_name}:Page')][Iri(f'{dm_name}:pageName')])
        self.assertIsNone(dm[Iri(f'{dm_name}:Page')].get(Iri(f'{dm_name}:comment')))


