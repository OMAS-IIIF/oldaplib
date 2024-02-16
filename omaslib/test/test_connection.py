import json
import unittest
from datetime import datetime, timezone
from pprint import pprint
from time import sleep
from typing import List

from rdflib import URIRef

from omaslib.src.connection import Connection, SparqlResultFormat
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import QName, NamespaceIRI, BNode, AnyIRI, NCName
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.query_processor import QueryProcessor, OmasStringLiteral
from omaslib.src.helpers.semantic_version import SemanticVersion


#sys.path.append("/Users/rosenth/ProgDev/OMAS/omaslib/omaslib")
#sys.path.append("omaslib")

class TestBasicConnection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://omas.org/test#")
        cls._context.use('test')

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     userId="rosenth",
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
                         userId="rosenth",
                         credentials="RioGrande",
                         context_name="DEFAULT")
        self.assertIsInstance(con, Connection)
        self.assertEqual(con.server, 'http://localhost:7200')
        self.assertEqual(con.repo, 'omas')
        self.assertEqual(con.context_name, 'DEFAULT')

        with self.assertRaises(OmasError) as ex:
            con = Connection(server='http://localhost:7200',
                             repo="omas",
                             userId="rosenth",
                             credentials="XXX",
                             context_name="DEFAULT")
        self.assertEqual(str(ex.exception), "Wrong credentials")

    def test_token(self):
        Connection.jwtkey = "This is a very special secret, yeah!"
        con = Connection(server='http://localhost:7200',
                         repo="omas",
                         userId="rosenth",
                         credentials="RioGrande",
                         context_name="DEFAULT")
        token = con.token
        con = Connection(server='http://localhost:7200',
                         repo="omas",
                         token=token,
                         context_name="DEFAULT")
        self.assertEqual(con.userid, NCName("rosenth"))
        self.assertEqual(con.userIri, AnyIRI("https://orcid.org/0000-0003-1681-4036"))

        with self.assertRaises(OmasError) as ex:
            con = Connection(server='http://localhost:7200',
                             repo="omas",
                             token=token + "X",
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
                              },
                             {'o': {'type': 'uri', 'value': 'http://omas.org/test#enum'},
                              's': {'type': 'uri', 'value': 'http://omas.org/test#enumShape'}
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
        self.assertEqual(len(res), 3)
        s0 = {
            URIRef('http://omas.org/test#commentShape'),
            URIRef('http://omas.org/test#testShape'),
            URIRef('http://omas.org/test#enumShape'),
        }
        s2 = {
            URIRef('http://omas.org/test#comment'),
            URIRef('http://omas.org/test#test'),
            URIRef('http://omas.org/test#enum'),
        }
        for r in res:
            self.assertIn(r[0], s0)
            self.assertIn(r[2], s2)

    #@unittest.skip('Work in progress')
    def test_json_query(self):
        expected = {
            QName('rdf:type'): {QName('test:testMyRes'), QName('sh:NodeShape')},
            QName("rdfs:comment"): "Resource for testing...",
            QName("rdfs:label"): {"My Resource@en", "Meine Ressource@de",  "Ma Resource@fr"},
            QName("sh:property"): QName("test:testShape"),
            QName("sh:closed"): True,
            QName("sh:targetClass"): QName("test:testMyRes"),
            QName("dcterms:hasVersion"): '1.0.0',
            QName("dcterms:creator"): AnyIRI("https://orcid.org/0000-0003-1681-4036"),
            QName("dcterms:created"): datetime(2023, 11, 4, 12, 0, tzinfo=timezone.utc),
            QName("dcterms:contributor"):  AnyIRI("https://orcid.org/0000-0003-1681-4036"),
            QName("dcterms:modified"): datetime(2023, 11, 4, 12, 0, tzinfo=timezone.utc)
        }
        query = self._context.sparql_context
        query += """
        SELECT ?prop ?value ?oo
        FROM test:shacl
        WHERE {
            test:testMyResShape ?prop ?value .
            OPTIONAL {
                ?value rdf:rest*/rdf:first ?oo
            }
        }
        """
        res = self._connection.query(query, format=SparqlResultFormat.JSON)
        result = QueryProcessor(self._context, res)
        for r in result:
            if isinstance(r['prop'], BNode) or isinstance(r['value'], BNode):
                continue
            if r['prop'] == 'rdfs:label':
                self.assertTrue(str(r['value']) in expected[r['prop']])
            elif r['prop'] == 'rdf:type':
                self.assertTrue(str(r['value']) in expected[r['prop']])
            else:
                self.assertEqual(r['value'], expected[r['prop']])

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
        query = self._context.sparql_context
        query += """
        INSERT DATA {
            GRAPH test:shacl {
                test:waseliwas a test:Waseliwas .
                test:waseliwas rdfs:label "WASELIWAS"
            }
        }
        """
        self._connection.update_query(query)

        self._connection.transaction_start()
        query = self._context.sparql_context
        query += """
        SELECT ?label
        WHERE {
            GRAPH test:shacl {
                ?obj a test:Waseliwas .
                ?obj rdfs:label ?label .
            }
        }
        """
        jsonobj = self._connection.transaction_query(query)
        res = QueryProcessor(self._context, jsonobj)
        self.assertEqual(len(res), 1)
        self.assertEqual(str(res[0]['label']), 'WASELIWAS')

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

        qq2 = self._context.sparql_context
        qq2 += "SELECT ?o FROM test:shacl WHERE {test:waseliwas rdfs:label ?o}"
        jsonobj = self._connection.transaction_query(qq2)
        res = QueryProcessor(self._context, jsonobj)
        for r in res:
            self.assertEqual(str(r['o']), "WASELIWAS ISCH DAS DENN AU?")

        self._connection.transaction_commit()

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
