import json
import unittest
from pprint import pprint
from time import sleep

from rdflib import URIRef, BNode

from omaslib.src.connection import Connection, SparqlResultFormat
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

        cls._connection.clear_graph(QName('test:shacl'))
        cls._connection.clear_graph(QName('test:onto'))
        cls._connection.upload_turtle("omaslib/testdata/connection_test.trig")
        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(QName('test:shacl'))
        #cls._connection.clear_graph(QName('test:onto'))
        pass

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

    #@unittest.skip('Has to be adapted to test data...')
    def test_query(self):
        query = self._context.sparql_context
        query += """
        SELECT ?s ?o
        FROM test:shacl
        WHERE {
            ?s a sh:PropertyShape .
            ?s sh:path ?o .
        }
        """
        res = self._connection.query(query)
        expected = {
            'head': {
                'vars': ['s', 'o']
            },
            'results': {
                'bindings': [{'o': {'type': 'uri', 'value': 'http://omas.org/test#comment'},
                              's': {'type': 'uri', 'value': 'http://omas.org/test#commentShape'}
                              },
                             {'o': {'type': 'uri', 'value': 'http://omas.org/test#test'},
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
    		?s rdf:type ?p .
            ?s sh:path ?o .
        }
        """
        p = URIRef(str(self._context.qname2iri('sh:PropertyShape')))
        res = self._connection.rdflib_query(query, {'p': p})
        self.assertEqual(len(res), 2)
        s0 = {
            URIRef('http://omas.org/test#commentShape'),
            URIRef('http://omas.org/test#testShape'),
        }
        s2 = {
            URIRef('http://omas.org/test#comment'),
            URIRef('http://omas.org/test#test'),
        }
        for r in res:
            self.assertIn(r[0], s0)
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
        qq1 += "SELECT ?o FROM test:shacl WHERE {test:gaga rdfs:label ?o}"
        res = self._connection.rdflib_query(qq1)
        self.assertEqual(len(res), 1)
        for r in res:
            self.assertEqual(str(r[0]), "GAGA")
        query2 = self._context.sparql_context
        query2 += """
        DELETE {
            GRAPH test:shacl {
                ?s rdfs:label ?o
            }
        }
        INSERT {
            GRAPH test:shacl {
                ?s rdfs:label "GUGUS"
            }
        }
        WHERE {
            ?s a test:Gaga .
            ?s rdfs:label ?o .
        }
        """
        self._connection.update_query(query2)
        qq2 = self._context.sparql_context
        qq2 += "SELECT ?o FROM test:shacl WHERE {test:gaga rdfs:label ?o}"
        res = self._connection.rdflib_query(qq2)
        self.assertEqual(len(res), 1)
        for r in res:
            self.assertEqual(str(r[0]), "GUGUS")

    def test_transaction(self):
        self._connection.transaction_start()
        query1 = self._context.sparql_context
        query1 += """
        INSERT DATA {
            GRAPH test:shacl {
                test:waseliwas a test:Waseliwas .
                test:waseliwas rdfs:label "WASELIWAS"
            }
        }
        """
        self._connection.transaction_update(query1)
        query2 = self._context.sparql_context
        query2 += """
        DELETE {
            GRAPH test:shacl {
                ?s rdfs:label ?o
            }
        }
        INSERT {
            GRAPH test:shacl {
                ?s rdfs:label "WASELIWAS ISCH DAS DENN AU?"
            }
        }
        WHERE {
            ?s a test:Waseliwas .
            ?s rdfs:label ?o .
        }
        """
        self._connection.transaction_update(query2)
        self._connection.transaction_commit()

        qq2 = self._context.sparql_context
        qq2 += "SELECT ?o FROM test:shacl WHERE {test:waseliwas rdfs:label ?o}"
        res = self._connection.rdflib_query(qq2)
        self.assertEqual(len(res), 1)
        for r in res:
            self.assertEqual(str(r[0]), "WASELIWAS ISCH DAS DENN AU?")

        self._connection.transaction_start()
        query3 = self._context.sparql_context
        query3 += """
        DELETE {
            GRAPH test:shacl {
                ?s rdfs:label ?o
            }
        }
        INSERT {
            GRAPH test:shacl {
                ?s rdfs:label "SHOULD NOT BE CHANGED"
            }
        }
        WHERE {
            ?s a test:Waseliwas .
            ?s rdfs:Label ?o .
        }
        """
        self._connection.transaction_update(query3)

        qq2a = self._context.sparql_context
        qq2a += "SELECT ?o FROM test:shacl WHERE {test:waseliwas rdfs:label ?o}"
        res = self._connection.transaction_query(qq2a, SparqlResultFormat.JSON)
        self.assertEqual(res['results']['bindings'][0]['o']['value'], "WASELIWAS ISCH DAS DENN AU?")

        self._connection.transaction_abort()
        qq3 = self._context.sparql_context
        qq3 += "SELECT ?o FROM test:shacl WHERE {test:waseliwas rdfs:label ?o}"
        res = self._connection.rdflib_query(qq2)
        self.assertEqual(len(res), 1)
        for r in res:
            self.assertEqual(str(r[0]), "WASELIWAS ISCH DAS DENN AU?")


if __name__ == '__main__':
    unittest.main()
