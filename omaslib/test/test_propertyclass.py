import unittest
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.dtypes.languagein import LanguageIn
from omaslib.src.dtypes.namespaceiri import NamespaceIRI
from omaslib.src.dtypes.rdfset import RdfSet
from omaslib.src.dtypes.xsdset import XsdSet
from omaslib.src.enums.action import Action
from omaslib.src.enums.language import Language
from omaslib.src.enums.propertyclassattr import PropClassAttr
from omaslib.src.enums.xsd_datatypes import XsdDatatypes
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.omaserror import OmasErrorAlreadyExists, OmasErrorValue
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.propertyclass import PropClassAttrContainer, PropertyClass, OwlPropertyType, \
    PropClassAttrChange
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_boolean import Xsd_boolean
from omaslib.src.xsd.xsd_datetime import Xsd_dateTime
from omaslib.src.xsd.xsd_decimal import Xsd_decimal
from omaslib.src.xsd.xsd_int import Xsd_int
from omaslib.src.xsd.xsd_integer import Xsd_integer
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_string import Xsd_string


class TestPropertyClass(unittest.TestCase):
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
        p = PropertyClass(con=self._connection,
                          graph=Xsd_NCName('test'),
                          property_class_iri=Iri('test:testprop'),
                          subPropertyOf=Iri('test:comment'),
                          datatype=XsdDatatypes.string,
                          name=LangString(["Test property@en", "Testprädikat@de"]),
                          description=LangString("A property for testing...@"),
                          maxCount=1,
                          order=Xsd_decimal(5))
        self.assertEqual(p.property_class_iri, Iri('test:testprop'))
        self.assertEqual(p.get(PropClassAttr.SUBPROPERTY_OF), Iri('test:comment'))
        self.assertEqual(p.get(PropClassAttr.DATATYPE), XsdDatatypes.string)
        self.assertEqual(p.get(PropClassAttr.NAME), LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(p.get(PropClassAttr.ORDER), Xsd_decimal(5))

        p2 = PropertyClass(con=self._connection,
                           graph=Xsd_NCName('test'),
                           toNodeIri=Iri('test:Person'),
                           maxCount=1)
        self.assertEqual(p2.get(PropClassAttr.TO_NODE_IRI), Xsd_QName('test:Person'))
        self.assertEqual(p2.get(PropClassAttr.MAX_COUNT), Xsd_integer(1))

        p3 = PropertyClass(con=self._connection,
                           graph=Xsd_NCName('test'),
                           property_class_iri=Iri('test:testprop3'),
                           datatype=XsdDatatypes.string,
                           inSet=RdfSet(Xsd_string('yes'), Xsd_string('may be'), Xsd_string('no')))
        self.assertEqual(p3.property_class_iri, Xsd_QName('test:testprop3'))
        self.assertEqual(p3.get(PropClassAttr.IN), {Xsd_string('yes'), Xsd_string('may be'), Xsd_string('no')})
        self.assertEqual(p3.get(PropClassAttr.DATATYPE), XsdDatatypes.string)

        p4 = PropertyClass(con=self._connection,
                           graph=Xsd_NCName('test'),
                           property_class_iri=Iri('test:testprop4'),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR))
        self.assertEqual(p4.property_class_iri, Xsd_QName('test:testprop4'))
        self.assertEqual(p4.get(PropClassAttr.LANGUAGE_IN), LanguageIn(Language.EN, Language.DE, Language.FR))
        self.assertEqual(p4.get(PropClassAttr.DATATYPE), XsdDatatypes.langString)

        with self.assertRaises(OmasErrorValue):
            p5 = PropertyClass(con=self._connection,
                               graph=Xsd_NCName('test'),
                               property_class_iri=Iri('test:testprop5'),
                               datatype=XsdDatatypes.string,
                               languageIn=LanguageIn(Language.EN, Language.DE, Language.FR))

    # @unittest.skip('Work in progress')
    def test_propertyclass_read_shacl(self):
        p1 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:comment'))
        self.assertEqual(p1.property_class_iri, Iri('test:comment'))
        self.assertEqual(p1.get(PropClassAttr.DATATYPE), XsdDatatypes.langString)
        self.assertEqual(p1.datatype, XsdDatatypes.langString)
        self.assertTrue(p1.get(PropClassAttr.UNIQUE_LANG))
        self.assertTrue(p1.uniqueLang)
        self.assertEqual(p1.get(PropClassAttr.MAX_COUNT), Xsd_integer(1))
        self.assertEqual(p1.maxCount, Xsd_integer(1))
        self.assertEqual(p1.get(PropClassAttr.NAME), LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(p1.name, LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(p1.get(PropClassAttr.DESCRIPTION), LangString("This is a test property@de"))
        self.assertEqual(p1.description, LangString("This is a test property@de"))
        self.assertIsNone(p1.get(PropClassAttr.SUBPROPERTY_OF))
        self.assertIsNone(p1.subPropertyOf)
        self.assertEqual(p1[PropClassAttr.ORDER], Xsd_decimal(2))
        self.assertEqual(p1.order, Xsd_decimal(2))
        self.assertEqual(p1.get(PropClassAttr.PROPERTY_TYPE), OwlPropertyType.OwlDataProperty)
        self.assertEqual(p1.propertyType, OwlPropertyType.OwlDataProperty)
        self.assertEqual(p1.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(p1.created, Xsd_dateTime("2023-11-04T12:00:00Z"))

        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:test'))
        self.assertEqual(p2.property_class_iri, Iri('test:test'))
        self.assertEqual(p2[PropClassAttr.MIN_COUNT], Xsd_integer(1))
        self.assertEqual(p2[PropClassAttr.NAME], LangString("Test"))
        self.assertEqual(p2[PropClassAttr.DESCRIPTION], LangString("Property shape for testing purposes"))
        self.assertEqual(p2[PropClassAttr.TO_NODE_IRI], Iri('test:comment'))
        self.assertEqual(p2[PropClassAttr.ORDER], Xsd_decimal(3))
        self.assertEqual(p2[PropClassAttr.PROPERTY_TYPE], OwlPropertyType.OwlObjectProperty)

        p3 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:enum'))
        self.assertEqual(p3[PropClassAttr.IN],
                         {"very good", "good", "fair", "insufficient"})
        self.assertEqual(p3[PropClassAttr.IN],
                         RdfSet({Xsd_string("very good"), Xsd_string("good"), Xsd_string("fair"), Xsd_string("insufficient")}))

    # @unittest.skip('Work in progress')
    def test_propertyclass_create(self):
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testWrite'),
            toNodeIri=Iri('test:comment'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            inSet=RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2")),
            order=Xsd_decimal(11)
        )
        p1.create()
        p1 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:testWrite'))
        self.assertEqual(p1.property_class_iri, Iri('test:testWrite'))
        self.assertEqual(p1[PropClassAttr.TO_NODE_IRI], Iri('test:comment'))
        self.assertEqual(p1[PropClassAttr.NAME], LangString("Annotations@en"))
        self.assertEqual(p1[PropClassAttr.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p1[PropClassAttr.IN],
                         RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2")))
        self.assertEqual(p1[PropClassAttr.ORDER], Xsd_decimal(11))

        p2 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testWrite2'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
            uniqueLang=Xsd_boolean(True),
            order=Xsd_decimal(11)
        )
        p2.create()
        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:testWrite2'))
        self.assertEqual(p2.property_class_iri, Iri('test:testWrite2'))
        self.assertEqual(p2[PropClassAttr.DATATYPE], XsdDatatypes.langString)
        self.assertEqual(p2[PropClassAttr.NAME], LangString("Annotations@en"))
        self.assertEqual(p2[PropClassAttr.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropClassAttr.LANGUAGE_IN],
                         LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertEqual(p2[PropClassAttr.ORDER], Xsd_decimal(11))

        pX = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testWrite'),
            datatype=XsdDatatypes.int
        )
        with self.assertRaises(OmasErrorAlreadyExists) as ex:
            pX.create()
        self.assertEqual(str(ex.exception), 'Property "test:testWrite" already exists.')

    # @unittest.skip('Work in progress')
    def test_propertyclass_undo(self):
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testUndo'),
            datatype=XsdDatatypes.langString,
            name=LangString(["Annotations@en", "Annotationen@de"]),
            languageIn=LanguageIn(Language.EN, Language.DE),
            uniqueLang=Xsd_boolean(True),
            pattern=Xsd_string('*.'),
            inSet=RdfSet(Iri("http://www.test.org/comment1"),
                         Iri("http://www.test.org/comment2"),
                         Iri("http://www.test.org/comment3")),

            order=Xsd_decimal(11)
        )
        self.assertEqual(p1.get(PropClassAttr.DATATYPE), XsdDatatypes.langString)
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p1[PropClassAttr.LANGUAGE_IN], LanguageIn(Language.EN, Language.DE))
        self.assertTrue(p1[PropClassAttr.UNIQUE_LANG])
        self.assertEqual(p1[PropClassAttr.PATTERN], '*.')
        self.assertEqual(p1[PropClassAttr.IN],
                         RdfSet(Iri("http://www.test.org/comment1"),
                                Iri("http://www.test.org/comment2"),
                                Iri("http://www.test.org/comment3")))
        self.assertEqual(p1[PropClassAttr.ORDER], Xsd_decimal(11))

        p1[PropClassAttr.NAME][Language.FR] = "Annotations en Français"
        del p1[PropClassAttr.NAME][Language.EN]
        p1[PropClassAttr.DESCRIPTION] = LangString("A description@en")
        p1[PropClassAttr.LANGUAGE_IN] = LanguageIn(Language.EN, Language.DE, Language.FR)
        p1[PropClassAttr.IN] = RdfSet(Iri("http://google.com"), Iri("https://google.com"))
        p1[PropClassAttr.ORDER] = Xsd_decimal(22)

        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotationen@de", "Annotations en Français@fr"]))
        self.assertEqual(p1[PropClassAttr.LANGUAGE_IN], LanguageIn(Language.EN, Language.DE, Language.FR))
        self.assertTrue(p1[PropClassAttr.UNIQUE_LANG])
        self.assertEqual(p1[PropClassAttr.PATTERN], Xsd_string('*.'))
        self.assertEqual(p1[PropClassAttr.IN], RdfSet(Iri("http://google.com"), Iri("https://google.com")))
        self.assertEqual(p1[PropClassAttr.ORDER], Xsd_decimal(22))
        p1.undo()
        self.assertEqual(p1[PropClassAttr.DATATYPE], XsdDatatypes.langString)
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p1[PropClassAttr.LANGUAGE_IN], LanguageIn(Language.EN, Language.DE))
        self.assertTrue(p1[PropClassAttr.UNIQUE_LANG])
        self.assertEqual(p1[PropClassAttr.PATTERN], Xsd_string('*.'))
        self.assertEqual(p1[PropClassAttr.IN], RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2"), Iri("http://www.test.org/comment3")))
        self.assertEqual(p1[PropClassAttr.ORDER], Xsd_decimal(11))

        p1[PropClassAttr.NAME][Language.FR] = "Annotations en Français"
        del p1[PropClassAttr.NAME][Language.EN]
        p1[PropClassAttr.DESCRIPTION] = LangString("A description@en")
        p1[PropClassAttr.LANGUAGE_IN] = LanguageIn(Language.EN, Language.DE, Language.FR)
        p1[PropClassAttr.IN] = RdfSet(Iri("https://gaga.com"), Iri("https://gugus.com"))
        p1[PropClassAttr.ORDER] = Xsd_decimal(22)

        p1.undo(PropClassAttr.NAME)
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        p1.undo(PropClassAttr.DESCRIPTION)
        self.assertIsNone(p1.get(PropClassAttr.DESCRIPTION))
        p1.undo(PropClassAttr.LANGUAGE_IN)
        self.assertEqual(p1[PropClassAttr.LANGUAGE_IN], LanguageIn(Language.EN, Language.DE))
        p1.undo(PropClassAttr.IN)
        self.assertEqual(p1[PropClassAttr.IN], RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2"), Iri("http://www.test.org/comment3")))
        p1.undo(PropClassAttr.ORDER)
        self.assertEqual(p1[PropClassAttr.ORDER], Xsd_decimal(11))
        self.assertEqual(p1.changeset, {})

        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testUndo'),
            toNodeIri=Iri('test:testUndo42'),
            minCount=Xsd_integer(1),
            maxCount=Xsd_integer(1),
            order=Xsd_decimal(11)
        )
        p1.toNodeIri = Iri('test:UP4014')
        del p1.minCount
        p1.maxCount = Xsd_integer(7)
        p1.order = Xsd_decimal(7)
        self.assertEqual(p1.toNodeIri, Iri('test:UP4014'))
        self.assertIsNone(p1.minCount)
        self.assertEqual(p1.maxCount, Xsd_integer(7))
        self.assertEqual(p1.order, Xsd_decimal(7))
        p1.undo()
        self.assertEqual(p1.toNodeIri, Iri('test:testUndo42'))
        self.assertEqual(p1.minCount, Xsd_integer(1))
        self.assertEqual(p1.maxCount, Xsd_integer(1))
        self.assertEqual(p1.order, Xsd_decimal(11))


    # @unittest.skip('Work in progress')
    def test_propertyclass_update(self):
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testUpdate'),
            subPropertyOf=Iri('test:masterProp'),
            datatype=XsdDatatypes.langString,
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
            uniqueLang=Xsd_boolean(True),
            maxCount=Xsd_integer(1),
            minCount=Xsd_integer(10),
            order=Xsd_decimal(11)
        )
        p1.create()

        p1[PropClassAttr.SUBPROPERTY_OF] = Iri('test:masterProp2')
        p1[PropClassAttr.ORDER] = Xsd_decimal(12)
        p1[PropClassAttr.NAME][Language.DE] = 'Annotationen'
        p1[PropClassAttr.UNIQUE_LANG] = Xsd_boolean(False)
        p1[PropClassAttr.IN] = RdfSet(Xsd_string("gaga"), Xsd_string("is was"))
        p1.order = Xsd_decimal(22)
        p1.minCount = Xsd_integer(1)
        self.maxDiff = None
        self.assertEqual(p1.changeset, {
            PropClassAttr.ORDER: PropClassAttrChange(Xsd_decimal(11), Action.REPLACE, True),
            PropClassAttr.NAME: PropClassAttrChange(None, Action.MODIFY, True),
            # PropClassAttr.LANGUAGE_IN: PropClassAttrChange(LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT), Action.REPLACE, True),
            PropClassAttr.SUBPROPERTY_OF: PropClassAttrChange(Iri('test:masterProp'), Action.REPLACE, True),
            PropClassAttr.UNIQUE_LANG: PropClassAttrChange(Xsd_boolean(True), Action.REPLACE, True),
            PropClassAttr.IN: PropClassAttrChange(None, Action.CREATE, True),
            PropClassAttr.MIN_COUNT: PropClassAttrChange(Xsd_integer(10), Action.REPLACE, True),
        })
        p1.update()
        self.assertEqual(p1.changeset, {})

        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:testUpdate'))
        self.assertEqual(p2.property_class_iri, Iri('test:testUpdate'))
        self.assertEqual(p2.subPropertyOf, Iri('test:masterProp2'))
        self.assertEqual(p2[PropClassAttr.DATATYPE], XsdDatatypes.langString)
        self.assertIsNone(p2.get(PropClassAttr.TO_NODE_IRI))
        self.assertEqual(p2[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p2[PropClassAttr.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropClassAttr.LANGUAGE_IN], LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertEqual(p2[PropClassAttr.IN], RdfSet(Xsd_string("gaga"), Xsd_string("is was")))
        self.assertEqual(p2[PropClassAttr.ORDER], Xsd_decimal(22))
        self.assertFalse(p2[PropClassAttr.UNIQUE_LANG])

    # @unittest.skip('Work in progress')
    def test_propertyclass_update2(self):
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testUpdate2'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            datatype=XsdDatatypes.langString,
            languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
            uniqueLang=Xsd_boolean(True),
            maxCount=Xsd_integer(1),
            minCount=Xsd_integer(0),
            order=Xsd_decimal(11)
        )
        p1.create()
        p1.order = Xsd_decimal(12)
        p1.name[Language.DE] = 'Annotationen'
        p1.languageIn.add(Language.ZU)
        p1.uniqueLang = Xsd_boolean(False)
        p1.inSet = RdfSet(Xsd_string("gaga"), Xsd_string("is was"))
        self.maxDiff = None
        self.assertEqual(p1.changeset, {
            PropClassAttr.ORDER: PropClassAttrChange(Xsd_decimal(11), Action.REPLACE, True),
            PropClassAttr.NAME: PropClassAttrChange(None, Action.MODIFY, True),
            PropClassAttr.LANGUAGE_IN: PropClassAttrChange(LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT), Action.REPLACE, True),
            PropClassAttr.UNIQUE_LANG: PropClassAttrChange(Xsd_boolean(True), Action.REPLACE, True),
            PropClassAttr.IN: PropClassAttrChange(None, Action.CREATE, True),
        })
        p1.update()
        self.assertEqual(p1.changeset, {})

        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:testUpdate2'))
        self.assertEqual(p2.property_class_iri, Iri('test:testUpdate2'))
        self.assertEqual(p2.datatype, XsdDatatypes.langString)
        self.assertIsNone(p2.toNodeIri)
        self.assertEqual(p2.name, LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p2.description, LangString("An annotation@en"))
        self.assertEqual(p2.languageIn,
                         LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT, Language.ZU))
        self.assertEqual(p2.inSet, RdfSet(Xsd_string("gaga"), Xsd_string("is was")))
        self.assertEqual(p2.order, Xsd_decimal(12))
        self.assertFalse(p2.uniqueLang)

    # @unittest.skip('Work in progress')
    def test_propertyclass_delete_attrs(self):
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testDelete'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            description=LangString("An annotation@en"),
            languageIn=LanguageIn(Language.ZU, Language.CY, Language.SV, Language.RM),
            uniqueLang=Xsd_boolean(True),
            maxCount=Xsd_integer(1),
            minCount=Xsd_integer(0),
            inSet=RdfSet(Xsd_string('A'), Xsd_string('B'), Xsd_string('C')),
            order=Xsd_decimal(11)
        )
        p1.create()
        del p1[PropClassAttr.NAME]
        del p1[PropClassAttr.MAX_COUNT]
        del p1[PropClassAttr.UNIQUE_LANG]
        del p1[PropClassAttr.LANGUAGE_IN]
        del p1[PropClassAttr.IN]
        p1.update()

        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:testDelete'))
        self.assertIsNone(p2.name)
        self.assertIsNone(p2.maxCount)
        self.assertIsNone(p2.uniqueLang)
        self.assertIsNone(p2.languageIn)
        self.assertIsNone(p2.inSet)
        cstr = self._context.sparql_context
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "zu" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "cy" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "sv" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "rm" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "A" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)

    # @unittest.skip('Work in progress')
    def test_propertyclass_delete(self):
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testDeleteIt'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            description=LangString("An annotation@en"),
            languageIn=LanguageIn(Language.ZU, Language.CY, Language.SV, Language.RM),
            uniqueLang=Xsd_boolean(True),
            maxCount=Xsd_integer(1),
            minCount=Xsd_integer(0),
            order=Xsd_decimal(11)
        )
        p1.create()

        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:testDeleteIt'))
        p2.delete()
        sparql = self._context.sparql_context
        sparql += 'SELECT ?p ?o WHERE { test:testDeleteIt ?p ?o }'
        jsonres = self._connection.query(sparql)
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)

        cstr = self._context.sparql_context
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "zu" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "cy" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "sv" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "rm" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)

        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testDeleteIt2'),
            toNodeIri=Iri('test:comment'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            description=LangString("An annotation@en"),
            inSet=XsdSet(Iri('test:gaga1'), Iri('test:gaga2'), Iri('test:gaga3')),
            maxCount=Xsd_integer(1),
            minCount=Xsd_integer(0),
            order=Xsd_decimal(11)
        )
        p1.create()

        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:testDeleteIt2'))
        p2.delete()
        sparql = self._context.sparql_context
        sparql += 'SELECT ?p ?o WHERE { test:testDeleteIt2 ?p ?o }'
        jsonres = self._connection.query(sparql)
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        cstr = self._context.sparql_context
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p test:gaga1 . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p test:gaga2 . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p test:gaga3 . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "rm" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)

    # @unittest.skip('Work in progress')
    def test_write_trig(self):
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testWriteIt'),
            toNodeIri=Iri('test:comment'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            description=LangString("An annotation@en"),
            maxCount=Xsd_integer(1),
            minCount=Xsd_integer(0),
        )
        p1.write_as_trig('propclass_test.trig')


if __name__ == '__main__':
    unittest.main()
