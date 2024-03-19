import unittest
from datetime import datetime
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.enums.action import Action
from omaslib.src.dtypes.namespaceiri import NamespaceIRI
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.xsd.xsd_boolean import Xsd_boolean
from omaslib.src.helpers.langstring import LangString
from omaslib.src.enums.language import Language
from omaslib.src.helpers.omaserror import OmasErrorAlreadyExists
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.enums.xsd_datatypes import XsdDatatypes
from omaslib.src.propertyclass import PropertyClass, OwlPropertyType, PropertyClassAttributesContainer, PropertyClassAttributeChange
from omaslib.src.enums.propertyclassattr import PropertyClassAttribute
from omaslib.src.propertyrestrictions import PropertyRestrictions
from omaslib.src.enums.propertyrestrictiontype import PropertyRestrictionType


class TestPropertyClass(unittest.TestCase):
    _context: Context
    _connection: Connection

    @classmethod
    def setUpClass(cls):
        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://omas.org/test#")
        cls._context.use('test')

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        cls._connection.upload_turtle("omaslib/testdata/connection_test.trig")
        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(QName('test:shacl'))
        #cls._connection.clear_graph(QName('test:onto'))
        pass

    def test_propertyclass_constructor(self):
        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.SUBPROPERTY_OF: Xsd_QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.NAME: LangString(["Test property@en", "Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("A property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={PropertyRestrictionType.MAX_COUNT: 1}),
            PropertyClassAttribute.ORDER: 5,
        }
        p = PropertyClass(con=self._connection,
                          graph=Xsd_NCName('test'),
                          property_class_iri=Xsd_QName('test:testprop'),
                          attrs=props)
        self.assertEqual(p.property_class_iri, Xsd_QName('test:testprop'))
        self.assertEqual(p.get(PropertyClassAttribute.SUBPROPERTY_OF), Xsd_QName('test:comment'))
        self.assertEqual(p.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertEqual(p.get(PropertyClassAttribute.NAME), LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(p.get(PropertyClassAttribute.ORDER), 5)

        attrs: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: Xsd_QName('test:Person'),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={PropertyRestrictionType.MAX_COUNT: 1}),
        }
        p2 = PropertyClass(con=self._connection,
                           graph=Xsd_NCName('test'),
                           attrs=attrs)
        self.assertEqual(p2.get(PropertyClassAttribute.TO_NODE_IRI), Xsd_QName('test:Person'))
        self.assertEqual(p2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MAX_COUNT), 1)

        attrs: PropertyClassAttributesContainer = {
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={PropertyRestrictionType.IN: {'yes', 'may be', 'no'}})
        }
        p3 = PropertyClass(con=self._connection,
                           graph=Xsd_NCName('test'),
                           property_class_iri=Xsd_QName('test:testprop3'),
                           attrs=attrs)
        self.assertEqual(p3.property_class_iri, Xsd_QName('test:testprop3'))
        self.assertEqual(p3[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.IN), {'yes', 'may be', 'no'})
        self.assertEqual(p3.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)

    def test_propertyclass_read_shacl(self):
        p1 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Xsd_QName('test:comment'))
        self.assertEqual(p1.property_class_iri, Xsd_QName('test:comment'))
        self.assertEqual(p1.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertTrue(p1.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(p1.get(PropertyClassAttribute.NAME), LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(p1.get(PropertyClassAttribute.DESCRIPTION), LangString("This is a test property@de"))
        self.assertIsNone(p1.get(PropertyClassAttribute.SUBPROPERTY_OF))
        self.assertEqual(p1[PropertyClassAttribute.ORDER], 2)
        self.assertEqual(p1.get(PropertyClassAttribute.PROPERTY_TYPE), OwlPropertyType.OwlDataProperty)
        self.assertEqual(p1.creator, Xsd_anyURI('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(p1.created, datetime.fromisoformat("2023-11-04T12:00:00Z"))

        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Xsd_QName('test:test'))
        self.assertEqual(p2.property_class_iri, Xsd_QName('test:test'))
        self.assertEqual(p2[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(p2[PropertyClassAttribute.NAME], LangString("Test"))
        self.assertEqual(p2[PropertyClassAttribute.DESCRIPTION], LangString("Property shape for testing purposes"))
        self.assertEqual(p2[PropertyClassAttribute.TO_NODE_IRI], Xsd_QName('test:comment'))
        self.assertEqual(p2[PropertyClassAttribute.ORDER], 3)
        self.assertEqual(p2[PropertyClassAttribute.PROPERTY_TYPE], OwlPropertyType.OwlObjectProperty)

        p3 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Xsd_QName('test:enum'))
        self.assertEqual(p3[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.IN],
                         {"very good", "good", "fair", "insufficient"})

    def test_propertyclass_create(self):
        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: Xsd_QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.anyURI,
            PropertyClassAttribute.NAME: LangString("Annotations@en"),
            PropertyClassAttribute.DESCRIPTION: LangString("An annotation@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT},
                PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                PropertyRestrictionType.IN: {"http://www.test.org/comment1", "http://www.test.org/comment2"}
            }),
            PropertyClassAttribute.ORDER: 11
        }
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Xsd_QName('test:testWrite'),
            attrs=props
        )
        p1.create()
        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Xsd_QName('test:testWrite'))
        self.assertEqual(p2.property_class_iri, Xsd_QName('test:testWrite'))
        self.assertEqual(p2[PropertyClassAttribute.TO_NODE_IRI], Xsd_QName('test:comment'))
        self.assertEqual(p2[PropertyClassAttribute.NAME], LangString("Annotations@en"))
        self.assertEqual(p2[PropertyClassAttribute.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE, Language.FR, Language.IT})
        self.assertEqual(p2[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.IN],
                         {"http://www.test.org/comment1", "http://www.test.org/comment2"})

        self.assertEqual(p2[PropertyClassAttribute.ORDER], 11)

        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.DATATYPE: XsdDatatypes.int,
        }
        pX = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Xsd_QName('test:testWrite'),
            attrs=props
        )
        with self.assertRaises(OmasErrorAlreadyExists) as ex:
            pX.create()
        self.assertEqual(str(ex.exception), 'Property "test:testWrite" already exists.')

    def test_propertyclass_undo(self):
        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: Xsd_QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.anyURI,
            PropertyClassAttribute.NAME: LangString(["Annotations@en", "Annotationen@de"]),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE},
                PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                PropertyRestrictionType.PATTERN: '*.',
                PropertyRestrictionType.IN: {"http://www.test.org/comment1", "http://www.test.org/comment2", "http://www.test.org/comment3"}
            }),
            PropertyClassAttribute.ORDER: 11
        }
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Xsd_QName('test:testUndo'),
            attrs=props
        )
        self.assertEqual(p1[PropertyClassAttribute.TO_NODE_IRI], Xsd_QName('test:comment'))
        self.assertEqual(p1[PropertyClassAttribute.DATATYPE], XsdDatatypes.anyURI)
        self.assertEqual(p1[PropertyClassAttribute.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE})
        self.assertTrue(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.PATTERN], '*.')
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.IN],
                         {"http://www.test.org/comment1", "http://www.test.org/comment2", "http://www.test.org/comment3"})

        self.assertEqual(p1[PropertyClassAttribute.ORDER], 11)

        p1[PropertyClassAttribute.TO_NODE_IRI] = Xsd_QName('test:waseliwas')
        p1[PropertyClassAttribute.NAME][Language.FR] = "Annotations en Français"
        del p1[PropertyClassAttribute.NAME][Language.EN]
        p1[PropertyClassAttribute.DESCRIPTION] = LangString("A description@en")
        p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN] = {Language.EN, Language.DE, Language.FR}
        p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.IN] = {"http://google.com", "https//google.com"}
        p1[PropertyClassAttribute.ORDER] = 22

        self.assertEqual(p1[PropertyClassAttribute.TO_NODE_IRI], Xsd_QName('test:waseliwas'))
        self.assertEqual(p1[PropertyClassAttribute.DATATYPE], XsdDatatypes.anyURI)
        self.assertEqual(p1[PropertyClassAttribute.NAME], LangString(["Annotationen@de", "Annotations en Français@fr"]))
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE, Language.FR})
        self.assertTrue(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.PATTERN], '*.')
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.IN],
                         {"http://google.com", "https//google.com"})
        self.assertEqual(p1[PropertyClassAttribute.ORDER], 22)

        p1.undo()
        self.assertEqual(p1[PropertyClassAttribute.TO_NODE_IRI], Xsd_QName('test:comment'))
        self.assertEqual(p1[PropertyClassAttribute.DATATYPE], XsdDatatypes.anyURI)
        self.assertEqual(p1[PropertyClassAttribute.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE})
        self.assertTrue(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.PATTERN], '*.')
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.IN],
                         {"http://www.test.org/comment1", "http://www.test.org/comment2", "http://www.test.org/comment3"})
        self.assertEqual(p1[PropertyClassAttribute.ORDER], 11)

        p1[PropertyClassAttribute.TO_NODE_IRI] = Xsd_QName('test:waseliwas')
        p1[PropertyClassAttribute.NAME][Language.FR] = "Annotations en Français"
        del p1[PropertyClassAttribute.NAME][Language.EN]
        p1[PropertyClassAttribute.DESCRIPTION] = LangString("A description@en")
        p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN] = {Language.EN, Language.DE, Language.FR}
        p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.IN] = {
            "https://gaga.com", "https:/gugus.com"
        }
        p1[PropertyClassAttribute.ORDER] = 22

        p1.undo(PropertyClassAttribute.TO_NODE_IRI)
        self.assertEqual(p1[PropertyClassAttribute.TO_NODE_IRI], Xsd_QName('test:comment'))
        p1.undo(PropertyClassAttribute.NAME)
        self.assertEqual(p1[PropertyClassAttribute.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        p1.undo(PropertyClassAttribute.DESCRIPTION)
        self.assertIsNone(p1.get(PropertyClassAttribute.DESCRIPTION))
        p1.undo(PropertyRestrictionType.LANGUAGE_IN)
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE})
        p1.undo(PropertyRestrictionType.IN)
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.IN],
                         {"http://www.test.org/comment1", "http://www.test.org/comment2", "http://www.test.org/comment3"})
        p1.undo(PropertyClassAttribute.ORDER)
        self.assertEqual(p1[PropertyClassAttribute.ORDER], 11)
        self.assertEqual(p1.changeset, {})

    def test_propertyclass_update(self):
        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: Xsd_QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.anyURI,
            PropertyClassAttribute.NAME: LangString("Annotations@en"),
            PropertyClassAttribute.DESCRIPTION: LangString("An annotation@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT},
                PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                PropertyRestrictionType.MAX_COUNT: 1,
                PropertyRestrictionType.MIN_COUNT: 0
            }),
            PropertyClassAttribute.ORDER: 11
        }
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Xsd_QName('test:testUpdate'),
            attrs=props
        )
        p1.create()
        p1[PropertyClassAttribute.ORDER] = 12
        p1[PropertyClassAttribute.NAME][Language.DE] = 'Annotationen'
        p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG] = Xsd_boolean(False)
        p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.IN] = {"gaga", "is was"}
        p1[PropertyClassAttribute.DATATYPE] = XsdDatatypes.string
        self.assertEqual(p1.changeset, {
            PropertyClassAttribute.ORDER: PropertyClassAttributeChange(11, Action.REPLACE, True),
            PropertyClassAttribute.NAME: PropertyClassAttributeChange(None, Action.MODIFY, True),
            PropertyClassAttribute.RESTRICTIONS: PropertyClassAttributeChange(None, Action.MODIFY, True),
            PropertyClassAttribute.DATATYPE: PropertyClassAttributeChange(XsdDatatypes.anyURI, Action.CREATE, True),
            PropertyClassAttribute.TO_NODE_IRI: PropertyClassAttributeChange(Xsd_QName('test:comment'), Action.DELETE, True)
        })
        p1.update()
        self.assertEqual(p1.changeset, {})

        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Xsd_QName('test:testUpdate'))
        self.assertEqual(p2.property_class_iri, Xsd_QName('test:testUpdate'))
        self.assertEqual(p2[PropertyClassAttribute.DATATYPE], XsdDatatypes.string)
        self.assertIsNone(p2.get(PropertyClassAttribute.TO_NODE_IRI))
        self.assertEqual(p2[PropertyClassAttribute.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p2[PropertyClassAttribute.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE, Language.FR, Language.IT})
        self.assertEqual(p2[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.IN], {"gaga", "is was"})
        self.assertEqual(p2[PropertyClassAttribute.ORDER], 12)
        self.assertFalse(p2[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])

    def test_propertyclass_delete_attrs(self):
        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: Xsd_QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.anyURI,
            PropertyClassAttribute.NAME: LangString(["Annotations@en", "Annotationen@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("An annotation@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: {Language.ZU, Language.CY, Language.SV, Language.RM},
                PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                PropertyRestrictionType.MAX_COUNT: 1,
                PropertyRestrictionType.MIN_COUNT: 0,
                PropertyRestrictionType.IN: {'A', 'B', 'C'}
            }),
            PropertyClassAttribute.ORDER: 11
        }
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Xsd_QName('test:testDelete'),
            attrs=props
        )
        p1.create()
        del p1[PropertyClassAttribute.NAME]
        del p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MAX_COUNT]
        del p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG]
        del p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN]
        del p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.IN]
        p1.update()

        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Xsd_QName('test:testDelete'))
        self.assertEqual(p2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MIN_COUNT), 0)
        self.assertIsNone(p2.get(PropertyClassAttribute.NAME))
        self.assertIsNone(p2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MAX_COUNT))
        self.assertIsNone(p2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.UNIQUE_LANG))
        self.assertIsNone(p2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.LANGUAGE_IN))
        self.assertIsNone(p2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.IN))
        jsonres = self._connection.query('SELECT ?s ?p ?o WHERE { ?s ?p "zu" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query('SELECT ?s ?p ?o WHERE { ?s ?p "cy" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query('SELECT ?s ?p ?o WHERE { ?s ?p "sv" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query('SELECT ?s ?p ?o WHERE { ?s ?p "rm" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query('SELECT ?s ?p ?o WHERE { ?s ?p "A" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)


    def test_propertyclass_delete(self):
        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: Xsd_QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.anyURI,
            PropertyClassAttribute.NAME: LangString(["Annotations@en", "Annotationen@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("An annotation@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: {Language.ZU, Language.CY, Language.SV, Language.RM},
                PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                PropertyRestrictionType.MAX_COUNT: 1,
                PropertyRestrictionType.MIN_COUNT: 0
            }),
            PropertyClassAttribute.ORDER: 11
        }
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Xsd_QName('test:testDeleteIt'),
            attrs=props
        )
        p1.create()

        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Xsd_QName('test:testDeleteIt'))
        p2.delete()
        sparql = self._context.sparql_context
        sparql += 'SELECT ?p ?o WHERE { test:testDeleteIt ?p ?o }'
        jsonres = self._connection.query(sparql)
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query('SELECT ?s ?p ?o WHERE { ?s ?p "zu" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query('SELECT ?s ?p ?o WHERE { ?s ?p "cy" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query('SELECT ?s ?p ?o WHERE { ?s ?p "sv" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query('SELECT ?s ?p ?o WHERE { ?s ?p "rm" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)

    def test_write_trig(self):
        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: Xsd_QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.anyURI,
            PropertyClassAttribute.NAME: LangString(["Annotations@en", "Annotationen@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("An annotation@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: {Language.ZU, Language.CY, Language.SV, Language.RM},
                PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                PropertyRestrictionType.MAX_COUNT: 1,
                PropertyRestrictionType.MIN_COUNT: 0
            }),
            PropertyClassAttribute.ORDER: 11
        }
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Xsd_QName('test:testWriteIt'),
            attrs=props
        )
        p1.write_as_trig('propclass_test.trig')


if __name__ == '__main__':
    unittest.main()
