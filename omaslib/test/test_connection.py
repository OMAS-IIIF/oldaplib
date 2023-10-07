import sys
import unittest
from os import getcwd

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import QName, NamespaceIRI
from omaslib.src.helpers.omaserror import OmasError


#sys.path.append("/Users/rosenth/ProgDev/OMAS/omaslib/omaslib")
#sys.path.append("omaslib")

class TestBasicConnection(unittest.TestCase):

    def test_basic_connection(self):
        con = Connection(server='http://localhost:7200',
                         repo="omas",
                         context_name="DEFAULT")
        self.assertIsInstance(con, Connection)
        self.assertEqual(con.server, 'http://localhost:7200')
        self.assertEqual(con.repo, 'omas')
        self.assertEqual(con.context_name, 'DEFAULT')
        with self.assertRaises(OmasError) as ex:
            con.server = 'http://exaample.org'
        self.assertEqual(ex.exception.message, 'Cannot change the server of a connection!')

        with self.assertRaises(OmasError) as ex:
            con.repo = 'gaga'
        self.assertEqual(ex.exception.message, 'Cannot change the repo of a connection!')

        with self.assertRaises(OmasError) as ex:
            con.context_name = 'GAGA'
        self.assertEqual(ex.exception.message, 'Cannot change the context name of a connection!')


    def test_upload_trig(self):
        context = Context(name="DEFAULT")
        context['test'] = NamespaceIRI("http://omas.org/test#")
        con = Connection(server='http://localhost:7200',
                         repo="omas",
                         context_name="DEFAULT")
        con.upload_turtle("omaslib/testdata/connection_test.trig")
        con.clear_graph(QName('test:shacl'))


class TestConnection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://omas.org/test#")

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     context_name="DEFAULT")
        cls._connection.upload_turtle("omaslib/testdata/connection_test.trig")
        print('+++++++++++++++++++++++++++++++++++')

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(QName('test:shacl'))
        print("------------------------------------")

    def test_query(self):
        query = self._context.sparql_context
        query += """
        SELECT ?s ?p ?o
        WHERE {
            ?s ?p ?o
        }
        """
        print(query)
        res = self._connection.query(query)
        print(res)

if __name__ == '__main__':
    unittest.main()
