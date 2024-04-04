import unittest

from omaslib.src.connection import Connection
from omaslib.src.datamodel import DataModel, PropertyClassChange, ResourceClassChange
from omaslib.src.helpers.context import Context
from omaslib.src.enums.action import Action
from omaslib.src.dtypes.namespaceiri import NamespaceIRI
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.helpers.langstring import LangString
from omaslib.src.enums.language import Language
from omaslib.src.enums.propertyclassattr import PropClassAttr
from omaslib.src.enums.resourceclassattr import ResourceClassAttribute
from omaslib.src.enums.xsd_datatypes import XsdDatatypes
from omaslib.src.propertyclass import PropClassAttrContainer, PropertyClass
from omaslib.src.propertyrestrictions import PropertyRestrictions
from omaslib.src.enums.propertyrestrictiontype import PropertyRestrictionType
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
        attrs: PropClassAttrContainer = {
            PropClassAttr.DATATYPE: XsdDatatypes.string,
            PropClassAttr.NAME: LangString(["Comment@en", "Kommentar@de"]),
            PropClassAttr.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
        }
        comment = PropertyClass(con=self._connection,
                                graph=dm_name,
                                property_class_iri=Xsd_QName(f'{dm_name}:comment'),
                                attrs=attrs)
        comment.force_external()

        #
        # Define the properties for the "Book"
        #
        attrs: PropClassAttrContainer = {
            PropClassAttr.DATATYPE: XsdDatatypes.string,
            PropClassAttr.NAME: LangString(["Title@en", "Titel@de"]),
            PropClassAttr.DESCRIPTION: LangString(["Title of book@en", "Titel des Buches@de"]),
            PropClassAttr.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropClassAttr.ORDER: 1
        }
        title = PropertyClass(con=self._connection,
                              graph=dm_name,
                              property_class_iri=Xsd_QName(f'{dm_name}:title'),
                              attrs=attrs)

        attrs: PropClassAttrContainer = {
            PropClassAttr.TO_NODE_IRI: Xsd_QName('omas:Person'),
            PropClassAttr.NAME: LangString(["Author(s)@en", "Autor(en)@de"]),
            PropClassAttr.DESCRIPTION: LangString(["Writers of the Book@en", "Schreiber des Buchs@de"]),
            PropClassAttr.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MIN_COUNT: 1,
                }),
            PropClassAttr.ORDER: 2
        }
        authors = PropertyClass(con=self._connection,
                                graph=dm_name,
                                property_class_iri=Xsd_QName(f'{dm_name}:authors'),
                                attrs=attrs)

        rattrs = ResourceClassAttributesContainer = {
            ResourceClassAttribute.LABEL: LangString(["Book@en", "Buch@de"]),
            ResourceClassAttribute.COMMENT: LangString("Ein Buch mit Seiten@en"),
            ResourceClassAttribute.CLOSED: True
        }
        book = ResourceClass(con=self._connection,
                             graph=dm_name,
                             owlclass_iri=Xsd_QName(f'{dm_name}:Book'),
                             attrs=rattrs,
                             properties=[title, authors, comment])

        attrs: PropClassAttrContainer = {
            PropClassAttr.DATATYPE: XsdDatatypes.int,
            PropClassAttr.NAME: LangString(["Pagenumber@en", "Seitennummer@de"]),
            PropClassAttr.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropClassAttr.ORDER: 1
        }
        pagenum = PropertyClass(con=self._connection,
                                graph=dm_name,
                                property_class_iri=Xsd_QName(f'{dm_name}:pagenum'),
                                attrs=attrs)

        attrs: PropClassAttrContainer = {
            PropClassAttr.TO_NODE_IRI: Xsd_QName(f'{dm_name}:Book'),
            PropClassAttr.NAME: LangString(["Pagenumber@en", "Seitennummer@de"]),
            PropClassAttr.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.MIN_COUNT: 1,
                }),
            PropClassAttr.ORDER: 1
        }
        inbook = PropertyClass(con=self._connection,
                               graph=dm_name,
                               property_class_iri=Xsd_QName(f'{dm_name}:inbook'),
                               attrs=attrs)

        rattrs = ResourceClassAttributesContainer = {
            ResourceClassAttribute.LABEL: LangString(["Page@en", "Seite@de"]),
            ResourceClassAttribute.COMMENT: LangString("Page of a book@en"),
            ResourceClassAttribute.CLOSED: True
        }

        page = ResourceClass(con=self._connection,
                             graph=dm_name,
                             owlclass_iri=Xsd_QName(f'{dm_name}:Page'),
                             attrs=rattrs,
                             properties=[pagenum, inbook, comment])

        dm = DataModel(con=self._connection,
                       graph=dm_name,
                       propclasses=[comment],
                       resclasses=[book, page])
        return dm

    #@unittest.skip('Work in progress')
    def test_datamodel_constructor(self):
        dm_name = Xsd_NCName("dmtest")

        dm = self.generate_a_datamodel(dm_name)
        dm.create()

        del dm

        dm2 = DataModel.read(con=self._connection, graph=dm_name)
        p1 = dm2[Xsd_QName(f'{dm_name}:comment')]
        self.assertEqual(p1[PropClassAttr.DATATYPE], XsdDatatypes.string)
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Comment@en", "Kommentar@de"]))
        self.assertTrue(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])

        r1 = dm2[Xsd_QName(f'{dm_name}:Book')]
        r1p1 = r1[Xsd_QName(f'{dm_name}:title')]
        self.assertEqual(r1p1.internal, Xsd_QName(f'{dm_name}:Book'))
        self.assertEqual(r1p1[PropClassAttr.DATATYPE], XsdDatatypes.string)
        self.assertEqual(r1p1[PropClassAttr.NAME], LangString(["Title@en", "Titel@de"]))
        self.assertEqual(r1p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.MIN_COUNT], 1)
        r1p2 = r1[Xsd_QName(f'{dm_name}:authors')]
        self.assertEqual(r1p2.internal, Xsd_QName(f'{dm_name}:Book'))
        self.assertEqual(r1p2[PropClassAttr.TO_NODE_IRI], Xsd_QName('omas:Person'))
        self.assertEqual(r1p2[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.MIN_COUNT], 1)
        r1p3 = r1[Xsd_QName(f'{dm_name}:comment')]
        self.assertIsNone(r1p3.internal)
        self.assertEqual(r1p3[PropClassAttr.DATATYPE], XsdDatatypes.string)

        r2 = dm2[Xsd_QName(f'{dm_name}:Page')]
        r2p1 = r2[Xsd_QName(f'{dm_name}:pagenum')]
        self.assertEqual(r2p1.internal, Xsd_QName(f'{dm_name}:Page'))
        self.assertEqual(r2p1[PropClassAttr.DATATYPE], XsdDatatypes.int)
        r2p2 = r2[Xsd_QName(f'{dm_name}:inbook')]
        self.assertEqual(r2p2.internal, Xsd_QName(f'{dm_name}:Page'))
        self.assertEqual(r2p2[PropClassAttr.TO_NODE_IRI], Xsd_QName(f'{dm_name}:Book'))
        r2p3 = r1[Xsd_QName(f'{dm_name}:comment')]
        self.assertIsNone(r2p3.internal)
        self.assertEqual(r2p3[PropClassAttr.DATATYPE], XsdDatatypes.string)

    #@unittest.skip('Work in progress')
    def test_datamodel_read(self):
        model = DataModel.read(self._connection, "omas")
        self.assertTrue(set(model.get_propclasses()) == {
            #QName("omas:comment"),
            Xsd_QName("omas:test"),
            Xsd_QName("dcterms:creator"),
            Xsd_QName("rdfs:label"),
            Xsd_QName("rdfs:comment"),
            Xsd_QName("dcterms:created"),
            Xsd_QName("dcterms:contributor"),
            Xsd_QName("dcterms:modified")
        })
        self.assertTrue(set(model.get_resclasses()) == {
            Xsd_QName("omas:Project"),
            Xsd_QName("omas:User"),
            Xsd_QName("omas:List"),
            Xsd_QName("omas:ListNode"),
            Xsd_QName("omas:AdminPermission"),
            Xsd_QName("omas:DataPermission"),
            Xsd_QName("omas:PermissionSet")
        })

    #@unittest.skip('Work in progress')
    def test_datamodel_modify_A(self):
        dm_name = Xsd_NCName("dmtest")
        dm = self.generate_a_datamodel(dm_name)
        dm.create()
        dm_name = Xsd_NCName("dmtest")
        dm = DataModel.read(self._connection, dm_name)

        #
        # define an external standalone property
        #
        attrs: PropClassAttrContainer = {
            PropClassAttr.DATATYPE: XsdDatatypes.gYear,
            PropClassAttr.NAME: LangString(["Publication Year@en", "Publikationsjahr@de"]),
            PropClassAttr.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1
                }),
        }
        pubyear = PropertyClass(con=self._connection,
                                graph=dm_name,
                                property_class_iri=Xsd_QName(f'{dm_name}:pubYear'),
                                attrs=attrs)
        pubyear.force_external()
        dm[Xsd_QName(f'{dm_name}:pubYear')] = pubyear
        self.assertEqual({Xsd_QName(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE)}, dm.changeset)

        dm[Xsd_QName(f'{dm_name}:comment')][PropClassAttr.NAME][Language.FR] = 'Commentaire'
        self.assertEqual({
            Xsd_QName(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE),
            Xsd_QName(f'{dm_name}:comment'): PropertyClassChange(None, Action.MODIFY)
        }, dm.changeset)

        dm[Xsd_QName(f'{dm_name}:Book')][Xsd_QName(f'{dm_name}:authors')][PropClassAttr.NAME][Language.FR] = "Ecrivain(s)"
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

        attrs: PropClassAttrContainer = {
            PropClassAttr.DATATYPE: XsdDatatypes.string,
            PropClassAttr.NAME: LangString(["Page name@en", "Seitenbezeichnung@de"]),
            PropClassAttr.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.MIN_COUNT: 1,
                }),
        }
        pagename = PropertyClass(con=self._connection,
                                 graph=dm_name,
                                 property_class_iri=Xsd_QName(f'{dm_name}:pageName'),
                                 attrs=attrs)

        dm[Xsd_QName(f'{dm_name}:Page')][Xsd_QName(f'{dm_name}:pageName')] = pagename
        self.assertEqual({
            Xsd_QName(f'{dm_name}:pubYear'): PropertyClassChange(None, Action.CREATE),
            Xsd_QName(f'{dm_name}:comment'): PropertyClassChange(None, Action.MODIFY),
            Xsd_QName(f'{dm_name}:Book'): ResourceClassChange(None, Action.MODIFY),
            Xsd_QName(f'{dm_name}:Page'): ResourceClassChange(None, Action.MODIFY)
        }, dm.changeset)

    #@unittest.skip('Work in progress')
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
        attrs: PropClassAttrContainer = {
            PropClassAttr.DATATYPE: XsdDatatypes.gYear,
            PropClassAttr.NAME: LangString(["Publication Year@en", "Publikationsjahr@de"]),
            PropClassAttr.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1
                }),
        }
        pubyear = PropertyClass(con=self._connection,
                                graph=dm_name,
                                property_class_iri=Xsd_QName(f'{dm_name}:pubYear'),
                                attrs=attrs)
        pubyear.force_external()

        dm[Xsd_QName(f'{dm_name}:pubYear')] = pubyear
        dm[Xsd_QName(f'{dm_name}:comment')][PropClassAttr.NAME][Language.FR] = 'Commentaire'
        dm[Xsd_QName(f'{dm_name}:Book')][Xsd_QName(f'{dm_name}:authors')][PropClassAttr.NAME][Language.FR] = "Ecrivain(s)"
        del dm[Xsd_QName(f'{dm_name}:Page')][Xsd_QName(f'{dm_name}:comment')]

        attrs: PropClassAttrContainer = {
            PropClassAttr.DATATYPE: XsdDatatypes.string,
            PropClassAttr.NAME: LangString(["Page name@en", "Seitenbezeichnung@de"]),
            PropClassAttr.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.MIN_COUNT: 1,
                }),
        }
        pagename = PropertyClass(con=self._connection,
                                 graph=dm_name,
                                 property_class_iri=Xsd_QName(f'{dm_name}:pageName'),
                                 attrs=attrs)

        dm[Xsd_QName(f'{dm_name}:Page')][Xsd_QName(f'{dm_name}:pageName')] = pagename

        dm.update()

        del dm

        dm = DataModel.read(self._connection, dm_name)
        self.assertIsNotNone(dm.get(Xsd_QName(f'{dm_name}:pubYear')))
        self.assertEqual(dm[Xsd_QName(f'{dm_name}:pubYear')][PropClassAttr.DATATYPE], XsdDatatypes.gYear)
        self.assertEqual(dm[Xsd_QName(f'{dm_name}:pubYear')][PropClassAttr.RESTRICTIONS][PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(dm[Xsd_QName(f'{dm_name}:comment')][PropClassAttr.NAME][Language.FR], 'Commentaire')
        self.assertEqual(dm[Xsd_QName(f'{dm_name}:Book')][Xsd_QName(f'{dm_name}:authors')][PropClassAttr.NAME][Language.FR], "Ecrivain(s)")
        self.assertIsNotNone(dm[Xsd_QName(f'{dm_name}:Page')][Xsd_QName(f'{dm_name}:pageName')])
        self.assertIsNone(dm[Xsd_QName(f'{dm_name}:Page')].get(Xsd_QName(f'{dm_name}:comment')))


