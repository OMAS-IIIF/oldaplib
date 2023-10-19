import unittest
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName, Action
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.propertyclass import PropertyClass, OwlPropertyType, PropertyClassPropsContainer, PropertyClassProp
from omaslib.src.propertyrestriction import PropertyRestrictionType, PropertyRestrictions, RestrictionContainer


class TestPropertyClass(unittest.TestCase):
    _context: Context
    _connection: Connection

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
        props: PropertyClassPropsContainer = {
            PropertyClassProp.SUBPROPERTY_OF: QName('test:testprop'),
            PropertyClassProp.DATATYPE: XsdDatatypes.string,
            PropertyClassProp.NAME: LangString(["Test property@en", "Testprädikat@de"]),
            PropertyClassProp.DESCRIPTION: LangString("A property for testing...@en"),
            PropertyClassProp.RESTRICTIONS: PropertyRestrictions(restrictions={
              PropertyRestrictionType.MAX_COUNT: 1
            }),
            PropertyClassProp.ORDER: 5
        }
        p = PropertyClass(con=self._connection,
                          property_class_iri=QName('test:testprop'),
                          props=props)
        self.assertEqual(p.property_class_iri, QName('test:testprop'))
        self.assertEqual(p.subproperty_of, QName('test:comment'))
        self.assertEqual(p.datatype, XsdDatatypes.string)
        self.assertEqual(p.name, LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(p.order, 5)
        self.assertIsNone(p.exclusive_for_class)

    def test_propertyclass_read_shacl(self):
        p1 = PropertyClass(con=self._connection, property_class_iri=QName('test:comment'))
        p1.read()
        self.assertEqual(p1.property_class_iri, QName('test:comment'))
        self.assertEqual(p1[PropertyClassProp.DATATYPE], XsdDatatypes.string)
        self.assertTrue(p1[PropertyClassProp.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1[PropertyClassProp.RESTRICTIONS][PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(p1[PropertyClassProp.NAME], LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(p1[PropertyClassProp.DESCRIPTION], LangString("This is a test property@de"))
        self.assertIsNone(p1.get(PropertyClassProp.EXCLUSIVE_FOR))
        #self.assertIsNone(p1.subproperty_of)
        #self.assertEqual(p1[PropertyClassProp.ORDER], 2)
        self.assertEqual(p1[PropertyClassProp.PROPERTY_TYPE], OwlPropertyType.OwlDataProperty)

        p2 = PropertyClass(con=self._connection,
                           property_class_iri=QName('test:test'))
        p2.read()
        self.assertEqual(p2.property_class_iri, QName('test:test'))
        self.assertEqual(p2[PropertyClassProp.RESTRICTIONS][PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(p2[PropertyClassProp.NAME], LangString("Test"))
        self.assertEqual(p2[PropertyClassProp.DESCRIPTION], LangString("Property shape for testing purposes"))
        self.assertIsNone(p2.get(PropertyClassProp.EXCLUSIVE_FOR))
        self.assertEqual(p2[PropertyClassProp.TO_NODE_IRI], QName('test:comment'))
        self.assertEqual(p2[PropertyClassProp.ORDER], 3)
        self.assertEqual(p2[PropertyClassProp.PROPERTY_TYPE], OwlPropertyType.OwlObjectProperty)

    def test_propertyclass_write(self):
        props: PropertyClassPropsContainer = {
            PropertyClassProp.TO_NODE_IRI: QName('test:comment'),
            PropertyClassProp.DATATYPE: XsdDatatypes.anyURI,
            PropertyClassProp.NAME: LangString("Annotations@en"),
            PropertyClassProp.DESCRIPTION: LangString("An annotation@en"),
            PropertyClassProp.RESTRICTIONS: PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT},
                PropertyRestrictionType.UNIQUE_LANG: True
            }),
            PropertyClassProp.ORDER: 11
        }
        p1 = PropertyClass(
            con=self._connection,
            property_class_iri=QName('test:hasAnnotation'),
            props=props
        )
        print("**************************")
        print(p1.create_shacl(as_string=True))
        print("**************************")
        p1.create_shacl()
        p1.delete_singleton()
        del p1
        p2 = PropertyClass(
            con=self._connection,
            property_class_iri=QName('test:hasAnnotation')
        )
        p2.read()
        self.assertEqual(p2.property_class_iri, QName('test:hasAnnotation'))
        self.assertEqual(p2[PropertyClassProp.TO_NODE_IRI], QName('test:comment'))
        self.assertEqual(p2[PropertyClassProp.NAME], LangString("Annotations@en"))
        self.assertEqual(p2[PropertyClassProp.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropertyClassProp.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE, Language.FR, Language.IT})
        self.assertEqual(p2[PropertyClassProp.ORDER], 11)

        #p2.name_add(Language.DE, "Annotationen")
        #self.assertEqual(p2.changeset, {('name', Action.CREATE)})

if __name__ == '__main__':
    unittest.main()