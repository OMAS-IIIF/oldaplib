import unittest
from pprint import pprint
from time import sleep

from rdflib import URIRef

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import QName, NamespaceIRI
from omaslib.src.helpers.omaserror import OmasError


#sys.path.append("/Users/rosenth/ProgDev/OMAS/omaslib/omaslib")
#sys.path.append("omaslib")

class TestBasicConnection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://omas.org/test#")

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     userid="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        cls._connection.upload_turtle("omaslib/testdata/connection_test.trig")
        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        cls._connection.clear_graph(QName('test:shacl'))

    def test_basic_connection(self):
        con = Connection(server='http://localhost:7200',
                         repo="omas",
                         userid="rosenth",
                         credentials="RioGrande",
                         context_name="DEFAULT")
        self.assertIsInstance(con, Connection)
        self.assertEqual(con.server, 'http://localhost:7200')
        self.assertEqual(con.repo, 'omas')
        self.assertEqual(con.context_name, 'DEFAULT')

        with self.assertRaises(OmasError) as ex:
            con = Connection(server='http://localhost:7200',
                             repo="omas",
                             userid="rosenth",
                             credentials="XXX",
                             context_name="DEFAULT")
        self.assertEqual(str(ex.exception), "Wrong credentials")


    def test_query(self):
        query = self._context.sparql_context
        query += """
        SELECT ?s ?p ?o
        FROM test:shacl
        WHERE {
            ?s sh:path ?o
        }
        """
        res = self._connection.query(query)
        expected = {
            'head': {
                'vars': ['s', 'p', 'o']
            },
            'results': {
                'bindings': [{'o': {'type': 'uri', 'value': 'http://omas.org/test#comment'},
                              's': {'type': 'uri', 'value': 'http://omas.org/test#commentShape'}
                              },{'o': {'type': 'uri', 'value': 'http://omas.org/test#test'},
                              's': {'type': 'uri', 'value': 'http://omas.org/test#testShape'}
                              }]
            }
        }
        self.maxDiff = None
        self.assertDictEqual(res, expected)

    def test_rdflib_query(self):
        query = self._context.sparql_context
        query += """
        SELECT ?s ?p ?o
        FROM test:shacl
        WHERE {
            ?s ?p ?o
        }
        """
        p = URIRef('http://www.w3.org/ns/shacl#path')
        res = self._connection.rdflib_query(query, {'p': p})
        self.assertEqual(len(res), 2)
        s0 = {URIRef('http://omas.org/test#commentShape'), URIRef('http://omas.org/test#testShape')}
        s2 = {URIRef('http://omas.org/test#comment'), URIRef('http://omas.org/test#test')}
        for r in res:
            self.assertIn(r[0], s0)
            self.assertEqual(r[1], URIRef('http://www.w3.org/ns/shacl#path'))
            self.assertIn(r[2], s2)

    def test_update_query(self):
        query1 = self._context.sparql_context
        query1 += """
        INSERT DATA {
            GRAPH test:shacl {
                test:gaga a test:Gaga .
                test:gaga rdfs:label "GAGA"
            }
        }
        """
        self._connection.update_query(query1)
        qq1 = self._context.sparql_context
        qq1 += "SELECT ?o FROM test:shacl WHERE {test:gaga rdfs:label ?p}"
        res = self._connection.rdflib_query(qq1)
        self.assertEqual(len(res), 1)
        for r in res:
            self.assertEqual(r[0], "GAGA")
        query2 = self._context.sparql_context
        query2 += """
        DELETE {
            ?s rdfs:label ?o
        }
        INSERT {
            ?s rdfs:label "GUGUS"
        }
        WHERE {
            ?s a test:Gaga
        }
        """
        self._connection.update_query(query1)
        qq2 = self._context.sparql_context
        qq2 += "SELECT ?o FROM test:shacl WHERE {test:gaga rdfs:label ?p}"
        res = self._connection.rdflib_query(qq2)
        self.assertEqual(len(res), 1)
        for r in res:
            self.assertEqual(r[0], "GUGUS")


if __name__ == '__main__':
    unittest.main()
