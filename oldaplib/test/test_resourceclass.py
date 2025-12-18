"""
Test data
"""
import json
import unittest
from copy import deepcopy
from enum import Enum
from pathlib import Path
from pprint import pprint
from time import sleep

from oldaplib.src.cachesingleton import CacheSingletonRedis
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
from oldaplib.src.helpers.oldaperror import OldapErrorAlreadyExists, OldapErrorNoPermission, OldapErrorInUse
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.semantic_version import SemanticVersion
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropClassAttrContainer, PropertyClass
from oldaplib.src.enums.owlpropertytype import OwlPropertyType
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.hasproperty import HasProperty
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
    _project: Project
    _sysproject: Project

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        project_root = find_project_root(__file__)

        cache = CacheSingletonRedis()
        cache.clear()

        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://oldap.org/test#")
        cls._context.use('test', 'dcterms')

        cls._connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        cls._unpriv = Connection(userId="fornaro",
                                 credentials="RioGrande",
                                 context_name="DEFAULT")


        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        cls._connection.clear_graph(Xsd_QName('test:data'))

        cls._connection.clear_graph(Xsd_QName('dcterms:shacl'))
        cls._connection.clear_graph(Xsd_QName('dcterms:onto'))

        file = project_root / 'oldaplib' / 'testdata' / 'connection_test.trig'
        cls._connection.upload_turtle(file)

        cls._project = Project.read(cls._connection, "test")
        cls._sysproject = Project.read(cls._connection, "oldap", ignore_cache=True)


    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(QName('test:shacl'))
        #cls._connection.clear_graph(QName('test:onto'))
        pass

    # @unittest.skip('Work in progress')
    def test_constructor(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:testprop'),
                           subPropertyOf=Xsd_QName('test:comment'),
                           datatype=XsdDatatypes.langString,
                           name=LangString(["Test property@en", "Testprädikat@de"]),
                           description=LangString("A property for testing...@en"),
                           uniqueLang=Xsd_boolean(True),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        p2 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:enumprop'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["Test enum@en", "Enumerationen@de"]),
                           inSet=RdfSet(Xsd_string("yes"), Xsd_string("maybe"), Xsd_string("no")))

        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:comment"), maxCount=1, order=1),
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:test"), minCount=1, order=2),
            HasProperty(con=self._connection, project=self._project, prop=p1, maxCount=1, order=3),
            HasProperty(con=self._connection, project=self._project, prop=p2, minCount=1, maxCount=1, order=4)
        ]

        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:TestResource"),
                           label=LangString(["Test resource@en", "Resource de test@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        self.assertEqual(r1[ResClassAttribute.LABEL], LangString(["Test resource@en", "Resource de test@fr"]))
        self.assertEqual(r1.label, LangString(["Test resource@en", "Resource de test@fr"]))
        self.assertEqual(r1[ResClassAttribute.COMMENT], LangString("For testing purposes@en"))
        self.assertEqual(r1.comment, LangString("For testing purposes@en"))
        self.assertTrue(r1[ResClassAttribute.CLOSED])
        self.assertTrue(r1.closed)

        prop1 = r1[Xsd_QName("test:comment")].prop
        self.assertEqual(r1[Xsd_QName("test:comment")].maxCount, Xsd_integer(1))
        self.assertEqual(r1[Xsd_QName("test:comment")].order, Xsd_decimal(1))
        self.assertIsNotNone(prop1)
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, Xsd_QName("test:comment"))
        self.assertEqual(prop1.datatype, XsdDatatypes.langString)
        self.assertEqual(prop1.name, LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(prop1.description, LangString("This is a test property@de"))
        self.assertEqual(prop1.uniqueLang, Xsd_boolean(True))

        prop2 = r1[Xsd_QName("test:test")].prop
        self.assertEqual(r1[Xsd_QName("test:test")].minCount, Xsd_integer(1))
        self.assertEqual(r1[Xsd_QName("test:test")].order, Xsd_decimal(2))
        self.assertIsNone(prop2.internal)
        self.assertEqual(prop2.property_class_iri, Xsd_QName("test:test"))
        self.assertEqual(prop2.datatype, XsdDatatypes.string)
        self.assertEqual(prop2.description, LangString("Property shape for testing purposes"))

        prop3 = r1[Xsd_QName("test:testprop")].prop
        self.assertEqual(r1[Xsd_QName("test:testprop")].maxCount, Xsd_integer(1))
        self.assertEqual(r1[Xsd_QName("test:testprop")].order, Xsd_decimal(3))
        self.assertEqual(prop3.internal, Xsd_QName('test:TestResource'))
        self.assertEqual(prop3.property_class_iri, Xsd_QName("test:testprop"))
        self.assertEqual(prop3.type, {OwlPropertyType.OwlDataProperty})
        self.assertEqual(prop3.datatype, XsdDatatypes.langString)
        self.assertEqual(prop3.name, LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(prop3.subPropertyOf, Xsd_QName("test:comment"))
        self.assertEqual(prop3.uniqueLang,  Xsd_boolean(True))
        self.assertEqual(prop3.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        prop4 = r1[Xsd_QName("test:enumprop")].prop
        self.assertEqual(r1[Xsd_QName("test:enumprop")].maxCount, Xsd_integer(1))
        self.assertEqual(r1[Xsd_QName("test:enumprop")].minCount, Xsd_integer(1))
        self.assertEqual(r1[Xsd_QName("test:enumprop")].order, Xsd_decimal(4))
        self.assertEqual(prop4[PropClassAttr.IN],
                         RdfSet(Xsd_string("yes"), Xsd_string("maybe"), Xsd_string("no")))

    @unittest.skip('Used only for development of currect SHACL/OWL....')
    def test_gaga(self):
        ep = PropertyClass(con=self._connection,
                           project="test",
                           property_class_iri=Xsd_QName("schema:givenName"),
                           datatype=XsdDatatypes.string,
                           maxLength=64,
                           minLength=3,
                           _externalOntology=Xsd_boolean(True))
        ep2 = PropertyClass(con=self._connection,
                            project="test",
                            property_class_iri=Xsd_QName("schema:comment"),
                            toClass='schema:Comment')
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=ep2, minCount=1, order=1),
            HasProperty(con=self._connection, project=self._project, prop=Iri('schema:description')),
            HasProperty(con=self._connection, project=self._project, prop=ep, minCount=1, maxCount=1, order=3.0),
        ]
        r1 = ResourceClass(con=self._connection,
                           project="test",
                           owlclass_iri=Xsd_QName("test:Gaga"),
                           label=LangString(["Test gaga@en", "Resource de gaga@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        p2 = r1[Xsd_QName('schema:description')]
        #r1.write_as_trig("0000000.trig")
        r1.create()
        p2 = r1[Xsd_QName('schema:description')]

        r2 = ResourceClass.read(con=self._connection,
                                project="test",
                                owl_class_iri=Xsd_QName('test:Gaga'),
                                ignore_cache=True)
        #r2.write_as_trig("111111111.trig")
        p1 = r2[Xsd_QName('schema:comment')]
        self.assertIsInstance(p1.prop.property_class_iri, Xsd_QName)
        p2 = r2[Xsd_QName('schema:description')]

    def test_create_next_generation(self):
        #
        # first we create a standalone property
        #
        p0 = PropertyClass(con=self._connection,
                           project="test",
                           property_class_iri=Xsd_QName('test:standalone'),
                           datatype=XsdDatatypes.integer)
        p0.create()
        p0 = PropertyClass.read(con=self._connection,
                                project="test",
                                property_class_iri=Xsd_QName('test:standalone'),
                                ignore_cache=True)

        #
        # now we create an internal property with no super property
        #
        p1 = PropertyClass(con=self._connection,
                           project="test",
                           property_class_iri=Xsd_QName('test:internal'),
                           datatype=XsdDatatypes.langString,
                           name=LangString(["internal@en", "internal@de"]),
                           description=LangString("A property for testing...@en"),
                           uniqueLang=Xsd_boolean(True),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        #
        # now we create an internal property with a super property
        #
        p2 = PropertyClass(con=self._connection,
                           project="test",
                           property_class_iri=Xsd_QName('test:internalWithSuper'),
                           subPropertyOf=Iri('dcterms:description'),
                           datatype=XsdDatatypes.langString,
                           name=LangString(["internalWithSuper@en", "internalWithSuper@de"]),
                           description=LangString("A property for testing...@en"),
                           uniqueLang=Xsd_boolean(True),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        #
        # now let's create a resource class with all possible combinations of properties
        #
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=p1, maxCount=1, order=1),
            HasProperty(con=self._connection, project=self._project, prop=p2, minCount=1, maxCount=1, order=2),
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName('schema:comment'), minCount=1, order=3),
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName('schema:description')),
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName('test:standalone'), maxCount=1, order=4)
        ]
        r1 = ResourceClass(con=self._connection,
                           project="test",
                           owlclass_iri=Xsd_QName("test:TestResourceNextGeneration"),
                           label=LangString(["Test resource@en", "Resource de test@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()

        r1 = ResourceClass.read(con=self._connection,
                                project="test",
                                owl_class_iri=Xsd_QName('test:TestResourceNextGeneration'),
                                ignore_cache=True)
        p1 = r1[Xsd_QName('test:internal')]
        self.assertEqual(p1.prop.datatype, XsdDatatypes.langString)
        self.assertEqual(p1.prop.name, LangString(["internal@en", "internal@de"]))
        self.assertEqual(p1.maxCount, 1)
        self.assertIsNone(p1.minCount)
        self.assertEqual(p1.order, 1)

        p2 = r1[Xsd_QName('test:internalWithSuper')]
        self.assertEqual(p2.maxCount, 1)
        self.assertEqual(p2.minCount, 1)
        self.assertEqual(p2.order, 2)
        self.assertEqual(p2.prop.subPropertyOf, Iri('dcterms:description'))
        self.assertEqual(p2.prop.datatype, XsdDatatypes.langString)
        self.assertEqual(p2.prop.name, LangString(["internalWithSuper@en", "internalWithSuper@de"]))
        self.assertEqual(p2.prop.description, LangString("A property for testing..."))
        self.assertEqual(p2.prop.uniqueLang,  Xsd_boolean(True))
        self.assertEqual(p2.prop.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        p3 = r1[Xsd_QName('schema:comment')]
        self.assertEqual(p3.minCount, 1)
        self.assertIsNone(p3.maxCount)
        self.assertEqual(p3.order, 3)
        self.assertIsNone(p3.group)
        self.assertIsInstance(p3.prop.property_class_iri, Xsd_QName)

        p4 = r1[Xsd_QName('schema:description')]
        self.assertIsNone(p4.minCount)
        self.assertIsNone(p4.maxCount)
        self.assertIsNone(p4.order)
        self.assertIsInstance(p4.prop.property_class_iri, Xsd_QName)

        p5 = r1[Xsd_QName('test:standalone')]
        self.assertIsNone(p5.minCount)
        self.assertEqual(p5.maxCount, 1)
        self.assertEqual(p5.order, 4)
        self.assertIsNone(p5.group)
        self.assertIsInstance(p5.prop, PropertyClass)
        self.assertEqual(p5.prop.datatype, XsdDatatypes.integer)

    def test_constructor_projectns(self):
        p1 = PropertyClass(con=self._connection,
                           project="test",
                           property_class_iri=Xsd_QName('test:testpropns'),
                           subPropertyOf=Iri('test:comment'),
                           datatype=XsdDatatypes.langString,
                           name=LangString(["Test property@en", "Testprädikat@de"]),
                           description=LangString("A property for testing...@en"),
                           uniqueLang=Xsd_boolean(True),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        p2 = PropertyClass(con=self._connection,
                           project="test",
                           property_class_iri=Xsd_QName('test:enumpropns'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["Test enum@en", "Enumerationen@de"]),
                           inSet=RdfSet(Xsd_string("yes"), Xsd_string("maybe"), Xsd_string("no")))

        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=p1, maxCount=1, order=1),
            HasProperty(con=self._connection, project=self._project, prop=p2, minCount=1, maxCount=1, order=2)
        ]

        r1 = ResourceClass(con=self._connection,
                           project="test",
                           owlclass_iri=Xsd_QName("test:TestResource"),
                           label=LangString(["Test resource@en", "Resource de test@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        self.assertEqual(r1[ResClassAttribute.LABEL], LangString(["Test resource@en", "Resource de test@fr"]))
        self.assertEqual(r1.label, LangString(["Test resource@en", "Resource de test@fr"]))
        self.assertEqual(r1[ResClassAttribute.COMMENT], LangString("For testing purposes@en"))
        self.assertEqual(r1.comment, LangString("For testing purposes@en"))
        self.assertTrue(r1[ResClassAttribute.CLOSED])
        self.assertTrue(r1.closed)

    def test_resourceclass_serialize_deserialize_A(self):
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:comment"), maxCount=1, order=1),
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:test"), minCount=1, order=2),
        ]

        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:TestResourceDeepcopyA"),
                           hasproperties=hasproperties)
        r1.create()
        jsonstr = json.dumps(r1, default=serializer.encoder_default)
        r2 = json.loads(jsonstr, object_hook=serializer.make_decoder_hook(connection=self._connection))

        p_a = r1[Xsd_QName("test:comment")].prop
        self.assertIsNone(p_a.internal)
        p_b = r2[Xsd_QName("test:comment")].prop
        self.assertIsNone(p_b.internal)


    #@unittest.skip('Work in progress')
    def test_resourceclass_serialize_deserialize(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:deepc_prop1'),
                           subPropertyOf=Xsd_QName('test:comment'),
                           datatype=XsdDatatypes.langString,
                           name=LangString(["Test property@en", "Testprädikat@de"]),
                           description=LangString("A property for testing...@en"),
                           uniqueLang=Xsd_boolean(True),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        p2 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:deepc_prop2'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["Test enum@en", "Enumerationen@de"]),
                           inSet=RdfSet(Xsd_string("yes"), Xsd_string("maybe"), Xsd_string("no")))

        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:comment"), maxCount=1, order=1),
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:test"), minCount=1, order=2),
            HasProperty(con=self._connection, project=self._project, prop=p1, maxCount=1, order=3),
            HasProperty(con=self._connection, project=self._project, prop=p2, minCount=1, maxCount=1, order=4)
        ]

        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:TestResourceDeepcopy"),
                           label=LangString(["Test resource@en", "Resource de test@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        #
        # in order to process standalone properties correctly for deserializing, the resourceclass
        # has to be written
        r1.create()
        jsonstr = json.dumps(r1, default=serializer.encoder_default)
        r2 = json.loads(jsonstr, object_hook=serializer.make_decoder_hook(connection=self._connection))

        self.assertFalse(r1 is r2)
        self.assertEqual(r1[ResClassAttribute.LABEL], r2[ResClassAttribute.LABEL])
        self.assertEqual(r1.label, r2.label)
        self.assertEqual(r1[ResClassAttribute.COMMENT], r2[ResClassAttribute.COMMENT])
        self.assertEqual(r1.comment, r2.comment)
        self.assertTrue(r2[ResClassAttribute.CLOSED])
        self.assertTrue(r2.closed)

        self.assertEqual(r1[Xsd_QName("test:comment")].maxCount, r2[Xsd_QName("test:comment")].maxCount)
        self.assertEqual(r1[Xsd_QName("test:comment")].order, r2[Xsd_QName("test:comment")].order)

        prop1a = r1[Xsd_QName("test:comment")].prop
        prop1b = r2[Xsd_QName("test:comment")].prop
        self.assertIsNotNone(prop1b)
        self.assertIsNone(prop1b.internal)
        self.assertEqual(prop1a.property_class_iri, prop1b.property_class_iri)
        self.assertEqual(prop1a.datatype, prop1a.datatype)
        self.assertEqual(prop1a.name, prop1b.name)
        self.assertEqual(prop1a.description, prop1b.description)
        self.assertEqual(prop1a.uniqueLang, prop1b.uniqueLang)

        self.assertEqual(r1[Xsd_QName("test:test")].minCount, r2[Xsd_QName("test:test")].minCount)
        self.assertEqual(r1[Xsd_QName("test:test")].order, r2[Xsd_QName("test:test")].order)
        prop2a = r1[Xsd_QName("test:test")].prop
        prop2b = r2[Xsd_QName("test:test")].prop
        self.assertIsNone(prop2b.internal)
        self.assertEqual(prop2a.property_class_iri, prop2b.property_class_iri)
        self.assertEqual(prop2a.datatype, prop2b.datatype)
        self.assertEqual(prop2a.description, prop2b.description)

        self.assertEqual(r1[Xsd_QName("test:deepc_prop1")].maxCount, r2[Xsd_QName("test:deepc_prop1")].maxCount)
        self.assertEqual(r1[Xsd_QName("test:deepc_prop1")].order, r2[Xsd_QName("test:deepc_prop1")].order)
        prop3a = r1[Xsd_QName("test:deepc_prop1")].prop
        prop3b = r2[Xsd_QName("test:deepc_prop1")].prop
        self.assertEqual(prop3a.internal, prop3b.internal)
        self.assertEqual(prop3a.property_class_iri, prop3b.property_class_iri)
        self.assertEqual(prop3a.type, prop3b.type)
        self.assertEqual(prop3a.datatype, prop3b.datatype)
        self.assertEqual(prop3a.name, prop3b.name)
        self.assertEqual(prop3a.subPropertyOf, prop3b.subPropertyOf)
        self.assertEqual(prop3a.uniqueLang,  prop3b.uniqueLang)
        self.assertEqual(prop3a.languageIn, prop3b.languageIn)

        self.assertEqual(r1[Xsd_QName("test:deepc_prop2")].maxCount, r2[Xsd_QName("test:deepc_prop2")].maxCount)
        self.assertEqual(r1[Xsd_QName("test:deepc_prop2")].minCount, r2[Xsd_QName("test:deepc_prop2")].minCount)
        self.assertEqual(r1[Xsd_QName("test:deepc_prop2")].order, r2[Xsd_QName("test:deepc_prop2")].order)
        prop4a = r1[Xsd_QName("test:deepc_prop2")].prop
        prop4b = r2[Xsd_QName("test:deepc_prop2")].prop
        self.assertEqual(prop4a[PropClassAttr.IN], prop4b[PropClassAttr.IN])

    def test_reading_sys(self):
        r1 = ResourceClass.read(con=self._connection,
                                project=self._sysproject,
                                owl_class_iri=Xsd_QName('oldap:User'),
                                ignore_cache=True)
        self.assertEqual(r1.owl_class_iri, Xsd_QName('oldap:User'))
        self.assertEqual(r1.version, SemanticVersion(0, 1, 0))
        self.assertEqual(r1.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(r1.created, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(r1.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(r1.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))

        prop1 = r1[Xsd_QName('dcterms:creator')]
        self.assertEqual(prop1.minCount, Xsd_integer(1))
        self.assertEqual(prop1.maxCount, Xsd_integer(1))
        self.assertEqual(prop1.prop.property_class_iri, Xsd_QName('dcterms:creator'))
        self.assertEqual(prop1.prop.toClass, Xsd_QName('oldap:User'))

        prop2 = r1[Xsd_QName('dcterms:created')]
        self.assertEqual(prop2.minCount, Xsd_integer(1))
        self.assertEqual(prop2.maxCount, Xsd_integer(1))
        self.assertEqual(prop2.prop.property_class_iri, Xsd_QName('dcterms:created'))
        self.assertEqual(prop2.prop.datatype, XsdDatatypes.dateTime)

        prop3 = r1[Xsd_QName('dcterms:contributor')]
        self.assertEqual(prop3.minCount, Xsd_integer(1))
        self.assertEqual(prop3.maxCount, Xsd_integer(1))
        self.assertEqual(prop3.prop.property_class_iri, Xsd_QName('dcterms:contributor'))
        self.assertEqual(prop3.prop.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop3.prop.created, Xsd_dateTime('2023-11-04T12:00:00+00:00'))
        self.assertEqual(prop3.prop.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop3.prop.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop3.prop.toClass, Xsd_QName('oldap:User'))

        prop4 = r1[Xsd_QName('dcterms:modified')]
        self.assertEqual(prop4.minCount, Xsd_integer(1))
        self.assertEqual(prop4.maxCount, Xsd_integer(1))
        self.assertEqual(prop4.prop.property_class_iri, Xsd_QName('dcterms:modified'))
        self.assertEqual(prop4.prop.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop4.prop.created, Xsd_dateTime('2023-11-04T12:00:00+00:00'))
        self.assertEqual(prop4.prop.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop4.prop.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop4.prop.datatype, XsdDatatypes.dateTime)

        prop5 = r1[Xsd_QName('oldap:userId')]
        self.assertEqual(prop5.minCount, Xsd_integer(1))
        self.assertEqual(prop5.maxCount, Xsd_integer(1))
        self.assertEqual(prop5.prop.property_class_iri, Xsd_QName('oldap:userId'))
        self.assertEqual(prop5.prop.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop5.prop.created, Xsd_dateTime('2023-11-04T12:00:00+00:00'))
        self.assertEqual(prop5.prop.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop5.prop.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop5.prop.datatype, XsdDatatypes.NCName)
        self.assertEqual(prop5.prop.minLength, Xsd_integer(3))
        self.assertEqual(prop5.prop.maxLength, Xsd_integer(32))

        prop6 = r1[Xsd_QName('schema:familyName')]
        self.assertEqual(prop6.minCount, Xsd_integer(1))
        self.assertEqual(prop6.maxCount, Xsd_integer(1))
        self.assertEqual(prop6.prop.property_class_iri, Xsd_QName('schema:familyName'))
        self.assertEqual(prop6.prop.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop6.prop.created, Xsd_dateTime('2023-11-04T12:00:00+00:00'))
        self.assertEqual(prop6.prop.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop6.prop.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop6.prop.datatype, XsdDatatypes.string)
        self.assertEqual(prop6.prop.name, LangString(["Family name@en", "Familiennamen@de", "Nom de famillie@fr", "Nome della famiglia@it"]))
        self.assertEqual(prop6.prop.description, LangString("The family name of some person.@en"))

        prop7 = r1[Xsd_QName('schema:givenName')]
        self.assertEqual(prop7.minCount, Xsd_integer(1))
        self.assertEqual(prop7.maxCount, Xsd_integer(1))
        self.assertEqual(prop7.prop.property_class_iri, Xsd_QName('schema:givenName'))
        self.assertEqual(prop7.prop.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop7.prop.created, Xsd_dateTime('2023-11-04T12:00:00+00:00'))
        self.assertEqual(prop7.prop.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop7.prop.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop7.prop.datatype, XsdDatatypes.string)
        self.assertEqual(prop7.prop.name, LangString(["Given name@en", "Vornamen@de", "Prénom@fr", "Nome@it"]))
        self.assertEqual(prop7.prop.description, LangString("The given name of some person@en"))

        prop8 = r1[Xsd_QName('oldap:credentials')]
        self.assertEqual(prop8.minCount, Xsd_integer(1))
        self.assertEqual(prop8.maxCount, Xsd_integer(1))
        self.assertEqual(prop8.prop.property_class_iri, Xsd_QName('oldap:credentials'))
        self.assertEqual(prop8.prop.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop8.prop.created, Xsd_dateTime('2023-11-04T12:00:00+00:00'))
        self.assertEqual(prop8.prop.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop8.prop.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop8.prop.datatype, XsdDatatypes.string)
        self.assertEqual(prop8.prop.name, LangString(["Password@en", "Passwort@de", "Mot de passe@fr", "Password@it"]))
        self.assertEqual(prop8.prop.description, LangString("Password for user.@en"))

        prop9 = r1[Xsd_QName('oldap:inProject')]
        self.assertEqual(prop9.prop.property_class_iri, Xsd_QName('oldap:inProject'))
        self.assertEqual(prop9.prop.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop9.prop.created, Xsd_dateTime('2023-11-04T12:00:00+00:00'))
        self.assertEqual(prop9.prop.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop9.prop.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop9.prop.toClass, Xsd_QName('oldap:Project'))

        prop10 = r1[Xsd_QName('oldap:isActive')]
        self.assertEqual(prop10.minCount, Xsd_integer(1))
        self.assertEqual(prop10.maxCount, Xsd_integer(1))
        self.assertEqual(prop10.prop.property_class_iri, Xsd_QName('oldap:isActive'))
        self.assertEqual(prop10.prop.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop10.prop.created, Xsd_dateTime('2023-11-04T12:00:00+00:00'))
        self.assertEqual(prop10.prop.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop10.prop.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop10.prop.datatype, XsdDatatypes.boolean)
        self.assertIsNone(prop10.prop.name)
        self.assertIsNone(prop10.prop.description)

        prop11 = r1[Xsd_QName('oldap:hasPermissions')]
        self.assertEqual(prop11.prop.property_class_iri, Xsd_QName('oldap:hasPermissions'))
        self.assertEqual(prop11.prop.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop11.prop.created, Xsd_dateTime('2023-11-04T12:00:00+00:00'))
        self.assertEqual(prop11.prop.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop11.prop.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop11.prop.toClass, Xsd_QName('oldap:PermissionSet'))

    # @unittest.skip('Work in progress')
    def test_reading(self):
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:testMyRes'),
                                ignore_cache=True)
        self.assertEqual(r1.owl_class_iri, Xsd_QName('test:testMyRes'))
        #self.assertEqual(r1.version, SemanticVersion(0, 1, 0))
        self.assertEqual(r1.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(r1.created, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(r1.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(r1.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(r1.label, LangString(["My Resource@en", "Meine Ressource@de", "Ma Resource@fr"]))
        self.assertEqual(r1.comment, LangString("Resource for testing..."))
        self.assertTrue(r1.closed)

        prop1 = r1[Xsd_QName('test:test')].prop
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, Xsd_QName("test:test"))
        #self.assertEqual(prop1.version, SemanticVersion(0, 1, 0))
        self.assertEqual(prop1.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop1.created, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop1.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop1.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop1.type, {OwlPropertyType.OwlDataProperty})
        self.assertEqual(prop1.datatype, XsdDatatypes.string)
        self.assertEqual(prop1.description, LangString("Property shape for testing purposes"))
        self.assertEqual(r1[Xsd_QName('test:test')].minCount, Xsd_integer(1))
        self.assertEqual(r1[Xsd_QName('test:test')].order, Xsd_decimal(3))

        prop2 = r1[Xsd_QName('test:hasText')].prop
        self.assertEqual(prop2.internal, Xsd_QName('test:testMyRes'))
        self.assertEqual(prop2.property_class_iri, Xsd_QName("test:hasText"))
        #self.assertEqual(prop2.version, SemanticVersion(1, 0, 0))
        self.assertEqual(prop2.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop2.created, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop2.contributor, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop2.modified, Xsd_dateTime('2023-11-04T12:00:00Z'))
        self.assertEqual(prop2.type, {OwlPropertyType.OwlDataProperty})
        self.assertEqual(prop2.datatype, XsdDatatypes.langString)
        self.assertEqual(prop2.name, LangString(["A text@en", "Ein Text@de"]))
        self.assertEqual(prop2.description, LangString("A longer text..."))
        self.assertEqual(r1[Xsd_QName('test:hasText')].minCount, Xsd_integer(1))
        self.assertEqual(r1[Xsd_QName('test:hasText')].maxCount, Xsd_integer(1))
        self.assertEqual(r1[Xsd_QName('test:hasText')].order, Xsd_decimal(1))

        prop3 = r1[Xsd_QName('test:hasEnum')].prop
        self.assertEqual(prop3.type, {OwlPropertyType.OwlDataProperty})
        self.assertEqual(prop3.datatype, XsdDatatypes.string)
        self.assertEqual(prop3.inSet,
                         RdfSet(Xsd_string('red'), Xsd_string('green'), Xsd_string('blue'), Xsd_string('yellow')))

    def test_resource_jsonify(self):
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:testMyRes'),
                                ignore_cache=True)
        jsonstr = json.dumps(r1, default=serializer.encoder_default, indent=3)
        r2 = json.loads(jsonstr, object_hook=serializer.make_decoder_hook(connection=self._connection))
        self.assertEqual(r2.owl_class_iri, Xsd_QName('test:testMyRes'))
        #self.assertEqual({Iri('test:testMyResMinimal'), Iri('oldap:Thing')}, {x for x in r2.superclass})
        self.assertEqual(r2.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertTrue(r2.closed)

        hp1 = r2[Xsd_QName('test:test')]
        self.assertEqual(hp1.minCount, Xsd_integer(1))
        self.assertEqual(hp1.maxCount, Xsd_integer(1))
        self.assertEqual(hp1.order, Xsd_decimal(3))
        p1 = hp1.prop
        self.assertIsNone(p1.internal)

        hp2 = r2[Xsd_QName('test:hasText')]
        self.assertEqual(hp2.minCount, Xsd_integer(1))
        self.assertEqual(hp2.maxCount, Xsd_integer(1))
        self.assertEqual(hp2.order, Xsd_decimal(1))
        p2 = hp2.prop
        self.assertIsNotNone(p2.internal)
        self.assertEqual(p2.datatype, XsdDatatypes.langString)
        self.assertEqual(p2.languageIn, {Language.EN, Language.DE})
        self.assertEqual(p2.name, LangString("A text@en", "Ein Text@de"))
        self.assertEqual(p2.description, LangString("A longer text...@en"))

        hp3 = r2[Xsd_QName('test:hasEnum')]
        p3 = hp3.prop
        self.assertEqual(p3.datatype, XsdDatatypes.string)
        self.assertEqual(p3.inSet, {'blue', 'red', 'green', 'yellow'})

    def test_reading_with_superclass(self):
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:testMyResInherit'))
        self.assertEqual(r1.owl_class_iri, Xsd_QName('test:testMyResInherit'))
        self.assertEqual({Xsd_QName('test:testMyResMinimal'), Xsd_QName('oldap:Thing')}, {x for x in r1.superclass})

    # @unittest.skip('Work in progress')
    def test_creating_empty_resource(self):
        r0 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:TestResourceEmpty"))

        r0.create()

    def test_creating_resource_incremental(self):
        r0 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:TestResourceIncremental", validate=False))
        r0.create()

        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:testIncrementalProp1'),
                           subPropertyOf=Iri('test:comment'),
                           datatype=XsdDatatypes.langString,
                           name=LangString(["Test property@en", "Testprädikat@de"]),
                           description=LangString("A property for testing incrfemental buildup...@en"),
                           uniqueLang=Xsd_boolean(True),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        hp1 = HasProperty(con=self._connection, project=self._project, prop=p1, minCount=1, order=1.0)
        r0[Xsd_QName('test:testIncrementalProp1')] = hp1
        r0.update()

        r0 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:TestResourceIncremental", validate=False))
        self.assertEqual(r0.owl_class_iri, Xsd_QName("test:TestResourceIncremental", validate=False))
        self.assertTrue(Xsd_QName("oldap:Thing", validate=False) in r0.superclass)
        hp1 = r0[Xsd_QName('test:testIncrementalProp1')]
        self.assertEqual(hp1.minCount, 1)
        self.assertIsNone(hp1.maxCount)
        self.assertEqual(hp1.order, 1.0)
        self.assertEqual(hp1.prop.property_class_iri, Xsd_QName("test:testIncrementalProp1", validate=False))
        self.assertEqual(hp1.prop.subPropertyOf, Xsd_QName("test:comment"))
        self.assertEqual(hp1.prop.datatype, XsdDatatypes.langString)

    # TODO: Start systematic testing here!!!!!!!!!!!!¨
    def test_creating(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:testone'),
                           subPropertyOf=Iri('test:comment'),
                           datatype=XsdDatatypes.langString,
                           name=LangString(["Test property@en", "Testprädikat@de"]),
                           description=LangString("A property for testing...@en"),
                           uniqueLang=Xsd_boolean(True),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        p2 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:testtwo'),
                           toClass=Xsd_QName('test:testMyRes'),
                           name=LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]),
                           description=LangString("An exclusive property for testing...@en"))

        p3 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:testthree'),
                           datatype=XsdDatatypes.int,
                           name=LangString(["E.N.U.M@en"]),
                           description=LangString("An exclusive enum testing...@en"),
                           inSet=RdfSet(Xsd_integer(1), Xsd_integer(2), Xsd_integer(3)))

        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:comment"), maxCount=1, order=1),
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:test"), minCount=1, order=2),
            HasProperty(con=self._connection, project=self._project, prop=p1, minCount=1, maxCount=1, order=3),
            HasProperty(con=self._connection, project=self._project, prop=p2, minCount=1, order=4),
            HasProperty(con=self._connection, project=self._project, prop=p3, maxCount=1, order=5)
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:TestResource"),
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()
        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:TestResource"))
        self.assertEqual(r2.owl_class_iri, Xsd_QName("test:TestResource"))
        self.assertEqual(r2.label, LangString(["CreateResTest@en", "CréationResTeste@fr"]))
        self.assertEqual(r2.comment, LangString("For testing purposes@en"))
        self.assertTrue(r2.closed)

        prop1 = r2[Xsd_QName("test:comment")].prop
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, Xsd_QName('test:comment'))
        self.assertEqual(prop1.datatype, XsdDatatypes.langString)
        self.assertTrue(prop1.uniqueLang)
        self.assertEqual(r2[Xsd_QName("test:comment")].maxCount, Xsd_integer(1))
        self.assertEqual(prop1.name, LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(prop1.description, LangString("This is a test property@de"))
        self.assertIsNone(prop1.subPropertyOf)
        self.assertEqual(prop1.type, {OwlPropertyType.OwlDataProperty})
        self.assertEqual(prop1.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop1.created, Xsd_dateTime("2023-11-04T12:00:00Z"))
        self.assertEqual(r2[Xsd_QName("test:comment")].order, Xsd_decimal(1))

        prop2 = r2[Xsd_QName("test:test")].prop
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop2.property_class_iri, Xsd_QName('test:test'))
        self.assertEqual(r2[Xsd_QName("test:test")].minCount, Xsd_integer(1))
        self.assertEqual(prop2.name, LangString("Test"))
        self.assertEqual(prop2.description, LangString("Property shape for testing purposes"))
        self.assertEqual(prop2.datatype, XsdDatatypes.string)
        self.assertEqual(prop2.type, {OwlPropertyType.OwlDataProperty})
        self.assertEqual(r2[Xsd_QName("test:test")].order, Xsd_decimal(2))

        prop3 = r2[Xsd_QName("test:testone")].prop
        self.assertEqual(prop3.internal, Xsd_QName("test:TestResource"))
        self.assertEqual(prop3.property_class_iri, Xsd_QName("test:testone"))
        self.assertEqual(prop3.datatype, XsdDatatypes.langString)
        self.assertEqual(prop3.name, LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(prop3.description, LangString("A property for testing...@en"))
        self.assertEqual(r2[Xsd_QName("test:testone")].minCount, Xsd_integer(1))
        self.assertEqual(r2[Xsd_QName("test:testone")].maxCount, Xsd_integer(1))
        self.assertEqual(prop3.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(prop3.uniqueLang)
        self.assertEqual(r2[Xsd_QName("test:testone")].order, Xsd_decimal(3))

        prop4 = r2[Xsd_QName("test:testtwo")].prop
        self.assertEqual(prop4.internal, Xsd_QName("test:TestResource"))
        self.assertEqual(prop4.property_class_iri, Xsd_QName("test:testtwo"))
        self.assertEqual(prop4.toClass, Xsd_QName('test:testMyRes'))
        self.assertEqual(prop4.name, LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]))
        self.assertEqual(prop4.description, LangString("An exclusive property for testing...@en"))
        self.assertEqual(r2[Xsd_QName("test:testtwo")].minCount, Xsd_integer(1))
        self.assertEqual(r2[Xsd_QName("test:testtwo")].order, Xsd_decimal(4))

        prop5 = r2[Xsd_QName("test:testthree")].prop
        self.assertEqual(prop5.internal, Xsd_QName("test:TestResource"))
        self.assertEqual(prop5.inSet, RdfSet(Xsd_integer(1), Xsd_integer(2), Xsd_integer(3)))
        # r2[Iri("test:testthree")].prop.inSet.add(Xsd_integer(4))
        # del r2[Iri("test:testthree")].maxCount
        # print('r2[Iri("test:testthree")].prop.changeset', r2[Iri("test:testthree")].prop.changeset)
        # print('r2[Iri("test:testthree")].changeset', r2[Iri("test:testthree")].changeset)
        # print('r2.changeset', r2.changeset)



    def test_creating_nopermission(self):
        p1 = PropertyClass(con=self._unpriv,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:testone_np'),
                           subPropertyOf=Xsd_QName('test:comment'),
                           datatype=XsdDatatypes.langString,
                           name=LangString(["Test property@en", "Testprädikat@de"]),
                           description=LangString("A property for testing...@en"),
                           uniqueLang=Xsd_boolean(True),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        p2 = PropertyClass(con=self._unpriv,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:testtwo_np'),
                           toClass=Xsd_QName('test:testMyRes'),
                           name=LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]),
                           description=LangString("An exclusive property for testing...@en"))

        p3 = PropertyClass(con=self._unpriv,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:testthree_np'),
                           datatype=XsdDatatypes.int,
                           name=LangString(["E.N.U.M@en"]),
                           description=LangString("An exclusive enum testing...@en"),
                           inSet=RdfSet(Xsd_integer(1), Xsd_integer(2), Xsd_integer(3)))

        hasproperties: list[HasProperty] = [
            HasProperty(con=self._unpriv, project=self._project, prop=Xsd_QName("test:comment"), maxCount=1, order=1),
            HasProperty(con=self._unpriv, project=self._project, prop=Xsd_QName("test:test"), minCount=1, order=2),
            HasProperty(con=self._unpriv, project=self._project, prop=p1, minCount=1, maxCount=1, order=3),
            HasProperty(con=self._unpriv, project=self._project, prop=p2, minCount=1, order=4),
            HasProperty(con=self._unpriv, project=self._project, prop=p3, order=5)
        ]
        r1 = ResourceClass(con=self._unpriv,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:TestResource_np"),
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)

        with self.assertRaises(OldapErrorNoPermission):
            r1.create()

    def test_creating_with_superclass(self):
        self._context[Xsd_NCName('crm')] = NamespaceIRI('http://www.cidoc-crm.org/cidoc-crm/')
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:sctest_prop1'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["TestProp1"]))
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=p1, order=1)
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:ResWithSuperclasses"),
                           superclass={"test:testMyResMinimal", 'crm:E22_Man-Made_Object'},
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()
        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:ResWithSuperclasses'))
        s = set(r2.superclass.keys())
        self.assertEqual({"oldap:Thing", "test:testMyResMinimal", 'crm:E22_Man-Made_Object'}, s)

    def test_updating_superclass_add(self):
        self._context[Xsd_NCName('crm')] = NamespaceIRI('http://www.cidoc-crm.org/cidoc-crm/')
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:Superclass1"),
                           label=LangString(["Superclass1@en", "Superclass1@fr"]),
                           closed=Xsd_boolean(True))
        r1.create()

        r2 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:Superclass2"),
                           label=LangString(["Superclass2@en", "Superclass2@fr"]),
                           closed=Xsd_boolean(True))
        r2.create()

        r3 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:Superclass3"),
                           label=LangString(["Superclass2@en", "Superclass2@fr"]),
                           closed=Xsd_boolean(True))
        r3.create()

        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:thingtest_prop1'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["ThingTestProp1"]))
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=p1, order=1)
        ]
        r = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:ResWithSuperThingAdd"),
                           superclass={'crm:E22_Man-Made_Object', "test:Superclass1"},
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r.create()
        r = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:ResWithSuperThingAdd'))
        r.add_superclasses({'test:Superclass2', 'test:Superclass3'})
        r.update()
        r = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:ResWithSuperThingAdd'))
        s = set(r.superclass.keys())
        self.assertEqual(s, {"oldap:Thing", 'crm:E22_Man-Made_Object', "test:Superclass1", "test:Superclass2", "test:Superclass3"})

    def test_updating_superclass_del(self):
        self._context[Xsd_NCName('crm')] = NamespaceIRI('http://www.cidoc-crm.org/cidoc-crm/')
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:SuperclassDel1"),
                           label=LangString(["SuperclassDel1@en", "SuperclassDel1@fr"]),
                           closed=Xsd_boolean(True))
        r1.create()

        r2 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:SuperclassDel2"),
                           label=LangString(["SuperclassDel2@en", "SuperclassDel2@fr"]),
                           closed=Xsd_boolean(True))
        r2.create()

        r3 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:SuperclassDel3"),
                           label=LangString(["SuperclassDel3@en", "SuperclassDel3@fr"]),
                           closed=Xsd_boolean(True))
        r3.create()

        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:deltest_prop1'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["DelTestProp1"]))
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=p1, order=1)
        ]
        r = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:ResWithManySuper2"),
                           superclass={
                               'crm:E22_Man-Made_Object',
                               "test:SuperclassDel1",
                               "test:SuperclassDel2",
                               "test:SuperclassDel3"},
                           label=LangString(["CreateResTestDelSup@en", "CréationResTesteDelSup@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r.create()
        r = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:ResWithManySuper2"))
        r.del_superclasses({'test:SuperclassDel1', 'test:SuperclassDel3'})
        r.update()
        r = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:ResWithManySuper2"))
        s = set(r.superclass.keys())
        self.assertEqual(s, {"oldap:Thing", 'crm:E22_Man-Made_Object', "test:SuperclassDel2"})

    def test_creating_with_thing_sc(self):
        self._context[Xsd_NCName('crm')] = NamespaceIRI('http://www.cidoc-crm.org/cidoc-crm/')
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:thingtest_prop1'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["ThingTestProp1"]))
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=p1, order=1)
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:ResWithSuperThing"),
                           superclass={'oldap:Thing', 'crm:E22_Man-Made_Object'},
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()
        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:ResWithSuperThing'))
        s = set(r2.superclass.keys())
        self.assertEqual({'oldap:Thing', Xsd_QName('crm:E22_Man-Made_Object')}, s)

    # @unittest.skip('Work in progress')
    def test_double_creation(self):
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:comment")),
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:test")),
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:testMyResMinimal"),
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)

        with self.assertRaises(OldapErrorAlreadyExists) as ex:
            r1.create()
        self.assertEqual(str(ex.exception), 'Object "test:testMyResMinimal" already exists.')

    def test_updating_resclass_attributes_add(self):
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:testMyRes"))
        r1.label.add("labello@it")
        r1.update()
        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:testMyRes"))
        self.assertEqual(r1.label, LangString("My Resource@en", "Meine Ressource@de", "Ma Resource@fr", "labello@it"))

    def test_updating_resclass_attributes(self):
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:testMyResMinimalA"))
        #self.assertTrue(r1.closed)
        r1[ResClassAttribute.LABEL] = LangString(["Minimal Resource@en", "Kleinste Resource@de", "Plus petite ressource@fr"])
        r1[ResClassAttribute.COMMENT] = LangString("Eine Beschreibung einer minimalen Ressource")
        r1[ResClassAttribute.SUPERCLASS] = Xsd_QName("test:testMyRes")
        r1.update()
        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:testMyResMinimalA"))
        self.assertEqual(LangString(["Minimal Resource@en", "Kleinste Resource@de", "Plus petite ressource@fr"]), r2.label)
        self.assertEqual(LangString("Eine Beschreibung einer minimalen Ressource"), r2.comment)
        self.assertEqual({Xsd_QName('test:testMyRes'), Xsd_QName('oldap:Thing')}, set(r2.superclass))


    def test_updating_add_ext_prop(self):
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:testMyResMinimalA"))
        self.assertTrue(r1.closed)

        r1[ResClassAttribute.LABEL] = LangString(["Minimal Resource@en", "Kleinste Resource@de", "Plus petite ressource@fr"])
        r1[ResClassAttribute.COMMENT] = LangString("Eine Beschreibung einer minimalen Ressource")
        r1[ResClassAttribute.SUPERCLASS] = Xsd_QName("test:testMyRes")
        r1[ResClassAttribute.CLOSED] = Xsd_boolean(False)

        #
        # Add an external, shared property defined by its own sh:PropertyShape instance
        #
        r1[Xsd_QName('test:test')] = HasProperty(con=self._connection,
                                           project=self._project,
                                           prop=Xsd_QName("test:test"),
                                           minCount=1,
                                           order=3,
                                           notifier=r1.notifier,
                                           notify_data=Xsd_QName("test:test"))
        r1.update()
        del r1
        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:testMyResMinimalA"))
        self.assertEqual(LangString(["Minimal Resource@en", "Kleinste Resource@de", "Plus petite ressource@fr"]), r2.label)
        self.assertEqual(LangString("Eine Beschreibung einer minimalen Ressource"), r2.comment)
        self.assertEqual({Xsd_QName('test:testMyRes'), Xsd_QName('oldap:Thing')}, set(r2.superclass))
        self.assertIsInstance(r2.superclass[Xsd_QName('test:testMyRes')], ResourceClass)
        self.assertFalse(r2[ResClassAttribute.CLOSED])

        prop1 = r2[Xsd_QName('test:test')].prop
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, Xsd_QName('test:test'))
        self.assertEqual(r2[Xsd_QName('test:test')].minCount, Xsd_integer(1))
        self.assertEqual(prop1.name, LangString("Test"))
        self.assertEqual(prop1.description, LangString("Property shape for testing purposes"))
        self.assertEqual(prop1.datatype, XsdDatatypes.string)
        self.assertEqual(r2[Xsd_QName('test:test')].order, Xsd_decimal(3))
        self.assertEqual(prop1.type, {OwlPropertyType.OwlDataProperty})

    def test_updating_add_int_prop(self):
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:testMyResMinimalB"))
        self.assertTrue(r1.closed)
        r1[ResClassAttribute.LABEL] = LangString(["Minimal Resource@en", "Kleinste Resource@de", "Plus petite ressource@fr"])
        r1[ResClassAttribute.COMMENT] = LangString("Eine Beschreibung einer minimalen Ressource")
        r1[ResClassAttribute.SUPERCLASS] = Xsd_QName("test:testMyRes")
        r1[ResClassAttribute.CLOSED] = Xsd_boolean(False)

        p = PropertyClass(con=self._connection,
                          project=self._project,
                          toClass=Xsd_QName('test:Person'))
        r1[Xsd_QName('dcterms:contributor')] = HasProperty(con=self._connection, project=self._project, prop=p, maxCount=Xsd_integer(1))

        r1.update()
        del r1
        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:testMyResMinimalB"))
        prop1 = r2[Xsd_QName('dcterms:contributor')].prop
        self.assertEqual(prop1.internal, Xsd_QName("test:testMyResMinimalB"))
        self.assertEqual(prop1.toClass, Xsd_QName('test:Person'))
        self.assertEqual(r2[Xsd_QName('dcterms:contributor')].maxCount, Xsd_integer(1))
        self.assertEqual(prop1.type, {OwlPropertyType.OwlObjectProperty})

    # @unittest.skip('Work in progress')
    def test_updating_add(self):
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:testMyResMinimalC"))
        self.assertTrue(r1.closed)
        r1[ResClassAttribute.LABEL] = LangString(["Minimal Resource@en", "Kleinste Resource@de", "Plus petite ressource@fr"])
        r1[ResClassAttribute.COMMENT] = LangString("Eine Beschreibung einer minimalen Ressource")
        r1[ResClassAttribute.SUPERCLASS] = Xsd_QName("test:testMyRes")
        r1[ResClassAttribute.CLOSED] = Xsd_boolean(False)

        #
        # Add an external, shared property defined by its own sh:PropertyShape instance
        #
        r1[Xsd_QName('test:test')] = HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:test"), minCount=1, order=3)

        #
        # Adding an internal, private property
        #
        p = PropertyClass(con=self._connection,
                          project=self._project,
                          toClass=Xsd_QName('test:Person'))
        r1[Xsd_QName('dcterms:creator')] = HasProperty(con=self._connection, project=self._project, prop=p, maxCount=Xsd_integer(1))

        p2 = PropertyClass(con=self._connection,
                           project=self._project,
                           datatype=XsdDatatypes.string,
                           inSet=RdfSet(Xsd_string('A'), Xsd_string('B'), Xsd_string('C'), Xsd_string('D'))
                           )
        r1[Xsd_QName('test:color')] = HasProperty(con=self._connection, project=self._project, prop=p2)
        r1.update()
        del r1
        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:testMyResMinimalC"))
        self.assertEqual(LangString(["Minimal Resource@en", "Kleinste Resource@de", "Plus petite ressource@fr"]), r2.label)
        self.assertEqual(LangString("Eine Beschreibung einer minimalen Ressource"), r2.comment)
        self.assertEqual({Xsd_QName("oldap:Thing"), Xsd_QName("test:testMyRes")}, set(r2.superclass))
        self.assertIsInstance(r2.superclass[Xsd_QName('test:testMyRes')], ResourceClass)
        self.assertFalse(r2[ResClassAttribute.CLOSED])

        prop1 = r2[Xsd_QName('test:test')].prop
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, Xsd_QName('test:test'))
        self.assertEqual(prop1.name, LangString("Test"))
        self.assertEqual(prop1.description, LangString("Property shape for testing purposes"))
        self.assertEqual(prop1.datatype, XsdDatatypes.string)
        self.assertEqual(prop1.type, {OwlPropertyType.OwlDataProperty})
        self.assertEqual(r2[Xsd_QName('test:test')].minCount, Xsd_integer(1))
        self.assertEqual(r2[Xsd_QName('test:test')].order, Xsd_decimal(3))

        prop2 = r2[Xsd_QName('dcterms:creator')].prop
        self.assertEqual(prop2.internal, Xsd_QName("test:testMyResMinimalC"))
        self.assertEqual(prop2.toClass, Xsd_QName('test:Person'))
        self.assertEqual(r2[Xsd_QName('dcterms:creator')].maxCount, Xsd_integer(1))
        self.assertEqual(prop1.type, {OwlPropertyType.OwlDataProperty})

        prop3 = r2[Xsd_QName('test:color')].prop
        self.assertEqual(prop3.internal, Xsd_QName("test:testMyResMinimalC"))
        self.assertEqual(prop3.inSet, RdfSet(Xsd_string('A'), Xsd_string('B'), Xsd_string('C'), Xsd_string('D')))

        sparql = self._context.sparql_context
        sparql += """
        SELECT ?p ?v
        FROM test:onto
        WHERE {
            test:testMyResMinimalC rdfs:subClassOf ?prop .
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
            test:testMyResMinimalC rdfs:subClassOf ?prop .
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

    # def test_temp(self):
    #     r1 = ResourceClass.read(con=self._connection,
    #                             project=self._project,
    #                             owl_class_iri=Iri("test:testMyRes"))
    #     r1[Iri('test:hasText')].maxCount = Xsd_integer(12)
    #     r1.update()
    #
    #     r2 = ResourceClass.read(con=self._connection,
    #                             project=self._project,
    #                             owl_class_iri=Iri("test:testMyRes"))
    #     self.assertEqual(r2[Iri('test:hasText')].maxCount, Xsd_integer(12))


    # @unittest.skip('Work in progress')
    def test_updating(self):
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:testMyRes"))
        self.assertEqual(r1[Xsd_QName('test:hasText')].maxCount, Xsd_integer(1))
        self.assertEqual(r1[Xsd_QName('test:hasText')].minCount, Xsd_integer(1))
        self.assertEqual(r1[Xsd_QName('test:hasText')].prop.languageIn, LanguageIn(Language.EN, Language.DE))
        self.assertEqual(r1[Xsd_QName('test:hasText')].prop.name, LangString(["A text@en", "Ein Text@de"]))

        r1.label[Language.IT] = "La mia risorsa"
        r1.closed = Xsd_boolean(False)
        r1[ResClassAttribute.SUPERCLASS] = {Xsd_QName("oldap:Thing"), Xsd_QName('dcterms:TopGaga')}
        r1[Xsd_QName('test:hasText')].prop.name[Language.FR] = "Un Texte Français"
        r1[Xsd_QName('test:hasText')].maxCount = Xsd_integer(12)  # TODO !!!!!!!!!!!!!!!!!!
        r1[Xsd_QName('test:hasText')].prop.languageIn = LanguageIn(Language.DE, Language.FR, Language.IT)
        r1[Xsd_QName('test:hasEnum')].prop.inSet = RdfSet(Xsd_string('L'), Xsd_string('a'), Xsd_string('b'))

        r1.update()

        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:testMyRes"))
        self.assertEqual(r2.label, LangString(["My Resource@en", "Meine Ressource@de", "Ma Resource@fr", "La mia risorsa@it"]))
        self.assertFalse(r2.closed)
        self.assertEqual({Xsd_QName("oldap:Thing"), Xsd_QName('dcterms:TopGaga')}, set(r2.superclass))
        self.assertIsNone(r2.superclass[Xsd_QName('dcterms:TopGaga')])
        self.assertEqual(r2[Xsd_QName('test:hasText')].prop.name, LangString(["A text@en", "Ein Text@de", "Un Texte Français@fr"]))
        self.assertEqual(r2[Xsd_QName('test:hasText')].maxCount, Xsd_integer(12))  # TODO !!!!!!!!!!!!!!!!
        self.assertEqual(r2[Xsd_QName('test:hasText')].prop.languageIn, LanguageIn(Language.DE, Language.FR, Language.IT))
        self.assertEqual(r2[Xsd_QName('test:hasEnum')].prop.inSet, RdfSet(Xsd_string('L'), Xsd_string('a'), Xsd_string('b')))

    def test_updating_sc_A(self):
        self._context[Xsd_NCName('crm')] = NamespaceIRI('http://www.cidoc-crm.org/cidoc-crm/')
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:p1'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["P1"]))
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=p1, order=1)
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:Crazy"),
                           superclass={"oldap:Thing", 'crm:E22_Man-Made_Object'},
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()
        del r1
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:Crazy'))
        del r1.superclass[Xsd_QName('crm:E22_Man-Made_Object')]
        r1.update()
        del r1
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:Crazy'))
        self.assertEqual({"oldap:Thing"}, set(r1.superclass))

    def test_updating_sc_B(self):
        self._context[Xsd_NCName('crm')] = NamespaceIRI('http://www.cidoc-crm.org/cidoc-crm/')
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:p2'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["P2"]))
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=p1, order=1)
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:CrazyB"),
                           superclass={"test:testMyRes", 'crm:E22_Man-Made_Object'},
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()
        del r1
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:CrazyB'))
        del r1.superclass[Xsd_QName("test:testMyRes")]
        r1.update()
        del r1
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:CrazyB'))
        self.assertEqual({Xsd_QName("oldap:Thing"), Xsd_QName('crm:E22_Man-Made_Object')}, set(r1.superclass))

    def test_updating_sc_C(self):
        self._context[Xsd_NCName('crm')] = NamespaceIRI('http://www.cidoc-crm.org/cidoc-crm/')
        self._context[Xsd_NCName('gaga')] = NamespaceIRI('http://gaga.com/ns/')
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:p3'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["P3"]))
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=p1, order=1)
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:CrazyC"),
                           superclass={"test:testMyRes", 'crm:E22_Man-Made_Object', 'test:testMyResMinimal'},
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()
        del r1
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:CrazyC'))
        del r1.superclass['test:testMyResMinimal']
        r1.superclass[Xsd_QName('gaga:DasWirdNichtGehen')] = None
        r1.update()
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:CrazyC'))
        self.assertEqual({"oldap:Thing",
                          "test:testMyRes",
                          'crm:E22_Man-Made_Object',
                          'gaga:DasWirdNichtGehen'}, set(r1.superclass))

    def test_updating_sc_D(self):
        self._context[Xsd_NCName('crm')] = NamespaceIRI('http://www.cidoc-crm.org/cidoc-crm/')
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:p4'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["P4"]))
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=p1, order=1)
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:CrazyD"),
                           superclass={"test:testMyRes", 'crm:E22_Man-Made_Object', 'test:testMyResMinimal'},
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()

        del r1[ResClassAttribute.LABEL]
        r1.update()
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:CrazyD'))
        self.assertIsNone(r1[ResClassAttribute.LABEL])

    def test_updating_sc_E(self):
        self._context[Xsd_NCName('crm')] = NamespaceIRI('http://www.cidoc-crm.org/cidoc-crm/')
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:p5'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["P5"]))
        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=p1, order=1)
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:CrazyE"),
                           superclass={"test:testMyRes", 'crm:E22_Man-Made_Object', 'test:testMyResMinimal'},
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()

        delattr(r1, 'label')
        r1.update()
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:CrazyE'))
        self.assertIsNone(r1[ResClassAttribute.LABEL])

    def test_updating_sc_F(self):
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:CrazyF"),
                           label=LangString(["LabelF english@en", "Label F french@fr"]),
                           comment=LangString("commentF english@en"))
        r1.create()
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:CrazyF'))
        del r1.label[Language.EN]
        r1.label.add("Label F italian@it")
        r1.update()
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName('test:CrazyF'))
        self.assertEqual(r1.label, LangString(["Label F french@fr", "Label F italian@it"]))
        #
        # Testing if also OWL ontology has been updated
        #
        sparql = self._context.sparql_context
        sparql += """
        SELECT ?label
        FROM test:onto
        WHERE {{
            test:CrazyF rdfs:label ?label .
        }}
        """
        jsonres = self._connection.query(sparql)
        res = QueryProcessor(self._context, jsonres)
        for r in res:
            self.assertIn(r['label'], [Xsd_string("Label F french@fr"), Xsd_string("Label F italian@it")])

    # @unittest.skip('Work in progress')
    def test_delete_props(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:propA'),
                           subPropertyOf=Xsd_QName('test:comment'),
                           datatype=XsdDatatypes.langString,
                           name=LangString(["Test property@en", "Testprädikat@de"]),
                           description=LangString("A property for testing...@en"),
                           uniqueLang=Xsd_boolean(True),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        p2 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:propB'),
                           toClass=Xsd_QName('test:testMyRes'),
                           name=LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]),
                           description=LangString("An exclusive property for testing...@en"))

        p3 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:propC'),
                           datatype=XsdDatatypes.int,
                           inSet=RdfSet(Xsd_integer(10), Xsd_integer(20), Xsd_integer(30)))

        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:comment"), order=1),
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:test"), order=2),
            HasProperty(con=self._connection, project=self._project, prop=p1, maxCount=Xsd_integer(1), minCount=Xsd_integer(1), order=3),
            HasProperty(con=self._connection, project=self._project, prop=p2, minCount=Xsd_integer(1), order=4),
            HasProperty(con=self._connection, project=self._project, prop=p3, order=5),
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:TestResourceDelProps"),
                           superclass="test:testMyResMinimal",
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)

        r1.create()

        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:TestResourceDelProps"), ignore_cache=True)
        del r2[Xsd_QName('test:propB')]
        del r2[Xsd_QName("test:test")]  # OWL is not yet removed (rdfs:subClassOf is still there)
        del r2[Xsd_QName('test:propC')]
        r2.update()

        r3 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:TestResourceDelProps"), ignore_cache=True)

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
                           property_class_iri=Xsd_QName('test:deleteA'),
                           subPropertyOf=Xsd_QName('test:comment'),
                           datatype=XsdDatatypes.langString,
                           name=LangString(["Test property@en", "Testprädikat@de"]),
                           description=LangString("A property for testing...@en"),
                           uniqueLang=Xsd_boolean(True),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        p2 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:deleteB'),
                           toClass=Iri('test:testMyRes'),
                           name=LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]),
                           description=LangString("A property for testing...@en"))

        p3 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:deleteC'),
                           datatype=XsdDatatypes.int,
                           inSet=RdfSet(Xsd_integer(10), Xsd_integer(20), Xsd_integer(30)))

        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:comment"), order=1),
            HasProperty(con=self._connection, project=self._project, prop=Xsd_QName("test:test"), order=2),
            HasProperty(con=self._connection, project=self._project, prop=p1, maxCount=Xsd_integer(1), minCount=Xsd_integer(1), order=3),
            HasProperty(con=self._connection, project=self._project, prop=p2, minCount=Xsd_integer(1), order=4),
            HasProperty(con=self._connection, project=self._project, prop=p3, order=5)
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:TestResourceDelete"),
                           superclass="test:testMyResMinimal",
                           label=LangString(["DeleteResTest@en", "EffaçerResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()
        del r1

        r2 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:TestResourceDelete"))
        r2.delete()

        self.assertTrue(check_res_empty(self._connection, self._context, Graph.SHACL, 'test:TestResourceDelete'))
        self.assertTrue(check_res_empty(self._connection, self._context, Graph.ONTO, 'test:TestResourceDelete'))
        superclass = ResourceClass.read(con=self._connection,
                                        project=self._project,
                                        owl_class_iri=Xsd_QName("test:testMyResMinimal"))
        self.assertEqual(Iri("test:testMyResMinimal"), superclass.owl_class_iri)

    # TODO!! TEST FAILES BECAUSE OF OBJECTFACTORY NOT YET FIXED!!!
    def test_in_use_case(self):
        p1 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:prop_A'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["Test property A@en", "Testprädikat A@de"]),
                           description=LangString("A property for testing...@en"))

        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=p1),
        ]
        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:TestResourceInUse"),
                           superclass="test:testMyResMinimal",
                           label=LangString(["CreateResTest@en", "CréationResTeste@fr"]),
                           comment=LangString("For testing purposes@en"),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()
        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:TestResourceInUse"), ignore_cache=True)

        factory = ResourceInstanceFactory(con=self._connection, project=self._project)
        TestResourceInUse = factory.createObjectInstance('TestResourceInUse')
        data = TestResourceInUse(
            label=['lanel_aaa@en', 'label_bbb@de'],
            comment=['comment_aaa@en', 'comment_bbb@de'],
            prop_A="WASELIWAS SOLL DENN DAS?",
            grantsPermission=Iri('oldap:GenericView')
        )
        data.create()
        data2 = TestResourceInUse.read(con=self._connection,
                                       iri=data.iri)


        with self.assertRaises(OldapErrorInUse):
            r1.delete()

        r1.del_superclasses("test:testMyResMinimal")
        with self.assertRaises(OldapErrorInUse):
            r1.update()

        r1 = ResourceClass.read(con=self._connection,
                                project=self._project,
                                owl_class_iri=Xsd_QName("test:TestResourceInUse"), ignore_cache=True)
        r1.add_superclasses("dcterms:waseliwas")
        with self.assertRaises(OldapErrorInUse):
            r1.update()


    # @unittest.skip('Work in progress')
    def test_write_trig(self):
        self._context[Xsd_NCName('andromeda')] = NamespaceIRI('http://andromeda.com/cluster1/')
        project_id = PropertyClass(con=self._connection,
                                   project=self._project,
                                   property_class_iri=Xsd_QName('test:projectId'),
                                   datatype=XsdDatatypes.langString,
                                   name=LangString(["Project ID@en", "Projekt ID@de"]),
                                   description=LangString(["Unique ID for project@en", "Eindeutige ID für Projekt@de"]),
                                   languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                                   uniqueLang=Xsd_boolean(True))
        project_name = PropertyClass(con=self._connection,
                                     project=self._project,
                                     property_class_iri=Xsd_QName('test:projectName'),
                                     datatype=XsdDatatypes.langString,
                                     name=LangString(["Project name@en", "Projektname@de"]),
                                     description=LangString(["A description of the project@en", "EineBeschreibung des Projekts@de"]),
                                     languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
                                     uniqueLang=Xsd_boolean(True))

        hasproperties: list[HasProperty] = [
            HasProperty(con=self._connection, project=self._project, prop=project_id, minCount=Xsd_integer(1), order=1),
            HasProperty(con=self._connection, project=self._project, prop=project_name, minCount=Xsd_integer(1), order=2)
        ]
        superclass = ResourceClass.read(con=self._connection,
                                        project=self._project,
                                        owl_class_iri=Xsd_QName("test:testMyResMinimal"))

        r1 = ResourceClass(con=self._connection,
                           project=self._project,
                           owlclass_iri=Xsd_QName("test:Project"),
                           superclass={"test:testMyResMinimal", Xsd_QName('andromeda:Cepheid42')},
                           label=LangString(["Project@en", "Projekt@de"]),
                           comment=LangString(["Definiton of a project@en", "Definition eines Projektes@de"]),
                           closed=Xsd_boolean(True),
                           hasproperties=hasproperties)
        r1.create()
        r1.label.add("projet@fr")
        r1.update()
        r1.read(con=self._connection,
                project=self._project,
                owl_class_iri=Xsd_QName("test:Project"), ignore_cache=True)
        r1.write_as_trig("gaga.trig")


if __name__ == '__main__':
    unittest.main()
