import unittest
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.propertyclass import PropertyClass, OwlPropertyType
from omaslib.src.propertyrestriction import PropertyRestrictionType, PropertyRestrictions


class TestPropertyClass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://omas.org/test#")

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     context_name="DEFAULT")

        cls._connection.upload_turtle("omaslib/testdata/connection_test.trig")
        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        cls._connection.clear_graph(QName('test:shacl'))
        cls._connection.clear_graph(QName('test:onto'))

    def test_propertyclass_constructor(self):
        p = PropertyClass(con=self._connection,
                          property_class_iri=QName('test:testprop'),
                          subproperty_of=QName('test:comment'),
                          datatype=XsdDatatypes.string,
                          name=LangString(["Test property@en", "Testprädikat@de"]),
                          description=LangString("A property for testing...@en"),
                          order=5)
        self.assertEqual(p.property_class_iri, QName('test:testprop'))
        self.assertEqual(p.subproperty_of, QName('test:comment'))
        self.assertEqual(p.datatype, XsdDatatypes.string)
        self.assertEqual(p.name, LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(p.order, 5)
        self.assertIsNone(p.exclusive_for_class)

    def test_propertyclass_read_shacl(self):
        p1 = PropertyClass(con=self._connection,
                          property_class_iri=QName('test:comment'))
        p1.read()
        self.assertEqual(p1.property_class_iri, QName('test:comment'))
        self.assertEqual(p1.datatype, XsdDatatypes.string)
        self.assertTrue(p1.restrictions[PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1.restrictions[PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(p1.name, LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(p1.description, LangString("This is a test property@de"))
        self.assertIsNone(p1.exclusive_for_class)
        self.assertIsNone(p1.subproperty_of)
        self.assertEqual(p1.order, 2)
        self.assertEqual(p1.property_type, OwlPropertyType.OwlDataProperty)

        p2 = PropertyClass(con=self._connection,
                           property_class_iri=QName('test:test'))
        p2.read()
        self.assertEqual(p2.property_class_iri, QName('test:test'))
        self.assertEqual(p2.restrictions[PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(p2.name, LangString("Test"))
        self.assertEqual(p2.description, LangString("Property shape for testing purposes"))
        self.assertIsNone(p2.exclusive_for_class)
        self.assertEqual(p2.to_node_iri, QName('test:comment'))
        self.assertEqual(p2.order, 3)
        self.assertEqual(p2.property_type, OwlPropertyType.OwlObjectProperty)

    def test_propertyclass_write(self):
        p1 = PropertyClass(
            con=self._connection,
            property_class_iri=QName('test:hasAnnotation'),
            to_node_iri=QName('test:comment'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            restrictions=PropertyRestrictions(
                restrictions={PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT},
                              PropertyRestrictionType.UNIQUE_LANG: True}
            )
        )
        p1.create_shacl()
        p1.delete_singleton()
        del p1
        p2 = PropertyClass(
            con=self._connection,
            property_class_iri=QName('test:hasAnnotation')
        )
        p2.read()
        self.assertEqual(p2.property_class_iri, QName('test:hasAnnotation'))
        self.assertEqual(p2.to_node_iri, QName('test:comment'))
        self.assertEqual(p2.name, LangString("Annotations@en"))
        self.assertEqual(p2.description, LangString("An annotation@en"))
        print(p2)
