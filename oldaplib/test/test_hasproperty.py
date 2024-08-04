import unittest
from pathlib import Path
from time import sleep

from oldaplib.src.connection import Connection
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_integer import Xsd_integer
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


class TestHasProperty(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        project_root = find_project_root(__file__)

        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://oldap.org/test#")
        cls._context.use('test', 'dcterms')

        cls._connection = Connection(server='http://localhost:7200',
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     repo="oldap",
                                     context_name="DEFAULT")

        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        cls._connection.clear_graph(Xsd_QName('dcterms:shacl'))
        cls._connection.clear_graph(Xsd_QName('dcterms:onto'))

        file = project_root / 'oldaplib' / 'testdata' / 'connection_test.trig'
        cls._connection.upload_turtle(file)
        sleep(1)  # upload may take a while...
        cls._project = Project.read(cls._connection, "test")

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(QName('test:shacl'))
        #cls._connection.clear_graph(QName('test:onto'))
        pass

    def test_creation(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:hasprop_test_A'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["HasPropTest A"]))
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, prop=p1, minCount=1, maxCount=1, group=Iri('test:group'), order=1),
            HasProperty(con=self._connection, prop=Iri("test:comment"), maxCount=1, group=Iri('test:group'), order=2),
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:HasPropertyTest_A"),
                           superclass={'oldap:Thing', 'http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object'},
                           label=LangString(["HAsProptestA@en", "PropeTesteA@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()

        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:HasPropertyTest_A"))
        self.assertEqual(r1[Iri('test:hasprop_test_A')].minCount, Xsd_integer(1))
        self.assertEqual(r1[Iri('test:hasprop_test_A')].maxCount, Xsd_integer(1))
        self.assertEqual(r1[Iri('test:hasprop_test_A')].order, Xsd_decimal(1))
        self.assertEqual(r1[Iri('test:hasprop_test_A')].group, Iri('test:group'))

        self.assertIsNone(r1[Iri("test:comment")].minCount)
        self.assertEqual(r1[Iri("test:comment")].maxCount, Xsd_integer(1))
        self.assertEqual(r1[Iri("test:comment")].order, Xsd_decimal(2))
        self.assertEqual(r1[Iri("test:comment")].group, Iri('test:group'))

    def test_modification_replace(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:hasprop_test_B'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["HasPropTest B"]))
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, prop=p1, minCount=1, maxCount=1, group=Iri('test:group'), order=1),
            HasProperty(con=self._connection, prop=Iri("test:comment"), maxCount=1, group=Iri('test:group'), order=2),
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:HasPropertyTest_B"),
                           superclass={'oldap:Thing', 'http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object'},
                           label=LangString(["HasProptestB@en", "PropeTesteB@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()

        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:HasPropertyTest_B"))
        r1[Iri('test:hasprop_test_B')].maxCount = Xsd_integer(2)
        r1[Iri('test:hasprop_test_B')].order = Xsd_decimal(2)
        r1[Iri('test:hasprop_test_B')].group = Iri('test:groupB')

        r1[Iri('test:comment')].maxCount = Xsd_integer(2)
        r1[Iri('test:comment')].order = Xsd_decimal(1)
        r1[Iri('test:comment')].group = Iri('test:groupB')

        r1.update()
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:HasPropertyTest_B"))
        self.assertEqual(Xsd_integer(2), r1[Iri('test:hasprop_test_B')].maxCount)
        self.assertEqual(Xsd_decimal(2), r1[Iri('test:hasprop_test_B')].order)
        self.assertEqual(Iri('test:groupB'), r1[Iri('test:hasprop_test_B')].group)

        self.assertEqual(Xsd_integer(2), r1[Iri('test:comment')].maxCount)
        self.assertEqual(Xsd_decimal(1), r1[Iri('test:comment')].order)
        self.assertEqual(Iri('test:groupB'), r1[Iri('test:comment')].group)

    def test_modification_add(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:hasprop_test_C'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["HasPropTest C"]))
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, prop=p1, minCount=1, order=1),
            HasProperty(con=self._connection, prop=Iri("test:comment"), maxCount=1, group=Iri('test:group')),
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:HasPropertyTest_C"),
                           superclass={'oldap:Thing', 'http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object'},
                           label=LangString(["HasProptestC@en", "PropeTesteC@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()

        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:HasPropertyTest_C"))
        r1[Iri('test:hasprop_test_C')].maxCount = Xsd_integer(10)
        #r1[Iri('test:hasprop_test_C')].group = Iri('test:group')
        #r1[Iri("test:comment")].minCount = Xsd_integer(1)
        #r1[Iri("test:comment")].order = Xsd_decimal(1)
        r1.update()
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:HasPropertyTest_C"))
        self.assertEqual(Xsd_integer(10), r1[Iri('test:hasprop_test_C')].maxCount)
        #self.assertEqual(Iri('test:group'), r1[Iri('test:hasprop_test_C')].group)
        #self.assertEqual(Xsd_integer(1), r1[Iri("test:comment")].minCount)
        #self.assertEqual(Xsd_decimal(1), r1[Iri("test:comment")].order)

    def test_modification_delete(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:hasprop_test_D'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["HasPropTest D"]))
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, prop=p1, minCount=1, maxCount=1, group=Iri('test:group'), order=1),
            HasProperty(con=self._connection, prop=Iri("test:comment"), maxCount=1, group=Iri('test:group'), order=2),
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:HasPropertyTest_D"),
                           superclass={'oldap:Thing', 'http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object'},
                           label=LangString(["HasProptestC@en", "PropeTesteC@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()

        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:HasPropertyTest_D"))
        del r1[Iri('test:hasprop_test_D')].maxCount
        del r1[Iri('test:hasprop_test_D')].order
        del r1[Iri('test:comment')].maxCount
        del r1[Iri('test:comment')].group
        del r1[Iri('test:comment')].order
        r1.update()

        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:HasPropertyTest_D"))
        self.assertIsNone(r1[Iri('test:hasprop_test_D')].maxCount)
        self.assertIsNone(r1[Iri('test:hasprop_test_D')].order)
        self.assertIsNone(r1[Iri('test:comment')].maxCount)
        self.assertIsNone(r1[Iri('test:comment')].group)
        self.assertIsNone(r1[Iri('test:comment')].order)



if __name__ == '__main__':
    unittest.main()
