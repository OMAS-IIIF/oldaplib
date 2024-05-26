import unittest
from datetime import datetime, timezone
from pathlib import Path
from time import sleep

from oldaplib.src.connection import Connection
from oldaplib.src.enums.sparql_result_format import SparqlResultFormat
from oldaplib.src.helpers.context import Context
from oldaplib.src.dtypes.bnode import BNode
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNotFound
from oldaplib.src.helpers.query_processor import QueryProcessor

def find_project_root(current_path):
    # Climb up the directory hierarchy and check for a marker file
    path = Path(current_path).absolute()
    while not (path / 'pyproject.toml').exists():
        if path.parent == path:
            # Root of the filesystem, file not found
            raise RuntimeError('Project root not found')
        path = path.parent
    return path


class TestBasicConnection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        project_root = find_project_root(__file__)
        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://oldap.org/test#")
        cls._context.use('test')

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="oldap",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        file = project_root / 'oldaplib' / 'testdata' / 'connection_test.trig'

        cls._connection.upload_turtle(file)
        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(QName('test:shacl'))
        #cls._connection.clear_graph(QName('test:onto'))
        pass

    def test_basic_connection(self):
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         userId="rosenth",
                         credentials="RioGrande",
                         context_name="DEFAULT")
        self.assertIsInstance(con, Connection)
        self.assertEqual(con.server, 'http://localhost:7200')
        self.assertEqual(con.repo, 'oldap')
        self.assertEqual(con.context_name, 'DEFAULT')

    def test_basic_connection_wrong_credentials(self):
        with self.assertRaises(OldapError) as ex:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             userId="rosenth",
                             credentials="XXX",
                             context_name="DEFAULT")
        self.assertEqual(str(ex.exception), "Wrong credentials")

    def test_basic_connection_unknown_user(self):
        with self.assertRaises(OldapErrorNotFound) as ex:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             userId="XXX",
                             credentials="RioGrande",
                             context_name="DEFAULT")
        self.assertEqual(str(ex.exception), "Given user not found!")

    def test_inactive_user(self):
        with self.assertRaises(OldapError) as ex:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             userId="bugsbunny",
                             credentials="DuffyDuck",
                             context_name="DEFAULT")
        self.assertEqual(str(ex.exception), "Wrong credentials")

    def test_basic_connection_injection_userid(self):
        with self.assertRaises(OldapError) as ex:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             userId="rosenth \". #\n; SELECT * {?s ?p ?o}",
                             credentials="RioGrande",
                             context_name="DEFAULT")
        self.assertEqual(str(ex.exception), 'Invalid string "rosenth ". #\n; SELECT * {?s ?p ?o}" for NCName')

    def test_basic_connection_injection_credentials(self):
        with self.assertRaises(OldapError) as ex:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             userId="rosenth",
                             credentials="RioGrande \". #\n; SELECT * {?s ?p ?o};",
                             context_name="DEFAULT")
        self.assertEqual(str(ex.exception), 'Wrong credentials')

    def test_token(self):
        Connection.jwtkey = "This is a very special secret, yeah!"
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         userId="rosenth",
                         credentials="RioGrande",
                         context_name="DEFAULT")
        token = con.token
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         token=token,
                         context_name="DEFAULT")
        self.assertEqual(con.userid, Xsd_NCName("rosenth"))
        self.assertEqual(con.userIri, Xsd_anyURI("https://orcid.org/0000-0003-1681-4036"))

        with self.assertRaises(OldapError) as ex:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
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
                'bindings': [{'o': {'type': 'uri', 'value': 'http://oldap.org/test#comment'},
                              's': {'type': 'uri', 'value': 'http://oldap.org/test#commentShape'}
                              },
                             {'o': {'type': 'uri', 'value': 'http://oldap.org/test#test'},
                              's': {'type': 'uri', 'value': 'http://oldap.org/test#testShape'}
                              },
                             {'o': {'type': 'uri', 'value': 'http://oldap.org/test#enum'},
                              's': {'type': 'uri', 'value': 'http://oldap.org/test#enumShape'}
                              }]
            }
        }
        self.maxDiff = None
        self.assertDictEqual(res, expected)

    #@unittest.skip('Work in progress')
    def test_json_query(self):
        expected = {
            Iri('rdf:type'): {Iri('test:testMyRes'), Iri('sh:NodeShape')},
            Iri("rdfs:comment"): "Resource for testing...",
            Iri("rdfs:label"): {"My Resource@en", "Meine Ressource@de", "Ma Resource@fr"},
            Iri("sh:property"): Xsd_QName("test:testShape"),
            Iri("sh:closed"): Xsd_boolean(True),
            Iri("sh:targetClass"): Xsd_QName("test:testMyRes"),
            Iri("dcterms:hasVersion"): '1.0.0',
            Iri("dcterms:creator"): Iri("https://orcid.org/0000-0003-1681-4036"),
            Iri("dcterms:created"): Xsd_dateTime(datetime(2023, 11, 4, 12, 0, tzinfo=timezone.utc)),
            Iri("dcterms:contributor"):  Iri("https://orcid.org/0000-0003-1681-4036"),
            Iri("dcterms:modified"): Xsd_dateTime(datetime(2023, 11, 4, 12, 0, tzinfo=timezone.utc))
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
                self.assertTrue(r['value'] in expected[r['prop']])
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
        jsonres = self._connection.query(qq1)
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 1)
        for r in res:
            self.assertEqual(str(r['o']), "GAGA")
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
        jsonres = self._connection.query(qq2)
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 1)
        for r in res:
            self.assertEqual(str(r['o']), "GUGUS")

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
        jsonres = self._connection.query(qq2)
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 1)
        for r in res:
            self.assertEqual(str(r['o']), "WASELIWAS ISCH DAS DENN AU?")

    def test_context(self):
        context = Context(name=self._connection.context_name)
        self.assertEqual("http://oldap.org/base#", self._context['oldap'])
        self.assertEqual("http://hyperhamlet.unibas.ch/", self._context['hyha'])


if __name__ == '__main__':
    unittest.main()
