from pathlib import Path
from pprint import pprint

from oldaplib.src.connection import Connection
import unittest

from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.helpers.construct_processor import ConstructProcessor
from oldaplib.src.helpers.context import Context
from oldaplib.src.project import Project
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.xsd_qname import Xsd_QName

def find_project_root(current_path):
    # Climb up the directory hierarchy and check for a marker file
    path = Path(current_path).absolute()
    while not (path / 'pyproject.toml').exists():
        if path.parent == path:
            # Root of the filesystem, file not found
            raise RuntimeError('Project root not found')
        path = path.parent
    return path


class TestKappa(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        project_root = find_project_root(__file__)

        cls._context = Context(name="DEFAULT")
        cls._context['ex'] = NamespaceIRI("https://example.com/")
        cls._context.use('test')

        cls._connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        cls._connection.clear_graph(Xsd_QName('ex:shacl'))
        cls._connection.clear_graph(Xsd_QName('ex:onto'))
        file = project_root / 'oldaplib' / 'testdata' / 'xxxx_kappa.trig'
        cls._connection.upload_turtle(str(file))
        cls._project = Project.read(cls._connection, "example")


    def test__read_shacl(self):
        connection = Connection(userId="rosenth",
                                credentials="RioGrande",
                                context_name="DEFAULT")

        shared = Project.read(connection, "shared")

        obj = ConstructProcessor.query_shacl(con=connection,
                                             project=shared,
                                             shape_iri=Xsd_QName('shared:MediaObject', validate=True))
        pprint(obj)

    def test_read_datamodel_shacl(self):
        connection = Connection(userId="rosenth",
                                credentials="RioGrande",
                                context_name="DEFAULT")

        shared = Project.read(connection, "shared")

        obj = ConstructProcessor.query_shacl(con=connection,
                                             project=shared)
        pprint(obj)

    def test_read_onto(self):
        connection = Connection(userId="rosenth",
                                credentials="RioGrande",
                                context_name="DEFAULT")

        shared = Project.read(connection, "shared")

        obj = ConstructProcessor.query_onto(con=connection,
                                             project=shared,
                                             class_iri=Xsd_QName('shared:MediaObject', validate=True))
        pprint(obj)

    def test_read_datamode_onto(self):
        connection = Connection(userId="rosenth",
                                credentials="RioGrande",
                                context_name="DEFAULT")

        shared = Project.read(connection, "shared")

        obj = ConstructProcessor.query_onto(con=connection,
                                             project=shared)
        pprint(obj)

    def test_read_shacl_resclass(self):
        connection = Connection(userId="rosenth",
                                credentials="RioGrande",
                                context_name="DEFAULT")

        shared = Project.read(connection, "shared")

        obj = ConstructProcessor.query_shacl(con=connection,
                                             project=shared,
                                             shape_iri=Xsd_QName('shared:MediaObject', validate=True))
        shaclobj = obj.get(Xsd_QName('shared:MediaObjectShape'))
        obj = ConstructProcessor.query_onto(con=connection,
                                            project=shared,
                                            class_iri=Xsd_QName('shared:MediaObject', validate=True))
        ontoobj = obj.get(Xsd_QName('shared:MediaObject'))
        print(shaclobj.get(Xsd_QName('sh:node')))
        print(ontoobj.get(Xsd_QName('rdfs:subClassOf')))

    def test_read_shacl_resclass2(self):
        connection = Connection(userId="rosenth",
                                credentials="RioGrande",
                                context_name="DEFAULT")

        obj = ConstructProcessor.query_shacl(con=connection,
                                             project=self._project)
                                             #shape_iri=Xsd_QName('ex:TestObj', validate=True))
        shaclobj = obj.get(Xsd_QName('example:TestObjShape'))
        obj = ConstructProcessor.query_onto(con=connection,
                                            project=self._project)
                                            #class_iri=Xsd_QName('ex:TestObj', validate=True))
        ontoobj = obj.get(Xsd_QName('example:TestObj'))

        print(shaclobj.get(Xsd_QName('sh:node')))
        print(ontoobj.get(Xsd_QName('rdfs:subClassOf')))

