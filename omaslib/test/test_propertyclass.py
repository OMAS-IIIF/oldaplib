import unittest
from pprint import pprint
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName, Action
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.propertyclass import PropertyClass, OwlPropertyType, PropertyClassPropsContainer, PropertyClassPropChange
from omaslib.src.helpers.propertyclassprops import PropertyClassProp
from omaslib.src.propertyrestrictions import PropertyRestrictionType, PropertyRestrictions, RestrictionContainer


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
        pass

    def test_propertyclass_constructor(self):
        props: PropertyClassPropsContainer = {
            PropertyClassProp.SUBPROPERTY_OF: QName('test:comment'),
            PropertyClassProp.DATATYPE: XsdDatatypes.string,
            PropertyClassProp.NAME: LangString(["Test property@en", "Testprädikat@de"]),
            PropertyClassProp.DESCRIPTION: LangString("A property for testing...@en"),
            PropertyClassProp.RESTRICTIONS: PropertyRestrictions(
                restrictions={PropertyRestrictionType.MAX_COUNT: 1}),
            PropertyClassProp.ORDER: 5
        }
        p = PropertyClass(con=self._connection,
                          property_class_iri=QName('test:testprop'),
                          props=props)
        self.assertEqual(p.property_class_iri, QName('test:testprop'))
        self.assertEqual(p.get(PropertyClassProp.SUBPROPERTY_OF), QName('test:comment'))
        self.assertEqual(p.get(PropertyClassProp.DATATYPE), XsdDatatypes.string)
        self.assertEqual(p.get(PropertyClassProp.NAME), LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(p.get(PropertyClassProp.ORDER), 5)
        self.assertIsNone(p.get(PropertyClassProp.EXCLUSIVE_FOR))

    def test_propertyclass_read_shacl(self):
        p1 = PropertyClass(con=self._connection, property_class_iri=QName('test:comment'))
        p1.read()
        self.assertEqual(p1.property_class_iri, QName('test:comment'))
        self.assertEqual(p1.get(PropertyClassProp.DATATYPE), XsdDatatypes.string)
        self.assertTrue(p1.get(PropertyClassProp.RESTRICTIONS)[PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1.get(PropertyClassProp.RESTRICTIONS)[PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(p1.get(PropertyClassProp.NAME), LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(p1.get(PropertyClassProp.DESCRIPTION), LangString("This is a test property@de"))
        self.assertIsNone(p1.get(PropertyClassProp.EXCLUSIVE_FOR))
        self.assertIsNone(p1.get(PropertyClassProp.SUBPROPERTY_OF))
        self.assertEqual(p1[PropertyClassProp.ORDER], 2)
        self.assertEqual(p1.get(PropertyClassProp.PROPERTY_TYPE), OwlPropertyType.OwlDataProperty)

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
            property_class_iri=QName('test:testWrite'),
            props=props
        )
        p1.create()
        p1.delete_singleton()
        del p1
        p2 = PropertyClass(
            con=self._connection,
            property_class_iri=QName('test:testWrite')
        )
        p2.read()
        self.assertEqual(p2.property_class_iri, QName('test:testWrite'))
        self.assertEqual(p2[PropertyClassProp.TO_NODE_IRI], QName('test:comment'))
        self.assertEqual(p2[PropertyClassProp.NAME], LangString("Annotations@en"))
        self.assertEqual(p2[PropertyClassProp.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropertyClassProp.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE, Language.FR, Language.IT})
        self.assertEqual(p2[PropertyClassProp.ORDER], 11)

    def test_propertyclass_update(self):
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
            property_class_iri=QName('test:testUpdate'),
            props=props
        )
        p1.create()
        p1[PropertyClassProp.ORDER] = 12
        p1[PropertyClassProp.NAME][Language.DE] = 'Annotationen'
        p1[PropertyClassProp.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG] = False
        self.assertEqual(p1.changeset, {
            PropertyClassProp.ORDER: PropertyClassPropChange(11, Action.REPLACE, True),
            PropertyClassProp.NAME: PropertyClassPropChange(None, Action.MODIFY, True),
            PropertyClassProp.RESTRICTIONS: PropertyClassPropChange(None, Action.MODIFY, True)
        })
        p1.update()
        self.assertEqual(p1.changeset, {})

        p1.delete_singleton()
        del p1
        p2 = PropertyClass(
            con=self._connection,
            property_class_iri=QName('test:testUpdate')
        )
        p2.read()
        self.assertEqual(p2.property_class_iri, QName('test:testUpdate'))
        self.assertEqual(p2[PropertyClassProp.TO_NODE_IRI], QName('test:comment'))
        self.assertEqual(p2[PropertyClassProp.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p2[PropertyClassProp.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropertyClassProp.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE, Language.FR, Language.IT})
        self.assertEqual(p2[PropertyClassProp.ORDER], 12)
        self.assertFalse(p2[PropertyClassProp.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])

if __name__ == '__main__':
    unittest.main()
