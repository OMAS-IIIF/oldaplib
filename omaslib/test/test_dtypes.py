import json
import unittest

from omaslib.src.connection import Connection
from omaslib.src.dtypes.bnode import BNode
from omaslib.src.dtypes.languagein import LanguageIn
from omaslib.src.dtypes.namespaceiri import NamespaceIRI
from omaslib.src.dtypes.rdfset import RdfSet
from omaslib.src.enums.language import Language
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_integer import Xsd_integer
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_string import Xsd_string


class MyTestCase(unittest.TestCase):

    _connection: Connection

    @classmethod
    def setUpClass(cls):
        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://testing.org/datatypes#")
        cls._context.use('test')
        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._connection.clear_graph(Xsd_QName('test:test'))

    @classmethod
    def tearDownClass(cls):
        pass

    def create_triple(self, name: Xsd_NCName | str, value: Xsd):
        if not isinstance(name, Xsd_NCName):
            name = Xsd_NCName(name)
        sparql = self._context.sparql_context
        sparql += f"""
        INSERT DATA {{
            GRAPH test:test {{
                test:{name} test:prop {value.toRdf}
            }}
        }}"""
        self._connection.update_query(sparql)

    def get_triple(self, name: Xsd_NCName | str) -> Xsd:
        if not isinstance(name, Xsd_NCName):
            name = Xsd_NCName(name)
        sparql = self._context.sparql_context
        sparql += f"""
        SELECT ?value
        FROM test:test
        WHERE {{
            test:{name} test:prop ?value
        }}
        """
        result = self._connection.query(sparql)
        res = QueryProcessor(context=self._context, query_result=result)
        return res[0]['value']

    def delete_triple(self, name: Xsd_NCName):
        sparql = self._context.sparql_context
        sparql += f"""
        DELETE FROM test:test {{
            test:{name} test:prop ?value
        }}
        """

    def test_namespace(self):
        ns1 = NamespaceIRI('http://www.org/test/')
        self.assertEqual(str(ns1), 'http://www.org/test/')
        self.assertEqual(repr(ns1), 'NamespaceIRI("http://www.org/test/")')
        self.assertEqual(ns1.toRdf, '"http://www.org/test/"^^xsd:anyURI')
        self.assertEqual(ns1 + "gaga", Xsd_anyURI("http://www.org/test/gaga"))

        ns2 = NamespaceIRI('http://www.org/test#')
        self.assertEqual(str(ns2), 'http://www.org/test#')
        self.assertEqual(ns2 + "gaga", Xsd_anyURI("http://www.org/test#gaga"))

        jsonstr = json.dumps(ns1, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(ns1, val2)

        self.create_triple("NamespaceIRI", ns1)
        valx = self.get_triple("NamespaceIRI")
        self.assertIsInstance(valx, Xsd_anyURI)
        if isinstance(valx, Xsd_anyURI):
            self.assertEqual(ns1, NamespaceIRI(valx))

        with self.assertRaises(OmasErrorValue) as ex:
            nons = NamespaceIRI('http://www.org/test')
        self.assertEqual(str(ex.exception), "NamespaceIRI must end with '/' or '#'!")

        with self.assertRaises(OmasErrorValue) as ex:
            nons = NamespaceIRI('http://www.org/test\"; SELECT * FROM {?s ?p ?o}')

        with self.assertRaises(OmasErrorValue) as ex:
            nons = NamespaceIRI('http://www.org/test<super>\"; SELECT * FROM {?s ?p ?o}')

    def test_language_in(self):
        li = LanguageIn({"en", "fr", "it"})
        self.assertTrue(Language.EN in li)
        self.assertTrue(Language.FR in li)
        self.assertTrue(Language.IT in li)
        self.assertFalse(Language.DE in li)
        s = str(li)
        s = s.strip('() ')
        s = s.split(', ')
        self.assertTrue('"en"' in s)
        self.assertTrue('"fr"' in s)
        self.assertTrue('"it"' in s)
        s = repr(li)
        s = s.removeprefix('LanguageIn(')
        s = s.strip('()')
        s = s.split(', ')
        self.assertTrue('"fr"^^xsd:string' in s)
        self.assertTrue('"en"^^xsd:string' in s)
        self.assertTrue('"it"^^xsd:string' in s)

        s = li.toRdf
        s = s.strip('()')
        s = s.split(' ')
        self.assertTrue('"fr"^^xsd:string' in s)
        self.assertTrue('"en"^^xsd:string' in s)
        self.assertTrue('"it"^^xsd:string' in s)

        li = LanguageIn("en", "fr", "it")
        self.assertTrue(Language.EN in li)
        self.assertTrue(Language.FR in li)
        self.assertTrue(Language.IT in li)
        self.assertFalse(Language.DE in li)

        li = LanguageIn(Language.EN, "fr", Language.IT)
        self.assertTrue(Language.EN in li)
        self.assertTrue(Language.FR in li)
        self.assertTrue(Language.IT in li)
        self.assertFalse(Language.DE in li)

        li = LanguageIn([Language.EN, "fr", "it"])
        self.assertTrue(Language.EN in li)
        self.assertTrue(Language.FR in li)
        self.assertTrue(Language.IT in li)
        self.assertFalse(Language.DE in li)

        li.add("el")
        self.assertTrue(Language.EL in li)

        li.add(Language.AB)
        self.assertTrue(Language.AB in li)

        li.discard("en")
        self.assertFalse(Language.EN in li)

        li.discard(Language.FR)
        self.assertFalse(Language.FR in li)

        with self.assertRaises(OmasErrorValue) as ex:
            li = LanguageIn([Language.EN, "fr", "xyz"])

    def test_rdf_set(self):
        val = RdfSet({Xsd_string("was"), Xsd_string("ist"), Xsd_string("das?")})
        self.assertTrue(Xsd_string("was") in val)
        self.assertTrue(Xsd_string("ist") in val)
        self.assertTrue(Xsd_string("das?") in val)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        val.add(Xsd_integer(42))
        self.assertTrue(Xsd_integer(42) in val)

        val.discard(Xsd_string("ist"))
        self.assertFalse(Xsd_string("ist") in val)

        val = RdfSet(Xsd_string("was"), Xsd_string("ist"), Xsd_string("das?"))
        self.assertTrue(Xsd_string("was") in val)
        self.assertTrue(Xsd_string("ist") in val)
        self.assertTrue(Xsd_string("das?") in val)

    def test_bnode(self):
        val = BNode("_:node42")
        self.assertEqual(str(val), "_:node42")

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)


if __name__ == '__main__':
    unittest.main()
