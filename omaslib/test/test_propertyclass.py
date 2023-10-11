import unittest
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.propertyclass import PropertyClass


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

    def test_propertyclass_constructor(self):
        p = PropertyClass(con=self._connection,
                          property_class_iri=QName('test:testprop'),
                          subproperty_of=QName('test:comment'),
                          datatype=XsdDatatypes.string,
                          name=LangString("Test property@en"),
                          description=LangString("A property for testing...@en"),
                          order=5)
        self.assertEqual(p.property_class_iri, QName('test:testprop'))
