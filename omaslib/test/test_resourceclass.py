import unittest
from enum import Enum
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.dtypes.languagein import LanguageIn
from omaslib.src.dtypes.namespaceiri import NamespaceIRI
from omaslib.src.dtypes.rdfset import RdfSet
from omaslib.src.enums.language import Language
from omaslib.src.enums.propertyclassattr import PropClassAttr
from omaslib.src.enums.propertyrestrictiontype import PropertyRestrictionType
from omaslib.src.enums.resourceclassattr import ResourceClassAttribute
from omaslib.src.enums.xsd_datatypes import XsdDatatypes
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.langstring import LangString
from omaslib.src.propertyclass import PropClassAttrContainer, PropertyClass, OwlPropertyType
from omaslib.src.propertyrestrictions import PropertyRestrictions
from omaslib.src.resourceclass import ResourceClass
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_boolean import Xsd_boolean
from omaslib.src.xsd.xsd_decimal import Xsd_decimal
from omaslib.src.xsd.xsd_integer import Xsd_integer
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_string import Xsd_string


class Graph(Enum):
    ONTO = 'test:onto'
    SHACL = 'test:shacl'


class TestResourceClass(unittest.TestCase):
    _context: Context
    _connection: Connection

    @classmethod
    def setUpClass(cls):
        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://omas.org/test#")
        cls._context.use('test', 'dcterms')

        cls._connection = Connection(server='http://localhost:7200',
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     repo="omas",
                                     context_name="DEFAULT")

        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        cls._connection.clear_graph(Xsd_QName('dcterms:shacl'))
        cls._connection.clear_graph(Xsd_QName('dcterms:onto'))
        cls._connection.upload_turtle("omaslib/testdata/connection_test.trig")
        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(QName('test:shacl'))
        #cls._connection.clear_graph(QName('test:onto'))
        pass

    #@unittest.skip('Work in progress')
    def test_constructor(self):
        p1 = PropertyClass(con=self._connection,
                           graph=Xsd_NCName('test'),
                           property_class_iri=Iri('test:testprop'),
                           subPropertyOf=Iri('test:comment'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["Test property@en", "Testprädikat@de"]),
                           description=LangString("A property for testing...@en"),
                           restrictions=PropertyRestrictions(restrictions={
                               PropertyRestrictionType.MAX_COUNT: Xsd_integer(1),
                               PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
                               PropertyRestrictionType.LANGUAGE_IN: LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT)

                           }),
                           order=Xsd_decimal(5))

        p2 = PropertyClass(con=self._connection,
                           graph=Xsd_NCName('test'),
                           property_class_iri=Iri('test:enumprop'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["Test enum@en", "Enumerationen@de"]),
                           restrictions=PropertyRestrictions(restrictions={
                               PropertyRestrictionType.MAX_COUNT: Xsd_integer(1),
                               PropertyRestrictionType.MIN_COUNT: Xsd_integer(1),
                               PropertyRestrictionType.IN: RdfSet(Xsd_string("yes"), Xsd_string("maybe"), Xsd_string("no"))
                           }),
                           order=Xsd_decimal(6))

        properties: list[PropertyClass | Iri] = [
            Iri("test:comment"),
            Iri("test:test"),
            p1, p2
        ]

        r1 = ResourceClass(con=self._connection,
                           graph=Xsd_NCName('test'),
                           owlclass_iri=Iri("test:TestResource"),
                           label=LangString(["Test resource@en", "Resource de test@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           properties=properties)
        self.assertEqual(r1[ResourceClassAttribute.LABEL], LangString(["Test resource@en", "Resource de test@fr"]))
        self.assertEqual(r1.label, LangString(["Test resource@en", "Resource de test@fr"]))
        self.assertEqual(r1[ResourceClassAttribute.COMMENT], LangString("For testing purposes@en"))
        self.assertEqual(r1.comment, LangString("For testing purposes@en"))
        self.assertTrue(r1[ResourceClassAttribute.CLOSED])
        self.assertTrue(r1.closed)

        prop1 = r1[Iri("test:comment")]
        self.assertIsNotNone(prop1)
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, Xsd_QName("test:comment"))
        self.assertEqual(prop1.datatype, XsdDatatypes.string)
        self.assertEqual(prop1.name, LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(prop1.description, LangString("This is a test property@de"))
        self.assertEqual(prop1.restrictions[PropertyRestrictionType.MAX_COUNT], Xsd_integer(1))
        self.assertEqual(prop1.restrictions[PropertyRestrictionType.UNIQUE_LANG], Xsd_boolean(True))

        prop2 = r1[Iri("test:test")]
        self.assertIsNone(prop2.internal)
        self.assertEqual(prop2.property_class_iri, Iri("test:test"))
        self.assertEqual(prop2.toNodeIri, Iri('test:comment'))
        self.assertEqual(prop2.description, LangString("Property shape for testing purposes"))
        self.assertEqual(prop2.restrictions.get(PropertyRestrictionType.MIN_COUNT), Xsd_integer(1))
        self.assertEqual(prop2.order, Xsd_decimal(3))

        prop3 = r1[Iri("test:testprop")]
        self.assertEqual(prop3.internal, Iri('test:TestResource'))
        self.assertEqual(prop3.property_class_iri, Iri("test:testprop"))
        self.assertEqual(prop3.propertyType, OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop3.datatype, XsdDatatypes.string)
        self.assertEqual(prop3.name, LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(prop3.order, Xsd_decimal(5))
        self.assertEqual(prop3.subPropertyOf, Iri("test:comment"))
        self.assertEqual(prop3.restrictions.get(PropertyRestrictionType.MAX_COUNT), Xsd_integer(1))
        self.assertEqual(prop3.restrictions[PropertyRestrictionType.UNIQUE_LANG], Xsd_boolean(True))
        self.assertEqual(prop3.restrictions[PropertyRestrictionType.LANGUAGE_IN], LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        prop4 = r1[Iri("test:enumprop")]
        self.assertEqual(prop4[PropClassAttr.RESTRICTIONS][PropertyRestrictionType.IN],
                         RdfSet(Xsd_string("yes"), Xsd_string("maybe"), Xsd_string("no")))


if __name__ == '__main__':
    unittest.main()
