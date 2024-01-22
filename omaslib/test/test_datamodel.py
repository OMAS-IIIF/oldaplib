import unittest
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.datamodel import DataModel
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName, NCName
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.propertyclassattr import PropertyClassAttribute
from omaslib.src.helpers.resourceclassattr import ResourceClassAttribute
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.propertyclass import PropertyClassAttributesContainer, PropertyClass
from omaslib.src.propertyrestrictions import PropertyRestrictions, PropertyRestrictionType
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
                                     userid="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        cls._connection.clear_graph(QName('test:shacl'))
        cls._connection.clear_graph(QName('test:onto'))
        cls._connection.clear_graph(QName('dmtest:shacl'))
        cls._connection.clear_graph(QName('dmtest:onto'))
        cls._connection.upload_turtle("omaslib/testdata/connection_test.trig")
        sleep(1)  # upload may take a while...

    def tearDown(self):
        pass

    #@unittest.skip('Work in progress')
    def test_datamodel_constructor(self):
        props = {}

        dm_name = NCName("dmtest")

        #
        # define an external standalone property
        #
        attrs: PropertyClassAttributesContainer = {
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.NAME: LangString(["Comment@en", "Kommentar@de"]),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
        }
        comment = PropertyClass(con=self._connection,
                                graph=dm_name,
                                property_class_iri=QName('dmtest:comment'),
                                attrs=attrs)
        comment.force_external()

        #
        # Define the properties for the "Book"
        #
        attrs: PropertyClassAttributesContainer = {
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.NAME: LangString(["Title@en", "Titel@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString(["Title of book@en", "Titel des Buches@de"]),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 1
        }
        title = PropertyClass(con=self._connection,
                              graph=dm_name,
                              property_class_iri=QName('dmtest:title'),
                              attrs=attrs)

        attrs: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: QName('omas:Person'),
            PropertyClassAttribute.NAME: LangString(["Author(s)@en", "Autor(en)@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString(["Writers of the Book@en", "Schreiber des Buchs@de"]),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MIN_COUNT: 1,
                }),
            PropertyClassAttribute.ORDER: 2
        }
        authors = PropertyClass(con=self._connection,
                                graph=dm_name,
                                property_class_iri=QName('dmtest:authors'),
                                attrs=attrs)

        rattrs = ResourceClassAttributesContainer = {
            ResourceClassAttribute.LABEL: LangString(["Book@en", "Buch@de"]),
            ResourceClassAttribute.COMMENT: LangString("Ein Buch mit Seiten@en"),
            ResourceClassAttribute.CLOSED: True
        }
        book = ResourceClass(con=self._connection,
                             graph=dm_name,
                             owlclass_iri=QName('dmtest:Book'),
                             attrs=rattrs,
                             properties=[title, authors, comment])

        attrs: PropertyClassAttributesContainer = {
            PropertyClassAttribute.DATATYPE: XsdDatatypes.int,
            PropertyClassAttribute.NAME: LangString(["Pagenumber@en", "Seitennummer@de"]),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 1
        }
        pagenum = PropertyClass(con=self._connection,
                                graph=dm_name,
                                property_class_iri=QName('dmtest:pagenum'),
                                attrs=attrs)

        attrs: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: QName('dmtest:Book'),
            PropertyClassAttribute.NAME: LangString(["Pagenumber@en", "Seitennummer@de"]),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.MIN_COUNT: 1,
                }),
            PropertyClassAttribute.ORDER: 1
        }
        inbook = PropertyClass(con=self._connection,
                               graph=dm_name,
                               property_class_iri=QName('dmtest:inbook'),
                               attrs=attrs)

        rattrs = ResourceClassAttributesContainer = {
            ResourceClassAttribute.LABEL: LangString(["Page@en", "Seite@de"]),
            ResourceClassAttribute.COMMENT: LangString("Page of a book@en"),
            ResourceClassAttribute.CLOSED: True
        }

        page = ResourceClass(con=self._connection,
                             graph=dm_name,
                             owlclass_iri=QName('dmtest:Page'),
                             attrs=rattrs,
                             properties=[pagenum, inbook, comment])

        dm = DataModel(con=self._connection,
                       graph=dm_name,
                       propclasses=[comment],
                       resclasses=[book, page])
        dm.create()

        del dm

        dm2 = DataModel.read(con=self._connection, graph=dm_name)
        p1 = dm2[QName('dmtest:comment')]
        self.assertEqual(p1[PropertyClassAttribute.DATATYPE], XsdDatatypes.string)
        self.assertEqual(p1[PropertyClassAttribute.NAME], LangString(["Comment@en", "Kommentar@de"]))
        self.assertTrue(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])

        r1 = dm2[QName('dmtest:Book')]
        r1p1 = r1[QName('dmtest:title')]
        self.assertEqual(r1p1.internal, QName('dmtest:Book'))
        self.assertEqual(r1p1[PropertyClassAttribute.DATATYPE], XsdDatatypes.string)
        self.assertEqual(r1p1[PropertyClassAttribute.NAME], LangString(["Title@en", "Titel@de"]))
        self.assertEqual(r1p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MIN_COUNT], 1)
        r1p2 = r1[QName('dmtest:authors')]
        self.assertEqual(r1p2.internal, QName('dmtest:Book'))
        self.assertEqual(r1p2[PropertyClassAttribute.TO_NODE_IRI], QName('omas:Person'))
        self.assertEqual(r1p2[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MIN_COUNT], 1)
        r1p3 = r1[QName('dmtest:comment')]
        self.assertIsNone(r1p3.internal)
        self.assertEqual(r1p3[PropertyClassAttribute.DATATYPE], XsdDatatypes.string)

        r2 = dm2[QName('dmtest:Page')]
        r2p1 = r2[QName('dmtest:pagenum')]
        self.assertEqual(r2p1.internal, QName('dmtest:Page'))
        self.assertEqual(r2p1[PropertyClassAttribute.DATATYPE], XsdDatatypes.int)
        r2p2 = r2[QName('dmtest:inbook')]
        self.assertEqual(r2p2.internal, QName('dmtest:Page'))
        self.assertEqual(r2p2[PropertyClassAttribute.TO_NODE_IRI], QName('dmtest:Book'))
        r2p3 = r1[QName('dmtest:comment')]
        self.assertIsNone(r2p3.internal)
        self.assertEqual(r2p3[PropertyClassAttribute.DATATYPE], XsdDatatypes.string)

    #@unittest.skip('Work in progress')
    def test_datamodel_read(self):
        model = DataModel.read(self._connection, "omas")
        self.assertTrue(set(model.get_propclasses()) == {QName("omas:comment"), QName("omas:test")})
        self.assertTrue(set(model.get_resclasses()) == {
            QName("omas:ListNode"), QName("omas:User"), QName("omas:Thing"),
            QName("omas:Project"), QName("omas:Date"), QName("omas:List"), QName("omas:AdminRights")
        })





