import unittest
from time import sleep

from omaslib.src.connection import Connection
from omaslib.src.datamodel import DataModel
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName


class TestDataModel(unittest.TestCase):
    _context: Context
    _connection: Connection

    @classmethod
    def setUp(cls):
        cls._context = Context(name="DEFAULT")

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     userid="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        #cls._connection.clear_graph(QName('test:shacl'))
        #cls._connection.clear_graph(QName('test:onto'))
        #cls._connection.upload_turtle("omaslib/testdata/connection_test.trig")
        sleep(1)  # upload may take a while...

    def tearDown(self):
        pass

    def test_datamodel_constructor(self):
        pass

    def test_datamodel_read(self):
        model = DataModel.read(self._connection, "omas")
        print(model.get_propclasses())
        print(model.get_resclasses())


