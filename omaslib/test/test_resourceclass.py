import unittest
from time import sleep
from typing import Dict, List, Union

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.propertyclassprops import PropertyClassAttribute
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.propertyclass import PropertyClassAttributesContainer, PropertyClass
from omaslib.src.propertyrestrictions import PropertyRestrictions, PropertyRestrictionType
from omaslib.src.resourceclass import ResourceClassAttributesContainer, ResourceClassAttributes, ResourceClass


class TestResourceClass(unittest.TestCase):
    _context: Context
    _connection: Connection

    @classmethod
    def setUpClass(cls):
        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://omas.org/test#")

        cls._connection = Connection(server='http://localhost:7200',
                                     userid="rosenth",
                                     credentials="RioGrande",
                                     repo="omas",
                                     context_name="DEFAULT")

        cls._connection.upload_turtle("omaslib/testdata/connection_test.trig")
        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        cls._connection.clear_graph(QName('test:shacl'))
        cls._connection.clear_graph(QName('test:onto'))
        pass

    def test_constructor(self):
        attrs: ResourceClassAttributesContainer = {
            ResourceClassAttributes.LABEL: LangString(["Test resource@en", "Resource de test@fr"]),
            ResourceClassAttributes.COMMENT: LangString("For testing purposes@en"),
            ResourceClassAttributes.CLOSED: True
        }

        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.SUBPROPERTY_OF: QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.NAME: LangString(["Test property@en", "Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("A property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 5
        }
        p = PropertyClass(con=self._connection, property_class_iri=QName('test:testprop'), attrs=props)
        self.assertEqual(p.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertEqual(p.get(PropertyClassAttribute.SUBPROPERTY_OF), QName("test:comment"))

        properties: List[Union[PropertyClass, QName]] = [QName("test:comment"), QName("test:test"), p]

        r1 = ResourceClass(con=self._connection,
                           owl_class_iri="TestResource",
                           attrs=attrs,
                           properties=properties)
        self.assertEqual(r1[ResourceClassAttributes.LABEL], LangString(["Test resource@en", "Resource de test@fr"]))
        self.assertEqual(r1[ResourceClassAttributes.COMMENT], LangString("For testing purposes@en"))
        self.assertTrue(r1[ResourceClassAttributes.CLOSED])

        prop1 = r1[QName("test:comment")]
        self.assertEqual(prop1.property_class_iri, QName("test:comment"))
        self.assertEqual(prop1[PropertyClassAttribute.DATATYPE], XsdDatatypes.string)
        self.assertEqual(prop1[PropertyClassAttribute.NAME], LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(prop1[PropertyClassAttribute.DESCRIPTION], LangString("This is a test property@de"))
        self.assertEqual(prop1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(prop1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG], True)

        prop2 = r1[QName("test:test")]
        self.assertEqual(prop2.property_class_iri, QName("test:test"))
        self.assertEqual(prop2.get(PropertyClassAttribute.TO_NODE_IRI), QName('test:comment'))
        self.assertEqual(prop2.get(PropertyClassAttribute.DESCRIPTION), LangString("Property shape for testing purposes"))
        self.assertEqual(prop2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MIN_COUNT), 1)
        self.assertEqual(prop2.get(PropertyClassAttribute.ORDER), 3)

        prop3 = r1[QName("test:testprop")]
        self.assertEqual(prop3.property_class_iri, QName("test:testprop"))
        self.assertEqual(prop3.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertEqual(prop3.get(PropertyClassAttribute.NAME), LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(prop3.get(PropertyClassAttribute.ORDER), 5)
        self.assertEqual(prop3[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MAX_COUNT), 1)
        self.assertEqual(prop3[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG], True)
        self.assertEqual(prop3[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN], {Language.EN, Language.DE, Language.FR, Language.IT})

    def test_reading(self):
        r1 = ResourceClass.read(con=self._connection, owl_class_iri=QName('test:testMyRes'))

