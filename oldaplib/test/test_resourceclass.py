"""
Test data
"""
import unittest
from enum import Enum
from pathlib import Path
from time import sleep

from oldaplib.src.connection import Connection
from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.dtypes.rdfset import RdfSet
from oldaplib.src.enums.language import Language
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.enums.resourceclassattr import ResClassAttribute
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorAlreadyExists
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.semantic_version import SemanticVersion
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropClassAttrContainer, PropertyClass, OwlPropertyType
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string


class Graph(Enum):
    ONTO = 'test:onto'
    SHACL = 'test:shacl'


def check_prop_empty(con: Connection, context: Context, graph: Graph, res: str, prop: str) -> bool:
    sparql = context.sparql_context
    if graph == Graph.SHACL:
        sparql += f"""
        SELECT ?p ?v ?pp ?oo
        FROM {graph.value}
        WHERE {{
            {res}Shape sh:property ?prop .
            ?prop sh:path {prop} .
            ?prop ?p ?v .
            OPTIONAL {{ ?v ?pp ?oo }}
        }}
        """
    else:
        sparql += f"""
        SELECT ?p ?v ?pp ?oo
        FROM {graph.value}
        WHERE {{
            {res} rdfs:subClassOf ?prop .
            ?prop owl:onProperty test:propB .
            ?prop ?p ?v .
            OPTIONAL {{ ?v ?pp ?oo }}
        }}
        """
    jsonres = con.query(sparql)
    res = QueryProcessor(context, jsonres)
    return len(res) == 0

def check_res_empty(con: Connection, context: Context, graph: Graph, res: str) -> bool:
    sparql = context.sparql_context
    if graph == Graph.SHACL:
        res += 'Shape'
    sparql += f"""
    SELECT ?p ?v ?pp ?oo
    FROM {graph.value}
    WHERE {{
        {res} ?p ?v .
        OPTIONAL {{ ?v ?pp ?oo }}
    }}
    """
    jsonres = con.query(sparql)
    res = QueryProcessor(context, jsonres)
    return len(res) == 0


def find_project_root(current_path):
    # Climb up the directory hierarchy and check for a marker file
    path = Path(current_path).absolute()
    while not (path / 'pyproject.toml').exists():
        if path.parent == path:
            # Root of the filesystem, file not found
            raise RuntimeError('Project root not found')
        path = path.parent
    return path


