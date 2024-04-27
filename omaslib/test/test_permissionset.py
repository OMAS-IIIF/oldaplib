import unittest
from time import sleep

from omaslib.src.PermissionSet import PermissionSet
from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_qname import Xsd_QName


class TestPermissionSet(unittest.TestCase):
    _connection: Connection
    _unpriv: Connection

    @classmethod
    def setUpClass(cls):
        cls._context = Context(name="DEFAULT")

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._unpriv = Connection(server='http://localhost:7200',
                                 repo="omas",
                                 userId="fornaro",
                                 credentials="RioGrande",
                                 context_name="DEFAULT")

        cls._connection.clear_graph(Xsd_QName('omas:admin'))
        cls._connection.upload_turtle("omaslib/ontologies/admin.trig")
        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(Xsd_QName('omas:admin'))
        #cls._connection.upload_turtle("omaslib/ontologies/admin.trig")
        #sleep(1)  # upload may take a while...
        pass

    def test_something(self):
        ps = PermissionSet.read(self._connection, Iri('omas:GenericView'))

        self.assertEqual(ps.givesPermission, False)  # add assertion here


if __name__ == '__main__':
    unittest.main()
