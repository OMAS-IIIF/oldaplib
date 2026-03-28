from pprint import pprint

from oldaplib.src.connection import Connection
import unittest

from oldaplib.src.datamodel import DataModel
from oldaplib.src.project import Project
from oldaplib.src.objectfactory import ResourceInstanceFactory, ResourceInstance, SortBy, SortDir


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


    def test_gaga(self):
        con = Connection(userId="rosenth",
                         credentials="RioGrande",
                         context_name="DEFAULT")
        # dm = DataModel.read(con=con, project='fasnacht')
        # factory = ResourceInstanceFactory(con=con, project='fasnacht')
        # NE = factory.createObjectInstance('fasnacht:NewsItem')
        res = ResourceInstance.search_fulltext(con,
                                               projectShortName='fasnacht',
                                               searchstr="neue",
                                               sortBy=[SortBy('oldap:creationDate', SortDir.desc)])
        print(res)

    def test_media_obj(self):
        con = Connection(userId="rosenth",
                         credentials="RioGrande",
                         context_name="DEFAULT")
        mo = ResourceInstance.get_media_object_by_id(con, "Io0W1LabrnUk")
        print(mo)

    def test_all_newsitems(self):
        con = Connection(userId="rosenth",
                         credentials="RioGrande",
                         context_name="DEFAULT"
        )
        res = ResourceInstance.all_resources(con=con,
                                             projectShortName="fasnacht",
                                             resClass="fasnacht:NewsItem",
                                             sortBy=[SortBy('fasnacht:newsItemStartDate', SortDir.desc)]
                                             )
        pprint(res)
