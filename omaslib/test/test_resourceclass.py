import unittest
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.propertyclassprops import PropertyClassAttribute
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.propertyclass import PropertyClassAttributesContainer, PropertyClass
from omaslib.src.propertyrestrictions import PropertyRestrictions, PropertyRestrictionType


class TestResourceClass(unittest.TestCase):
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

    def test_constructor(self):
        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.SUBPROPERTY_OF: QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.NAME: LangString(["Test property@en", "Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("A property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={PropertyRestrictionType.MAX_COUNT: 1}),
            PropertyClassAttribute.ORDER: 5
        }
        comment_p = PropertyClass(con=self._connection,
                                  property_class_iri=QName('test:testprop'),
                                  attrs=props)

        pdict = {

        }
