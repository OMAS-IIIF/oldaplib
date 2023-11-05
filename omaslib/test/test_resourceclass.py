import unittest
from time import sleep
from typing import Dict, List

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName
from omaslib.src.helpers.langstring import LangString
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
        properties: List[PropertyClass] = [
            PropertyClass(con=self._connection,
                          property_class_iri=QName("test:comment")),
            PropertyClass(con=self._connection,
                          property_class_iri=QName("test:test")),
        ]

        r1 = ResourceClass(con=self._connection,
                           owl_cass="TestResource",
                           attrs=attrs,
                           properties=properties)
        self.assertEqual(r1[ResourceClassAttributes.LABEL], LangString(["Test resource@en", "Resource de test@fr"]))
        self.assertEqual(r1[ResourceClassAttributes.COMMENT], LangString("For testing purposes@en"))
        self.assertTrue(r1[ResourceClassAttributes.CLOSED])
        self.assertEqual(r1[QName("test:comment")].property_class_iri, QName("test:comment"))
        self.assertEqual(r1[QName("test:comment")][PropertyClassAttribute.DATATYPE], XsdDatatypes.string)
        self.assertEqual(r1[QName("test:comment")][PropertyClassAttribute.NAME], LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(r1[QName("test:comment")][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MAX_COUNT], 1)
