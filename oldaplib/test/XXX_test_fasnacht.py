from oldaplib.src.connection import Connection
import unittest

from oldaplib.src.datamodel import DataModel
from oldaplib.src.project import Project

class TestDataModel(unittest.TestCase):

    # @unittest.skip('Work in progress')
    def test_fasnacht(self):
        connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        project = Project.read(connection, "fasnacht")
        dm = DataModel.read(connection, project, ignore_cache=False)
        pass
