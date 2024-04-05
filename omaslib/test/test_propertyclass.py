import unittest
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.dtypes.languagein import LanguageIn
from omaslib.src.dtypes.namespaceiri import NamespaceIRI
from omaslib.src.dtypes.rdfset import RdfSet
from omaslib.src.enums.action import Action
from omaslib.src.enums.language import Language
from omaslib.src.enums.propertyclassattr import PropClassAttr
from omaslib.src.enums.propertyrestrictiontype import PropertyRestrictionType
from omaslib.src.enums.xsd_datatypes import XsdDatatypes
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.omaserror import OmasErrorAlreadyExists
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.propertyclass import PropClassAttrContainer, PropertyClass, OwlPropertyType, \
    PropClassAttrChange
from omaslib.src.propertyrestrictions import PropertyRestrictions
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_boolean import Xsd_boolean
from omaslib.src.xsd.xsd_datetime import Xsd_dateTime
from omaslib.src.xsd.xsd_decimal import Xsd_decimal
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
                          restrictions=PropertyRestrictions(
                              restrictions={PropertyRestrictionType.MAX_COUNT: Xsd_integer(1)}
                          ),
                          order=Xsd_decimal(5))
        self.assertEqual(p.property_class_iri, Iri('test:testprop'))
        self.assertEqual(p.get(PropClassAttr.SUBPROPERTY_OF), Iri('test:comment'))
        self.assertEqual(p.get(PropClassAttr.DATATYPE), XsdDatatypes.string)
        self.assertEqual(p.get(PropClassAttr.NAME), LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(p.get(PropClassAttr.ORDER), Xsd_decimal(5))

        p2 = PropertyClass(con=self._connection,
                           graph=Xsd_NCName('test'),
                           toNodeIri=Iri('test:Person'),
                           restrictions=PropertyRestrictions(
                               restrictions={PropertyRestrictionType.MAX_COUNT: Xsd_integer(1)}
                           ))
        self.assertEqual(p2.get(PropClassAttr.TO_NODE_IRI), Xsd_QName('test:Person'))
        self.assertEqual(p2[PropClassAttr.RESTRICTIONS].get(PropertyRestrictionType.MAX_COUNT), Xsd_integer(1))

        p3 = PropertyClass(con=self._connection,
                           graph=Xsd_NCName('test'),
                           property_class_iri=Iri('test:testprop3'),
                           datatype=XsdDatatypes.string,
                           restrictions=PropertyRestrictions(
                               restrictions={PropertyRestrictionType.IN: RdfSet(Xsd_string('yes'), Xsd_string('may be'), Xsd_string('no'))}
                           ))
        self.assertEqual(p3.property_class_iri, Xsd_QName('test:testprop3'))
        self.assertEqual(p3[PropClassAttr.RESTRICTIONS].get(PropertyRestrictionType.IN), {Xsd_string('yes'), Xsd_string('may be'), Xsd_string('no')})
        self.assertEqual(p3.get(PropClassAttr.DATATYPE), XsdDatatypes.string)

    # @unittest.skip('Work in progress')
    def test_propertyclass_read_shacl(self):
        p1 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:comment'))
        self.assertEqual(p1.property_class_iri, Iri('test:comment'))
        self.assertEqual(p1.get(PropClassAttr.DATATYPE), XsdDatatypes.string)
        self.assertEqual(p1.datatype, XsdDatatypes.string)
        self.assertTrue(p1.get(PropClassAttr.RESTRICTIONS)[PropertyRestrictionType.UNIQUE_LANG])
        self.assertTrue(p1.restrictions[PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1.get(PropClassAttr.RESTRICTIONS)[PropertyRestrictionType.MAX_COUNT], Xsd_integer(1))
        self.assertEqual(p1.restrictions[PropertyRestrictionType.MAX_COUNT], Xsd_integer(1))
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
        self.assertEqual(p2.property_class_iri, Xsd_QName('test:test'))
        self.assertEqual(p2[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.MIN_COUNT], Xsd_integer(1))
        self.assertEqual(p2[PropClassAttr.NAME], LangString("Test"))
        self.assertEqual(p2[PropClassAttr.DESCRIPTION], LangString("Property shape for testing purposes"))
        self.assertEqual(p2[PropClassAttr.TO_NODE_IRI], Xsd_QName('test:comment'))
        self.assertEqual(p2[PropClassAttr.ORDER], Xsd_decimal(3))
        self.assertEqual(p2[PropClassAttr.PROPERTY_TYPE], OwlPropertyType.OwlObjectProperty)

        p3 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:enum'))
        self.assertEqual(p3[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.IN],
                         {"very good", "good", "fair", "insufficient"})
        self.assertEqual(p3[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.IN],
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
            restrictions=PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                PropertyRestrictionType.IN: RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2"))
            }),
            order=Xsd_decimal(11)
        )
        p1.create()
        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:testWrite'))
        self.assertEqual(p2.property_class_iri, Iri('test:testWrite'))
        self.assertEqual(p2[PropClassAttr.TO_NODE_IRI], Iri('test:comment'))
        self.assertEqual(p2[PropClassAttr.NAME], LangString("Annotations@en"))
        self.assertEqual(p2[PropClassAttr.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertEqual(p2[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.IN],
                         RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2")))

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
            toNodeIri=Iri('test:comment'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            restrictions=PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.LANGUAGE_IN: LanguageIn(Language.EN, Language.DE),
                    PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                    PropertyRestrictionType.PATTERN: Xsd_string('*.'),
                    PropertyRestrictionType.IN: RdfSet(Iri("http://www.test.org/comment1"),
                                                       Iri("http://www.test.org/comment2"),
                                                       Iri("http://www.test.org/comment3"))

                }
            ),
            order=Xsd_decimal(11)
        )
        self.assertEqual(p1[PropClassAttr.TO_NODE_IRI], Xsd_QName('test:comment'))
        self.assertIsNone(p1.get(PropClassAttr.DATATYPE)),
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         LanguageIn(Language.EN, Language.DE))
        self.assertTrue(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.PATTERN], '*.')
        self.assertEqual(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.IN],
                         RdfSet(Iri("http://www.test.org/comment1"),
                                Iri("http://www.test.org/comment2"),
                                Iri("http://www.test.org/comment3")))
        self.assertEqual(p1[PropClassAttr.ORDER], Xsd_decimal(11))

        p1[PropClassAttr.TO_NODE_IRI] = Iri('test:waseliwas')
        p1[PropClassAttr.NAME][Language.FR] = "Annotations en Français"
        del p1[PropClassAttr.NAME][Language.EN]
        p1[PropClassAttr.DESCRIPTION] = LangString("A description@en")
        p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN] = LanguageIn(Language.EN, Language.DE, Language.FR)
        p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.IN] = RdfSet(Iri("http://google.com"), Iri("https://google.com"))
        p1[PropClassAttr.ORDER] = Xsd_decimal(22)

        self.assertEqual(p1[PropClassAttr.TO_NODE_IRI], Iri('test:waseliwas'))
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotationen@de", "Annotations en Français@fr"]))
        self.assertEqual(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         LanguageIn(Language.EN, Language.DE, Language.FR))
        self.assertTrue(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.PATTERN], Xsd_string('*.'))
        self.assertEqual(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.IN],
                         RdfSet(Iri("http://google.com"), Iri("https://google.com")))
        self.assertEqual(p1[PropClassAttr.ORDER], Xsd_decimal(22))
        p1.undo()
        self.assertEqual(p1[PropClassAttr.TO_NODE_IRI], Iri('test:comment'))
        self.assertIsNone(p1.get(PropClassAttr.DATATYPE))
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         LanguageIn(Language.EN, Language.DE))
        self.assertTrue(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.PATTERN], Xsd_string('*.'))
        self.assertEqual(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.IN],
                         RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2"), Iri("http://www.test.org/comment3")))
        self.assertEqual(p1[PropClassAttr.ORDER], Xsd_decimal(11))

        p1[PropClassAttr.TO_NODE_IRI] = Iri('test:waseliwas')
        p1[PropClassAttr.NAME][Language.FR] = "Annotations en Français"
        del p1[PropClassAttr.NAME][Language.EN]
        p1[PropClassAttr.DESCRIPTION] = LangString("A description@en")
        p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN] = LanguageIn(Language.EN, Language.DE, Language.FR)
        p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.IN] = RdfSet(
            Iri("https://gaga.com"), Iri("https://gugus.com")
        )
        p1[PropClassAttr.ORDER] = Xsd_decimal(22)

        p1.undo(PropClassAttr.TO_NODE_IRI)
        self.assertEqual(p1[PropClassAttr.TO_NODE_IRI], Iri('test:comment'))
        p1.undo(PropClassAttr.NAME)
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        p1.undo(PropClassAttr.DESCRIPTION)
        self.assertIsNone(p1.get(PropClassAttr.DESCRIPTION))
        p1.undo(PropertyRestrictionType.LANGUAGE_IN)
        self.assertEqual(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         LanguageIn(Language.EN, Language.DE))
        p1.undo(PropertyRestrictionType.IN)
        self.assertEqual(p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.IN],
                         RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2"), Iri("http://www.test.org/comment3")))
        p1.undo(PropClassAttr.ORDER)
        self.assertEqual(p1[PropClassAttr.ORDER], Xsd_decimal(11))
        self.assertEqual(p1.changeset, {})

    # @unittest.skip('Work in progress')
    def test_propertyclass_update(self):
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testUpdate'),
            toNodeIri=Iri('test:comment'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            restrictions=PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                PropertyRestrictionType.MAX_COUNT: Xsd_integer(1),
                PropertyRestrictionType.MIN_COUNT: Xsd_integer(0)
            }),
            order=Xsd_decimal(11)
        )
        p1.create()
        p1[PropClassAttr.ORDER] = Xsd_decimal(12)
        p1[PropClassAttr.NAME][Language.DE] = 'Annotationen'
        p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG] = Xsd_boolean(False)
        p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.IN] = RdfSet(Xsd_string("gaga"), Xsd_string("is was"))
        p1[PropClassAttr.DATATYPE] = XsdDatatypes.string
        self.assertEqual(p1.changeset, {
            PropClassAttr.ORDER: PropClassAttrChange(Xsd_decimal(11), Action.REPLACE, True),
            PropClassAttr.NAME: PropClassAttrChange(None, Action.MODIFY, True),
            PropClassAttr.RESTRICTIONS: PropClassAttrChange(None, Action.MODIFY, True),
            PropClassAttr.DATATYPE: PropClassAttrChange(None, Action.CREATE, True),
            PropClassAttr.TO_NODE_IRI: PropClassAttrChange(Iri('test:comment'), Action.DELETE, True)  # TODO!!!!!!!!!!!!!
        })
        p1.update()
        self.assertEqual(p1.changeset, {})

        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:testUpdate'))
        self.assertEqual(p2.property_class_iri, Iri('test:testUpdate'))
        self.assertEqual(p2[PropClassAttr.DATATYPE], XsdDatatypes.string)
        self.assertIsNone(p2.get(PropClassAttr.TO_NODE_IRI))
        self.assertEqual(p2[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p2[PropClassAttr.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertEqual(p2[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.IN], RdfSet(Xsd_string("gaga"), Xsd_string("is was")))
        self.assertEqual(p2[PropClassAttr.ORDER], Xsd_decimal(12))
        self.assertFalse(p2[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])

    def test_propertyclass_update2(self):
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testUpdate2'),
            toNodeIri=Iri('test:comment'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            restrictions=PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                PropertyRestrictionType.MAX_COUNT: Xsd_integer(1),
                PropertyRestrictionType.MIN_COUNT: Xsd_integer(0)
            }),
            order=Xsd_decimal(11)
        )
        p1.create()
        p1.order = Xsd_decimal(12)
        p1.name[Language.DE] = 'Annotationen'
        p1.restrictions[PropertyRestrictionType.UNIQUE_LANG] = Xsd_boolean(False)
        p1.restrictions[PropertyRestrictionType.IN] = RdfSet(Xsd_string("gaga"), Xsd_string("is was"))
        p1.datatype = XsdDatatypes.string
        self.maxDiff = None
        self.assertEqual(p1.changeset, {
            PropClassAttr.ORDER: PropClassAttrChange(Xsd_decimal(11), Action.REPLACE, True),
            PropClassAttr.NAME: PropClassAttrChange(None, Action.MODIFY, True),
            PropClassAttr.RESTRICTIONS: PropClassAttrChange(None, Action.MODIFY, True),
            PropClassAttr.DATATYPE: PropClassAttrChange(None, Action.CREATE, True),
            PropClassAttr.TO_NODE_IRI: PropClassAttrChange(Iri('test:comment'), Action.DELETE, True)  # TODO!!!!!!!!!!!!!
        })
        p1.update()
        self.assertEqual(p1.changeset, {})

        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:testUpdate2'))
        self.assertEqual(p2.property_class_iri, Iri('test:testUpdate2'))
        self.assertEqual(p2.datatype, XsdDatatypes.string)
        self.assertIsNone(p2.toNodeIri)
        self.assertEqual(p2.name, LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p2.description, LangString("An annotation@en"))
        self.assertEqual(p2.restrictions[PropertyRestrictionType.LANGUAGE_IN],
                         LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertEqual(p2.restrictions[PropertyRestrictionType.IN], RdfSet(Xsd_string("gaga"), Xsd_string("is was")))
        self.assertEqual(p2.order, Xsd_decimal(12))
        self.assertFalse(p2.restrictions[PropertyRestrictionType.UNIQUE_LANG])

    def test_propertyclass_delete_attrs(self):
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Xsd_QName('test:testDelete'),
            toNodeIri=Iri('test:comment'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            description=LangString("An annotation@en"),
            restrictions=PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: LanguageIn(Language.ZU, Language.CY, Language.SV, Language.RM),
                PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                PropertyRestrictionType.MAX_COUNT: Xsd_integer(1),
                PropertyRestrictionType.MIN_COUNT: Xsd_integer(0),
                PropertyRestrictionType.IN: RdfSet(Xsd_string('A'), Xsd_string('B'), Xsd_string('C'))
            }),
            order=Xsd_decimal(11)
        )
        p1.create()
        del p1[PropClassAttr.NAME]
        del p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.MAX_COUNT]
        del p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG]
        del p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN]
        del p1[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.IN]
        p1.update()

        p2 = PropertyClass.read(con=self._connection,
                                graph=Xsd_NCName('test'),
                                property_class_iri=Iri('test:testDelete'))
        self.assertEqual(p2.restrictions.get(PropertyRestrictionType.MIN_COUNT), 0)
        self.assertIsNone(p2.name)
        self.assertIsNone(p2.restrictions.get(PropertyRestrictionType.MAX_COUNT))
        self.assertIsNone(p2.restrictions.get(PropertyRestrictionType.UNIQUE_LANG))
        self.assertIsNone(p2.restrictions.get(PropertyRestrictionType.LANGUAGE_IN))
        self.assertIsNone(p2.restrictions.get(PropertyRestrictionType.IN))
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
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testDeleteIt'),
            toNodeIri=Iri('test:comment'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            description=LangString("An annotation@en"),
            restrictions=PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: LanguageIn(Language.ZU, Language.CY, Language.SV, Language.RM),
                PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                PropertyRestrictionType.MAX_COUNT: Xsd_integer(1),
                PropertyRestrictionType.MIN_COUNT: Xsd_integer(0)
            }),
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
        props: PropClassAttrContainer = {
            PropClassAttr.TO_NODE_IRI: Xsd_QName('test:comment'),
            PropClassAttr.DATATYPE: XsdDatatypes.anyURI,
            PropClassAttr.NAME: LangString(["Annotations@en", "Annotationen@de"]),
            PropClassAttr.DESCRIPTION: LangString("An annotation@en"),
            PropClassAttr.RESTRICTIONS: PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: LanguageIn(Language.ZU, Language.CY, Language.SV, Language.RM),
                PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                PropertyRestrictionType.MAX_COUNT: Xsd_integer(1),
                PropertyRestrictionType.MIN_COUNT: Xsd_integer(0)
            }),
            PropClassAttr.ORDER: 11
        }
        p1 = PropertyClass(
            con=self._connection,
            graph=Xsd_NCName('test'),
            property_class_iri=Iri('test:testWriteIt'),
            toNodeIri=Iri('test:comment'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            description=LangString("An annotation@en"),
            restrictions=PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: LanguageIn(Language.ZU, Language.CY, Language.SV, Language.RM),
                PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                PropertyRestrictionType.MAX_COUNT: Xsd_integer(1),
                PropertyRestrictionType.MIN_COUNT: Xsd_integer(0)
            })
        )
        p1.write_as_trig('propclass_test.trig')


if __name__ == '__main__':
    unittest.main()
