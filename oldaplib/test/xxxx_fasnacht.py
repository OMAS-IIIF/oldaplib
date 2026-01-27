from pprint import pprint

from oldaplib.src.connection import Connection
import unittest

from oldaplib.src.datamodel import DataModel
from oldaplib.src.project import Project

class TestDataModel(unittest.TestCase):

    #@unittest.skip('Work in progress')
    def test_fasnacht(self):
        connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        dm = DataModel.read(connection, "fasnacht", ignore_cache=False)
        pass

    def test_datamodel_read_shared(self):
        connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        model = DataModel.read(connection, 'shared')
        pp = model.get_propclasses()
        for p in pp:
            print(model[p])
        model = DataModel.read(connection, 'shared', ignore_cache=True)
        pp = model.get_propclasses()
        for p in pp:
            print(model[p])
