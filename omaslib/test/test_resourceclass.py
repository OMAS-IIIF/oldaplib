import unittest
from datetime import datetime
from time import sleep
from typing import Dict, List, Union

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.propertyclassprops import PropertyClassAttribute
from omaslib.src.helpers.semantic_version import SemanticVersion
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.propertyclass import PropertyClassAttributesContainer, PropertyClass, OwlPropertyType
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
            PropertyClassAttribute.EXCLUSIVE_FOR: QName('test:TestResource'),
            PropertyClassAttribute.ORDER: 5
        }
        p = PropertyClass(con=self._connection, property_class_iri=QName('test:testprop'), attrs=props)
        self.assertEqual(p.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)

        properties: List[Union[PropertyClass, QName]] = [
            QName("test:comment"),
            QName("test:test"),
            p
        ]

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
        self.assertIsNone(prop1.get(PropertyClassAttribute.EXCLUSIVE_FOR))

        prop2 = r1[QName("test:test")]
        self.assertEqual(prop2.property_class_iri, QName("test:test"))
        self.assertEqual(prop2.get(PropertyClassAttribute.TO_NODE_IRI), QName('test:comment'))
        self.assertEqual(prop2.get(PropertyClassAttribute.DESCRIPTION), LangString("Property shape for testing purposes"))
        self.assertEqual(prop2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MIN_COUNT), 1)
        self.assertEqual(prop2.get(PropertyClassAttribute.ORDER), 3)
        self.assertIsNone(prop2.get(PropertyClassAttribute.EXCLUSIVE_FOR))

        prop3 = r1[QName("test:testprop")]
        self.assertEqual(prop3.property_class_iri, QName("test:testprop"))
        self.assertEqual(prop3.get(PropertyClassAttribute.PROPERTY_TYPE), OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop3.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertEqual(prop3.get(PropertyClassAttribute.NAME), LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(prop3.get(PropertyClassAttribute.ORDER), 5)
        self.assertEqual(prop3.get(PropertyClassAttribute.SUBPROPERTY_OF), QName("test:comment"))
        self.assertEqual(prop3.get(PropertyClassAttribute.EXCLUSIVE_FOR), QName('test:TestResource'))
        self.assertEqual(prop3[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MAX_COUNT), 1)
        self.assertEqual(prop3[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG], True)
        self.assertEqual(prop3[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN], {Language.EN, Language.DE, Language.FR, Language.IT})

    def test_reading(self):
        r1 = ResourceClass.read(con=self._connection, owl_class_iri=QName('test:testMyRes'))
        self.assertEqual(r1.owl_class_iri, QName('test:testMyRes'))
        self.assertEqual(r1.version, SemanticVersion(1, 0, 0))
        self.assertEqual(r1.creator, QName('orcid:ORCID-0000-0003-1681-4036'))
        self.assertEqual(r1.created, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(r1.contributor, QName('orcid:ORCID-0000-0003-1681-4036'))
        self.assertEqual(r1.modified, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(r1.get(ResourceClassAttributes.LABEL), LangString(["My Resource@en", "Meine Ressource@de", "Ma Resource@fr"]))
        self.assertEqual(r1.get(ResourceClassAttributes.COMMENT), LangString("Resource for testing..."))
        self.assertEqual(r1.get(ResourceClassAttributes.CLOSED), True)

        prop1 = r1[QName('test:test')]
        self.assertEqual(prop1.property_class_iri, QName("test:test"))
        self.assertEqual(prop1.version, SemanticVersion(1, 0, 0))
        self.assertEqual(prop1.creator, QName('orcid:ORCID-0000-0003-1681-4036'))
        self.assertEqual(prop1.created, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(prop1.contributor, QName('orcid:ORCID-0000-0003-1681-4036'))
        self.assertEqual(prop1.modified, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(prop1.get(PropertyClassAttribute.PROPERTY_TYPE), OwlPropertyType.OwlObjectProperty)
        self.assertEqual(prop1.get(PropertyClassAttribute.TO_NODE_IRI), QName('test:comment'))
        self.assertEqual(prop1.get(PropertyClassAttribute.DESCRIPTION), LangString("Property shape for testing purposes"))
        self.assertEqual(prop1[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MIN_COUNT), 1)
        self.assertEqual(prop1.get(PropertyClassAttribute.ORDER), 3)
        self.assertIsNone(prop1.get(PropertyClassAttribute.EXCLUSIVE_FOR))

        prop2 = r1[QName('test:hasText')]
        self.assertEqual(prop2.property_class_iri, QName("test:hasText"))
        self.assertEqual(prop2.version, SemanticVersion(1, 0, 0))
        self.assertEqual(prop2.creator, QName('orcid:ORCID-0000-0003-1681-4036'))
        self.assertEqual(prop2.created, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(prop2.contributor, QName('orcid:ORCID-0000-0003-1681-4036'))
        self.assertEqual(prop2.modified, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(prop2.get(PropertyClassAttribute.PROPERTY_TYPE), OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop2.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertEqual(prop2.get(PropertyClassAttribute.NAME), LangString(["A text", "Ein Text@de"]))
        self.assertEqual(prop2.get(PropertyClassAttribute.DESCRIPTION), LangString("A longer text..."))
        self.assertEqual(prop2.get(PropertyClassAttribute.ORDER), 1)
        self.assertEqual(prop2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MIN_COUNT), 1)
        self.assertEqual(prop2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MAX_COUNT), 1)
        self.assertEqual(prop2.get(PropertyClassAttribute.EXCLUSIVE_FOR), QName('test:testMyRes'))

