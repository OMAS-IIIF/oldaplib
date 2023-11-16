import unittest
from datetime import datetime
from pprint import pprint
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName, Action
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.propertyclass import PropertyClass, OwlPropertyType, PropertyClassAttributesContainer, PropertyClassAttributeChange
from omaslib.src.helpers.propertyclassprops import PropertyClassAttribute
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
                                     userid="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        cls._connection.clear_graph(QName('test:shacl'))
        cls._connection.clear_graph(QName('test:onto'))
        cls._connection.upload_turtle("omaslib/testdata/connection_test.trig")
        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(QName('test:shacl'))
        #cls._connection.clear_graph(QName('test:onto'))
        pass

    def test_propertyclass_constructor(self):
        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.SUBPROPERTY_OF: QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.NAME: LangString(["Test property@en", "Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("A property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={PropertyRestrictionType.MAX_COUNT: 1}),
            PropertyClassAttribute.ORDER: 5
        }
        p = PropertyClass(con=self._connection,
                          property_class_iri=QName('test:testprop'),
                          attrs=props)
        self.assertEqual(p.property_class_iri, QName('test:testprop'))
        self.assertEqual(p.get(PropertyClassAttribute.SUBPROPERTY_OF), QName('test:comment'))
        self.assertEqual(p.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertEqual(p.get(PropertyClassAttribute.NAME), LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(p.get(PropertyClassAttribute.ORDER), 5)
        self.assertIsNone(p.get(PropertyClassAttribute.EXCLUSIVE_FOR))

    def test_propertyclass_read_shacl(self):
        #p1 = PropertyClass(con=self._connection, property_class_iri=QName('test:comment'))
        p1 = PropertyClass.read(con=self._connection, property_class_iri=QName('test:comment'))
        self.assertEqual(p1.property_class_iri, QName('test:comment'))
        self.assertEqual(p1.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertTrue(p1.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(p1.get(PropertyClassAttribute.NAME), LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(p1.get(PropertyClassAttribute.DESCRIPTION), LangString("This is a test property@de"))
        self.assertIsNone(p1.get(PropertyClassAttribute.EXCLUSIVE_FOR))
        self.assertIsNone(p1.get(PropertyClassAttribute.SUBPROPERTY_OF))
        self.assertEqual(p1[PropertyClassAttribute.ORDER], 2)
        self.assertEqual(p1.get(PropertyClassAttribute.PROPERTY_TYPE), OwlPropertyType.OwlDataProperty)
        self.assertEqual(p1.creator, QName('orcid:ORCID-0000-0003-1681-4036'))
        self.assertEqual(p1.created, datetime.fromisoformat("2023-11-04T12:00:00Z"))

        #p2 = PropertyClass(con=self._connection, property_class_iri=QName('test:test'))
        p2 = PropertyClass.read(con=self._connection, property_class_iri=QName('test:test'))
        self.assertEqual(p2.property_class_iri, QName('test:test'))
        self.assertEqual(p2[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(p2[PropertyClassAttribute.NAME], LangString("Test"))
        self.assertEqual(p2[PropertyClassAttribute.DESCRIPTION], LangString("Property shape for testing purposes"))
        self.assertIsNone(p2.get(PropertyClassAttribute.EXCLUSIVE_FOR))
        self.assertEqual(p2[PropertyClassAttribute.TO_NODE_IRI], QName('test:comment'))
        self.assertEqual(p2[PropertyClassAttribute.ORDER], 3)
        self.assertEqual(p2[PropertyClassAttribute.PROPERTY_TYPE], OwlPropertyType.OwlObjectProperty)

    def test_propertyclass_write(self):
        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.anyURI,
            PropertyClassAttribute.NAME: LangString("Annotations@en"),
            PropertyClassAttribute.DESCRIPTION: LangString("An annotation@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT},
                PropertyRestrictionType.UNIQUE_LANG: True
            }),
            PropertyClassAttribute.ORDER: 11
        }
        p1 = PropertyClass(
            con=self._connection,
            property_class_iri=QName('test:testWrite'),
            attrs=props
        )
        p1.create()
        #p1.delete_singleton()
        del p1
        #p2 = PropertyClass(con=self._connection, property_class_iri=QName('test:testWrite'))
        p2 = PropertyClass.read(con=self._connection, property_class_iri=QName('test:testWrite'))
        self.assertEqual(p2.property_class_iri, QName('test:testWrite'))
        self.assertEqual(p2[PropertyClassAttribute.TO_NODE_IRI], QName('test:comment'))
        self.assertEqual(p2[PropertyClassAttribute.NAME], LangString("Annotations@en"))
        self.assertEqual(p2[PropertyClassAttribute.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE, Language.FR, Language.IT})
        self.assertEqual(p2[PropertyClassAttribute.ORDER], 11)

    def test_propertyclass_undo(self):
        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.anyURI,
            PropertyClassAttribute.NAME: LangString(["Annotations@en", "Annotationen@de"]),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE},
                PropertyRestrictionType.UNIQUE_LANG: True,
                PropertyRestrictionType.PATTERN: '*.'
            }),
            PropertyClassAttribute.ORDER: 11
        }
        p1 = PropertyClass(
            con=self._connection,
            property_class_iri=QName('test:testUndo'),
            attrs=props
        )
        self.assertEqual(p1[PropertyClassAttribute.TO_NODE_IRI], QName('test:comment'))
        self.assertEqual(p1[PropertyClassAttribute.DATATYPE], XsdDatatypes.anyURI)
        self.assertEqual(p1[PropertyClassAttribute.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE})
        self.assertTrue(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.PATTERN], '*.')
        self.assertEqual(p1[PropertyClassAttribute.ORDER], 11)

        p1[PropertyClassAttribute.TO_NODE_IRI] = QName('test:waseliwas')
        p1[PropertyClassAttribute.NAME][Language.FR] = "Annotations en Français"
        del p1[PropertyClassAttribute.NAME][Language.EN]
        p1[PropertyClassAttribute.DESCRIPTION] = LangString("A description@en")
        p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN] = {Language.EN, Language.DE, Language.FR}
        p1[PropertyClassAttribute.ORDER] = 22

        self.assertEqual(p1[PropertyClassAttribute.TO_NODE_IRI], QName('test:waseliwas'))
        self.assertEqual(p1[PropertyClassAttribute.DATATYPE], XsdDatatypes.anyURI)
        self.assertEqual(p1[PropertyClassAttribute.NAME], LangString(["Annotationen@de", "Annotations en Français@fr"]))
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE, Language.FR})
        self.assertTrue(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.PATTERN], '*.')
        self.assertEqual(p1[PropertyClassAttribute.ORDER], 22)

        p1.undo()
        self.assertEqual(p1[PropertyClassAttribute.TO_NODE_IRI], QName('test:comment'))
        self.assertEqual(p1[PropertyClassAttribute.DATATYPE], XsdDatatypes.anyURI)
        self.assertEqual(p1[PropertyClassAttribute.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE})
        self.assertTrue(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.PATTERN], '*.')
        self.assertEqual(p1[PropertyClassAttribute.ORDER], 11)

        p1[PropertyClassAttribute.TO_NODE_IRI] = QName('test:waseliwas')
        p1[PropertyClassAttribute.NAME][Language.FR] = "Annotations en Français"
        del p1[PropertyClassAttribute.NAME][Language.EN]
        p1[PropertyClassAttribute.DESCRIPTION] = LangString("A description@en")
        p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN] = {Language.EN, Language.DE, Language.FR}
        p1[PropertyClassAttribute.ORDER] = 22

        p1.undo(PropertyClassAttribute.TO_NODE_IRI)
        self.assertEqual(p1[PropertyClassAttribute.TO_NODE_IRI], QName('test:comment'))
        p1.undo(PropertyClassAttribute.NAME)
        self.assertEqual(p1[PropertyClassAttribute.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        p1.undo(PropertyClassAttribute.DESCRIPTION)
        self.assertIsNone(p1.get(PropertyClassAttribute.DESCRIPTION))
        p1.undo(PropertyRestrictionType.LANGUAGE_IN)
        self.assertEqual(p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE})
        p1.undo(PropertyClassAttribute.ORDER)
        self.assertEqual(p1[PropertyClassAttribute.ORDER], 11)
        self.assertEqual(p1.changeset, {})

    def test_propertyclass_update(self):
        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.anyURI,
            PropertyClassAttribute.NAME: LangString("Annotations@en"),
            PropertyClassAttribute.DESCRIPTION: LangString("An annotation@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(restrictions={
                PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT},
                PropertyRestrictionType.UNIQUE_LANG: True,
                PropertyRestrictionType.MAX_COUNT: 1,
                PropertyRestrictionType.MIN_COUNT: 0
            }),
            PropertyClassAttribute.ORDER: 11
        }
        p1 = PropertyClass(
            con=self._connection,
            property_class_iri=QName('test:testUpdate'),
            attrs=props
        )
        p1.create()
        p1[PropertyClassAttribute.ORDER] = 12
        p1[PropertyClassAttribute.NAME][Language.DE] = 'Annotationen'
        p1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG] = False
        p1[PropertyClassAttribute.DATATYPE] = XsdDatatypes.string
        self.assertEqual(p1.changeset, {
            PropertyClassAttribute.ORDER: PropertyClassAttributeChange(11, Action.REPLACE, True),
            PropertyClassAttribute.NAME: PropertyClassAttributeChange(None, Action.MODIFY, True),
            PropertyClassAttribute.RESTRICTIONS: PropertyClassAttributeChange(None, Action.MODIFY, True),
            PropertyClassAttribute.DATATYPE: PropertyClassAttributeChange(XsdDatatypes.anyURI, Action.CREATE, True),
            PropertyClassAttribute.TO_NODE_IRI: PropertyClassAttributeChange(QName('test:comment'), Action.DELETE, True)
        })
        p1.update()
        self.assertEqual(p1.changeset, {})

        #p1.delete_singleton()
        del p1
        #p2 = PropertyClass(con=self._connection, property_class_iri=QName('test:testUpdate'))
        p2 = PropertyClass.read(con=self._connection, property_class_iri=QName('test:testUpdate'))
        self.assertEqual(p2.property_class_iri, QName('test:testUpdate'))
        self.assertEqual(p2[PropertyClassAttribute.DATATYPE], XsdDatatypes.string)
        self.assertIsNone(p2.get(PropertyClassAttribute.TO_NODE_IRI))
        self.assertEqual(p2[PropertyClassAttribute.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p2[PropertyClassAttribute.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN],
                         {Language.EN, Language.DE, Language.FR, Language.IT})
        self.assertEqual(p2[PropertyClassAttribute.ORDER], 12)
        self.assertFalse(p2[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG])

if __name__ == '__main__':
    unittest.main()
