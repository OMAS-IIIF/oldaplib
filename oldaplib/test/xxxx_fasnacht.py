from pprint import pprint

from oldaplib.src.connection import Connection
import unittest

from oldaplib.src.datamodel import DataModel
from oldaplib.src.helpers.context import Context
from oldaplib.src.project import Project
from oldaplib.src.objectfactory import ResourceInstanceFactory, ResourceInstance, SortBy, SortDir, FTSearchFilter, \
    LogicOp, SearchFilter, CompOp
from oldaplib.src.xsd.xsd_qname import Xsd_QName


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

    def test_combined_search(self):
        con = Connection(userId="rosenth",
                         credentials="RioGrande",
                         context_name="DEFAULT")
        searchstr = 'Gluggsi'
        res = ResourceInstance.search(con=con,
                                      project='fasnacht',
                                      ftfilter=[FTSearchFilter(field='archiveObjectDescription', query=searchstr),
                                                'OR',
                                                FTSearchFilter(field='representedArchiveObjectDescription', query=searchstr)])
        pprint(res)

    def test_read_instance(self):
        con = Connection(userId="rosenth",
                         credentials="RioGrande",
                         context_name="DEFAULT")
        project = Project.read(con, 'dmtest')
        dm = DataModel.read(con=con, project=project)
        context = Context(name=con.context_name)
        factory = ResourceInstanceFactory(con=con, project='dmtest')
        instance = factory.read('urn:uuid:32abf755-2b5b-4e06-8a83-92fd1610489b')
        # urn:uuid:ba81f700-8f07-4969-824b-30b080acf5a3
        print(instance)

    def test_search_not_exists(self):
        con = Connection(userId="rosenth",
                         credentials="RioGrande",
                         context_name="DEFAULT")
        res = ResourceInstance.search(con=con,
                                      project='fasnacht',
                                      filter=[SearchFilter(prop=Xsd_QName('fasnacht:externalSource'),
                                                           op=CompOp.NOT_EXISTS,
                                                           value=Xsd_QName('fasnacht:externalSource'))])
        pprint(res)