class TestResourceClass(unittest.TestCase):
    _context: Context
    _connection: Connection

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

    # @unittest.skip('Work in progress')
    def test_constructor(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:testprop'),
                           subPropertyOf=Iri('test:comment'),
                           datatype=XsdDatatypes.langString,
                           name=LangString(["Test property@en", "Testprädikat@de"]),
                           description=LangString("A property for testing...@en"),
                           maxCount=Xsd_integer(1),
                           uniqueLang=Xsd_boolean(True),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                           order=Xsd_decimal(5))

        p2 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:enumprop'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["Test enum@en", "Enumerationen@de"]),
                           maxCount=Xsd_integer(1),
                           minCount=Xsd_integer(1),
                           inSet=RdfSet(Xsd_string("yes"), Xsd_string("maybe"), Xsd_string("no")),
                           order=Xsd_decimal(6))

        properties: list[PropertyClass | Iri] = [
            Iri("test:comment"),
            Iri("test:test"),
            p1, p2
        ]

        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:TestResource"),
                           label=LangString(["Test resource@en", "Resource de test@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           properties=properties)
        self.assertEqual(r1[ResClassAttribute.LABEL], LangString(["Test resource@en", "Resource de test@fr"]))
        self.assertEqual(r1.label, LangString(["Test resource@en", "Resource de test@fr"]))
        self.assertEqual(r1[ResClassAttribute.COMMENT], LangString("For testing purposes@en"))
        self.assertEqual(r1.comment, LangString("For testing purposes@en"))
        self.assertTrue(r1[ResClassAttribute.CLOSED])
        self.assertTrue(r1.closed)

        prop1 = r1[Iri("test:comment")]
        self.assertIsNotNone(prop1)
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, Iri("test:comment"))
        self.assertEqual(prop1.datatype, XsdDatatypes.langString)
        self.assertEqual(prop1.name, LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(prop1.description, LangString("This is a test property@de"))
        self.assertEqual(prop1.maxCount, Xsd_integer(1))
        self.assertEqual(prop1.uniqueLang, Xsd_boolean(True))

        prop2 = r1[Iri("test:test")]
        self.assertIsNone(prop2.internal)
        self.assertEqual(prop2.property_class_iri, Iri("test:test"))
        self.assertEqual(prop2.datatype, XsdDatatypes.string)
        self.assertEqual(prop2.description, LangString("Property shape for testing purposes"))
        self.assertEqual(prop2.minCount, Xsd_integer(1))
        self.assertEqual(prop2.order, Xsd_decimal(3))

        prop3 = r1[Iri("test:testprop")]
        self.assertEqual(prop3.internal, Iri('test:TestResource'))
        self.assertEqual(prop3.property_class_iri, Iri("test:testprop"))
        self.assertEqual(prop3.propertyType, OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop3.datatype, XsdDatatypes.langString)
        self.assertEqual(prop3.name, LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(prop3.order, Xsd_decimal(5))
        self.assertEqual(prop3.subPropertyOf, Iri("test:comment"))
        self.assertEqual(prop3.maxCount, Xsd_integer(1))
        self.assertEqual(prop3.uniqueLang,  Xsd_boolean(True))
        self.assertEqual(prop3.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        prop4 = r1[Iri("test:enumprop")]
        self.assertEqual(prop4[PropClassAttr.IN],
                         RdfSet(Xsd_string("yes"), Xsd_string("maybe"), Xsd_string("no")))

    # @unittest.skip('Work in progress')
    def test_reading(self):
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri('test:testMyRes'))
        self.assertEqual(r1.owl_class_iri, Iri('test:testMyRes'))
        self.assertEqual(r1.version, SemanticVersion(1, 0, 0))
        self.assertEqual(r1.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(r1.created, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(r1.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(r1.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(r1.label, LangString(["My Resource@en", "Meine Ressource@de", "Ma Resource@fr"]))
        self.assertEqual(r1.comment, LangString("Resource for testing..."))
        self.assertTrue(r1.closed)

        prop1 = r1[Iri('test:test')]
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, Iri("test:test"))
        self.assertEqual(prop1.version, SemanticVersion(1, 0, 0))
        self.assertEqual(prop1.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop1.created, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop1.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop1.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop1.propertyType, OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop1.datatype, XsdDatatypes.string)
        self.assertEqual(prop1.description, LangString("Property shape for testing purposes"))
        self.assertEqual(prop1.minCount, Xsd_integer(1))
        self.assertEqual(prop1.order, Xsd_decimal(3))

        prop2 = r1[Iri('test:hasText')]
        self.assertEqual(prop2.internal, Iri('test:testMyRes'))
        self.assertEqual(prop2.property_class_iri, Iri("test:hasText"))
        self.assertEqual(prop2.version, SemanticVersion(1, 0, 0))
        self.assertEqual(prop2.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop2.created, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop2.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop2.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop2.propertyType, OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop2.datatype, XsdDatatypes.langString)
        self.assertEqual(prop2.name, LangString(["A text@en", "Ein Text@de"]))
        self.assertEqual(prop2.description, LangString("A longer text..."))
        self.assertEqual(prop2.order, Xsd_decimal(1))
        self.assertEqual(prop2.minCount, Xsd_integer(1))
        self.assertEqual(prop2.maxCount, Xsd_integer(1))

        prop3 = r1[Iri('test:hasEnum')]
        self.assertEqual(prop3.propertyType, OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop3.datatype, XsdDatatypes.string)
        self.assertEqual(prop3.inSet,
                         RdfSet(Xsd_string('red'), Xsd_string('green'), Xsd_string('blue'), Xsd_string('yellow')))

    def test_reading_with_superclass(self):
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri('test:testMyResInherit'))
        self.assertEqual(r1.owl_class_iri, Iri('test:testMyResInherit'))
        self.assertEqual({Iri('test:testMyResMinimal')}, {x for x in r1.superclass})

    # @unittest.skip('Work in progress')
    def test_creating(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:testone'),
                           subPropertyOf=Iri('test:comment'),
                           datatype=XsdDatatypes.langString,
                           name=LangString(["Test property@en", "Testprädikat@de"]),
                           description=LangString("A property for testing...@en"),
                           minCount=Xsd_integer(1),
                           maxCount=Xsd_integer(1),
                           uniqueLang=Xsd_boolean(True),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                           order=Xsd_decimal(1))

        p2 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:testtwo'),
                           toNodeIri=Iri('test:testMyRes'),
                           name=LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]),
                           description=LangString("An exclusive property for testing...@en"),
                           minCount=Xsd_integer(1),
                           order=Xsd_decimal(2))

        p3 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:testthree'),
                           datatype=XsdDatatypes.int,
                           name=LangString(["E.N.U.M@en"]),
                           description=LangString("An exclusive enum testing...@en"),
                           inSet=RdfSet(Xsd_integer(1), Xsd_integer(2), Xsd_integer(3)),
                           order=Xsd_decimal(3))

        properties: list[PropertyClass | Iri] = [
            Iri("test:comment"),
            Iri("test:test"),
            p1, p2, p3
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:TestResource"),
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           properties=properties)

        r1.create()

        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:TestResource"))
        self.assertEqual(r2.owl_class_iri, Xsd_QName("test:TestResource"))
        self.assertEqual(r2.label, LangString(["CreateResTest@en", "CréationResTeste@fr"]))
        self.assertEqual(r2.comment, LangString("For testing purposes@en"))
        self.assertTrue(r2.closed)

        prop1 = r2[Iri("test:comment")]
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, Iri('test:comment'))
        self.assertEqual(prop1.datatype, XsdDatatypes.langString)
        self.assertTrue(prop1.uniqueLang)
        self.assertEqual(prop1.maxCount, Xsd_integer(1))
        self.assertEqual(prop1.name, LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(prop1.description, LangString("This is a test property@de"))
        self.assertIsNone(prop1.subPropertyOf)
        self.assertEqual(prop1.order, Xsd_decimal(2))
        self.assertEqual(prop1.propertyType, OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop1.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop1.created, Xsd_dateTime("2023-11-04T12:00:00Z"))

        prop2 = r2[Iri("test:test")]
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop2.property_class_iri, Iri('test:test'))
        self.assertEqual(prop2.minCount, Xsd_integer(1))
        self.assertEqual(prop2.name, LangString("Test"))
        self.assertEqual(prop2.description, LangString("Property shape for testing purposes"))
        self.assertEqual(prop2.datatype, XsdDatatypes.string)
        self.assertEqual(prop2.order, Xsd_decimal(3))
        self.assertEqual(prop2.propertyType, OwlPropertyType.OwlDataProperty)

        prop3 = r2[Iri("test:testone")]
        self.assertEqual(prop3.internal, Iri("test:TestResource"))
        self.assertEqual(prop3.property_class_iri, Iri("test:testone"))
        self.assertEqual(prop3.datatype, XsdDatatypes.langString)
        self.assertEqual(prop3.name, LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(prop3.description, LangString("A property for testing...@en"))
        self.assertEqual(prop3.maxCount, Xsd_integer(1))
        self.assertEqual(prop3.minCount, Xsd_integer(1))
        self.assertEqual(prop3.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(prop3.uniqueLang)
        self.assertEqual(prop3.order, Xsd_decimal(1))

        prop4 = r2[Iri("test:testtwo")]
        self.assertEqual(prop4.internal, Iri("test:TestResource"))
        self.assertEqual(prop4.property_class_iri, Iri("test:testtwo"))
        self.assertEqual(prop4.toNodeIri, Iri('test:testMyRes'))
        self.assertEqual(prop4.name, LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]))
        self.assertEqual(prop4.description, LangString("An exclusive property for testing...@en"))
        self.assertEqual(prop4.minCount, Xsd_integer(1))
        self.assertEqual(prop4.order, Xsd_decimal(2))

        prop5 = r2[Iri("test:testthree")]
        self.assertEqual(prop5.inSet, RdfSet(Xsd_integer(1), Xsd_integer(2), Xsd_integer(3)))

    def test_creating_with_superclass(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:sctest_prop1'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["TestProp1"]),
                           order=Xsd_decimal(1))
        properties: list[PropertyClass | Iri] = [ p1 ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:ResWithSuperclasses"),
                           superclass={"test:testMyResMinimal", 'http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object'},
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           properties=properties)
        r1.create()
        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri('test:ResWithSuperclasses'))
        s = set(r2.superclass.keys())
        self.assertEqual({"test:testMyResMinimal", 'http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object'}, s)

    def test_creating_with_thing_sc(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:thingtest_prop1'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["ThingTestProp1"]),
                           order=Xsd_decimal(1))
        properties: list[PropertyClass | Iri] = [ p1 ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:ResWithSuperThing"),
                           superclass={'oldap:Thing', 'http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object'},
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           properties=properties)
        r1.create()
        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri('test:ResWithSuperThing'))
        s = set(r2.superclass.keys())
        self.assertEqual({'oldap:Thing', Iri('http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object')}, s)

    # @unittest.skip('Work in progress')
    def test_double_creation(self):
        properties: list[PropertyClass | Iri] = [
            Iri("test:comment"),
            Iri("test:test"),
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:testMyResMinimal"),
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           properties=properties)

        with self.assertRaises(OldapErrorAlreadyExists) as ex:
            r1.create()
        self.assertEqual(str(ex.exception), 'Object "test:testMyResMinimal" already exists.')

    # @unittest.skip('Work in progress')
    def test_updating_add(self):
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:testMyResMinimal"))
        self.assertTrue(r1.closed)
        r1[ResClassAttribute.LABEL] = LangString(["Minimal Resource@en", "Kleinste Resource@de", "Plus petite ressource@fr"])
        r1[ResClassAttribute.COMMENT] = LangString("Eine Beschreibung einer minimalen Ressource")
        r1[ResClassAttribute.SUPERCLASS] = Iri("test:testMyRes")
        r1[ResClassAttribute.CLOSED] = Xsd_boolean(False)

        #
        # Add an external, shared property defined by its own sh:PropertyShape instance
        #
        r1[Iri('test:test')] = None

        #
        # Adding an internal, private property
        #
        p = PropertyClass(con=self._connection,
                          project=self._project,
                          toNodeIri=Iri('test:Person'),
                          maxCount=Xsd_integer(1))
        r1[Iri('dcterms:creator')] = p

        p2 = PropertyClass(con=self._connection,
                           project=self._project,
                           datatype=XsdDatatypes.string,
                           inSet=RdfSet(Xsd_string('A'), Xsd_string('B'), Xsd_string('C'), Xsd_string('D'))
                           )
        r1[Iri('test:color')] = p2
        r1.update()
        del r1
        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:testMyResMinimal"))
        self.assertEqual(LangString(["Minimal Resource@en", "Kleinste Resource@de", "Plus petite ressource@fr"]), r2.label)
        self.assertEqual(LangString("Eine Beschreibung einer minimalen Ressource"), r2.comment)
        self.assertEqual({Iri('test:testMyRes')}, set(r2.superclass))
        self.assertIsInstance(r2.superclass[Iri('test:testMyRes')], ResourceClass)
        self.assertFalse(r2[ResClassAttribute.CLOSED])

        prop1 = r2[Iri('test:test')]
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, Iri('test:test'))
        self.assertEqual(prop1.minCount, Xsd_integer(1))
        self.assertEqual(prop1.name, LangString("Test"))
        self.assertEqual(prop1.description, LangString("Property shape for testing purposes"))
        self.assertEqual(prop1.datatype, XsdDatatypes.string)
        self.assertEqual(prop1.order, Xsd_decimal(3))
        self.assertEqual(prop1.propertyType, OwlPropertyType.OwlDataProperty)

        prop2 = r2[Iri('dcterms:creator')]
        self.assertEqual(prop2.internal, Xsd_QName("test:testMyResMinimal"))
        self.assertEqual(prop2.toNodeIri, Xsd_QName('test:Person'))
        self.assertEqual(prop2.maxCount, Xsd_integer(1))
        self.assertEqual(prop1.propertyType, OwlPropertyType.OwlDataProperty)

        prop3 = r2[Iri('test:color')]
        self.assertEqual(prop3.internal, Xsd_QName("test:testMyResMinimal"))
        self.assertEqual(prop3.inSet, RdfSet(Xsd_string('A'), Xsd_string('B'), Xsd_string('C'), Xsd_string('D')))

        sparql = self._context.sparql_context
        sparql += """
        SELECT ?p ?v
        FROM test:onto
        WHERE {
            test:testMyResMinimal rdfs:subClassOf ?prop .
            ?prop owl:onProperty dcterms:creator .
            ?prop ?p ?v .
        }
        """
        jsonobj = self._connection.query(sparql)
        res = QueryProcessor(self._context, jsonobj)
        result = {
            Iri('rdf:type'): 'owl:Restriction',
            Iri('owl:onProperty'): 'dcterms:creator',
            Iri('owl:maxQualifiedCardinality'): 1,
            Iri('owl:onClass'): 'test:Person'
        }
        for r in res:
            p = r['p']
            v = r['v']
            self.assertEqual(result[p], v)

        sparql = self._context.sparql_context
        sparql += """
        SELECT ?p ?v
        FROM test:onto
        WHERE {
            test:testMyResMinimal rdfs:subClassOf ?prop .
            ?prop owl:onProperty test:test .
            ?prop ?p ?v .
        }
        """
        jsonobj = self._connection.query(sparql)
        res = QueryProcessor(self._context, jsonobj)
        result = {
            Iri('rdf:type'): Iri('owl:Restriction'),
            Iri('owl:onProperty'): Iri('test:test'),
            Iri('owl:minQualifiedCardinality'): Xsd_integer(1),
            Iri('owl:onDatatype'): Iri("xsd:string"),
        }
        for r in res:
            p = r['p']
            v = r['v']
            self.assertEqual(result[p], v)

    # @unittest.skip('Work in progress')
    def test_updating(self):
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:testMyRes"))
        self.assertEqual(r1[Iri('test:hasText')].maxCount, Xsd_integer(1))
        self.assertEqual(r1[Iri('test:hasText')].minCount, Xsd_integer(1))
        self.assertEqual(r1[Iri('test:hasText')].languageIn, LanguageIn(Language.EN, Language.DE))
        r1.label[Language.IT] = "La mia risorsa"
        r1.closed = Xsd_boolean(False)
        r1[ResClassAttribute.SUPERCLASS] = {Iri('dcterms:TopGaga')}
        r1[Iri('test:hasText')].name[Language.FR] = "Un Texte Français"
        r1[Iri('test:hasText')].maxCount = Xsd_integer(12)
        r1[Iri('test:hasText')].languageIn = LanguageIn(Language.DE, Language.FR, Language.IT)
        r1[Iri('test:hasEnum')].inSet = RdfSet(Xsd_string('L'), Xsd_string('a'), Xsd_string('b'))
        r1.update()

        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:testMyRes"))
        self.assertEqual(r2.label, LangString(["My Resource@en", "Meine Ressource@de", "Ma Resource@fr", "La mia risorsa@it"]))
        self.assertFalse(r2.closed)
        self.assertEqual({Iri('dcterms:TopGaga')}, set(r2.superclass))
        self.assertIsNone(r2.superclass[Iri('dcterms:TopGaga')])
        self.assertEqual(r2[Iri('test:hasText')].name, LangString(["A text@en", "Ein Text@de", "Un Texte Français@fr"]))
        self.assertEqual(r2[Iri('test:hasText')].maxCount, Xsd_integer(12))
        self.assertEqual(r2[Iri('test:hasText')].languageIn, LanguageIn(Language.DE, Language.FR, Language.IT))
        self.assertEqual(r2[Iri('test:hasEnum')].inSet, RdfSet(Xsd_string('L'), Xsd_string('a'), Xsd_string('b')))

    def test_updating_sc_A(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:p1'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["P1"]),
                           order=Xsd_decimal(1))
        properties: list[PropertyClass | Iri] = [ p1 ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:Crazy"),
                           superclass={"oldap:Thing", 'http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object'},
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           properties=properties)
        r1.create()
        del r1
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri('test:Crazy'))
        del r1.superclass[Iri('http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object')]
        r1.update()
        del r1
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri('test:Crazy'))
        self.assertEqual({"oldap:Thing"}, set(r1.superclass))

    def test_updating_sc_B(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:p2'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["P2"]),
                           order=Xsd_decimal(1))
        properties: list[PropertyClass | Iri] = [ p1 ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:CrazyB"),
                           superclass={"test:testMyRes", 'http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object'},
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           properties=properties)
        r1.create()
        del r1
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri('test:CrazyB'))
        del r1.superclass[Iri("test:testMyRes")]
        r1.update()
        del r1
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri('test:CrazyB'))
        self.assertEqual({Iri('http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object')}, set(r1.superclass))

    def test_updateing_sc_C(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:p3'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["P3"]),
                           order=Xsd_decimal(1))
        properties: list[PropertyClass | Iri] = [ p1 ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:CrazyC"),
                           superclass={"test:testMyRes", 'http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object', 'test:testMyResMinimal'},
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           properties=properties)
        r1.create()
        del r1
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri('test:CrazyC'))
        del r1.superclass['test:testMyResMinimal']
        r1.superclass[Iri('http://gugus.com/gaga/wird/nicht/gehen')] = None
        r1.update()
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri('test:CrazyC'))
        self.assertEqual({"test:testMyRes",
                          'http://www.cidoc-crm.org/cidoc-crm/E22_Man-Made_Object',
                          'http://gugus.com/gaga/wird/nicht/gehen'}, set(r1.superclass))

    # @unittest.skip('Work in progress')
    def test_delete_props(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:propA'),
                           subPropertyOf=Iri('test:comment'),
                           datatype=XsdDatatypes.langString,
                           name=LangString(["Test property@en", "Testprädikat@de"]),
                           description=LangString("A property for testing...@en"),
                           maxCount=Xsd_integer(1),
                           minCount=Xsd_integer(1),
                           uniqueLang=Xsd_boolean(True),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                           order=Xsd_decimal(1))

        p2 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:propB'),
                           toNodeIri=Iri('test:testMyRes'),
                           name=LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]),
                           description=LangString("An exclusive property for testing...@en"),
                           minCount=Xsd_integer(1),
                           order=Xsd_decimal(2))

        p3 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:propC'),
                           datatype=XsdDatatypes.int,
                           inSet=RdfSet(Xsd_integer(10), Xsd_integer(20), Xsd_integer(30)))

        properties: list[PropertyClass | Iri] = [
            Iri("test:comment"),
            Iri("test:test"),
            p1, p2, p3
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:TestResourceDelProps"),
                           superclass="test:testMyResMinimal",
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           properties=properties)

        r1.create()

        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:TestResourceDelProps"))
        del r2[Iri('test:propB')]
        del r2[Iri("test:test")]  # OWL is not yet removed (rdfs:subClassOf is still there)
        del r2[Iri('test:propC')]
        r2.update()

        r3 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:TestResourceDelProps"))

        self.assertTrue(check_prop_empty(self._connection, self._context, Graph.SHACL, 'test:testMyResMinimal', 'test:propB'))
        self.assertTrue(check_prop_empty(self._connection, self._context, Graph.ONTO, 'test:testMyResMinimal', 'test:propB'))

        self.assertTrue(check_prop_empty(self._connection, self._context, Graph.SHACL, 'test:testMyResMinimal', 'test:test'))
        self.assertTrue(check_prop_empty(self._connection, self._context, Graph.ONTO, 'test:testMyResMinimal', 'test:test'))

        self.assertTrue(check_prop_empty(self._connection, self._context, Graph.SHACL, 'test:testMyResMinimal', 'test:propC'))
        self.assertTrue(check_prop_empty(self._connection, self._context, Graph.ONTO, 'test:testMyResMinimal', 'test:propC'))

    # @unittest.skip('Work in progress')
    def test_delete(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:deleteA'),
                           subPropertyOf=Iri('test:comment'),
                           datatype=XsdDatatypes.langString,
                           name=LangString(["Test property@en", "Testprädikat@de"]),
                           description=LangString("A property for testing...@en"),
                           maxCount=Xsd_integer(1),
                           minCount=Xsd_integer(1),
                           uniqueLang=Xsd_boolean(True),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                           order=Xsd_decimal(1))

        p2 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:deleteB'),
                           toNodeIri=Iri('test:testMyRes'),
                           name=LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]),
                           description=LangString("A property for testing...@en"),
                           minCount=Xsd_integer(1),
                           order=Xsd_decimal(2))

        p3 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:deleteC'),
                           datatype=XsdDatatypes.int,
                           inSet=RdfSet(Xsd_integer(10), Xsd_integer(20), Xsd_integer(30)))

        properties: list[PropertyClass | Iri] = [
            Iri("test:comment"),
            Iri("test:test"),
            p1, p2, p3
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:TestResourceDelete"),
                           superclass="test:testMyResMinimal",
                           label=LangString(["DeleteResTest@en", "EffaçerResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           properties=properties)
        r1.create()
        del r1

        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Iri("test:TestResourceDelete"))
        r2.delete()

        self.assertTrue(check_res_empty(self._connection, self._context, Graph.SHACL, 'test:TestResourceDelete'))
        self.assertTrue(check_res_empty(self._connection, self._context, Graph.ONTO, 'test:TestResourceDelete'))
        superclass = ResourceClass.read(con=self._connection,
                                        project=self._project,
                                        owl_class_iri=Iri("test:testMyResMinimal"))
        self.assertEqual(Iri("test:testMyResMinimal"), superclass.owl_class_iri)

    # @unittest.skip('Work in progress')
    def test_write_trig(self):
        project_id = PropertyClass(con=self._connection,
                                   project=self._project,
                                   property_class_iri=Iri('test:projectId'),
                                   datatype=XsdDatatypes.langString,
                                   name=LangString(["Project ID@en", "Projekt ID@de"]),
                                   description=LangString(["Unique ID for project@en", "Eindeutige ID für Projekt@de"]),
                                   minCount=Xsd_integer(1),
                                   languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                                   uniqueLang=Xsd_boolean(True),
                                   order=Xsd_decimal(1))
        project_name = PropertyClass(con=self._connection,
                                     project=self._project,
                                     property_class_iri=Iri('test:projectName'),
                                     datatype=XsdDatatypes.langString,
                                     name=LangString(["Project name@en", "Projektname@de"]),
                                     description=LangString(["A description of the project@en", "EineBeschreibung des Projekts@de"]),
                                     minCount=Xsd_integer(1),
                                     languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                                     uniqueLang=Xsd_boolean(True),
                                     order=Xsd_decimal(2))

        properties: list[PropertyClass | Xsd_QName] = [
            project_id, project_name
        ]
        superclass = ResourceClass.read(con=self._connection,
                                        project=self._project,
                                        owl_class_iri=Iri("test:testMyResMinimal"))

        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Iri("test:Project"),
                           superclass={"test:testMyResMinimal", Iri('http://andromeda.com/cluster1/cepheid_42')},
                           label=LangString(["Project@en", "Projekt@de"]),
                           comment=LangString(["Definiton of a project@en", "Definition eines Projektes@de"]),
                           closed=Xsd_boolean(True),
                           properties=properties)
        r1.write_as_trig("gaga.trig")


if __name__ == '__main__':
    unittest.main()
