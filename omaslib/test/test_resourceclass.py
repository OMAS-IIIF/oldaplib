import unittest
from datetime import datetime
from enum import Enum
from time import sleep
from typing import Dict, List, Union

from xmlschema import XsdType

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName, NCName, AnyIRI
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.omaserror import OmasErrorNotFound, OmasErrorAlreadyExists
from omaslib.src.helpers.propertyclassattr import PropertyClassAttribute
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.semantic_version import SemanticVersion
from omaslib.src.helpers.tools import lprint
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.propertyclass import PropertyClassAttributesContainer, PropertyClass, OwlPropertyType
from omaslib.src.propertyrestrictions import PropertyRestrictions, PropertyRestrictionType
from omaslib.src.resourceclass import ResourceClassAttributesContainer, ResourceClass
from omaslib.src.helpers.resourceclassattr import ResourceClassAttribute


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
    res = con.rdflib_query(sparql)
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
    res = con.rdflib_query(sparql)
    return len(res) == 0


class TestResourceClass(unittest.TestCase):
    _context: Context
    _connection: Connection

    @classmethod
    def setUpClass(cls):
        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://omas.org/test#")
        cls._context.use('test', 'dcterms')

        cls._connection = Connection(server='http://localhost:7200',
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     repo="omas",
                                     context_name="DEFAULT")

        cls._connection.clear_graph(QName('test:shacl'))
        cls._connection.clear_graph(QName('test:onto'))
        cls._connection.clear_graph(QName('dcterms:shacl'))
        cls._connection.clear_graph(QName('dcterms:onto'))
        cls._connection.upload_turtle("omaslib/testdata/connection_test.trig")
        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(QName('test:shacl'))
        #cls._connection.clear_graph(QName('test:onto'))
        pass

    #@unittest.skip('Work in progress')
    def test_constructor(self):
        attrs: PropertyClassAttributesContainer = {
            PropertyClassAttribute.SUBPROPERTY_OF: QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.NAME: LangString(["Test property@en", "Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("A property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 5
        }
        p1 = PropertyClass(con=self._connection,
                          graph=NCName('test'),
                          property_class_iri=QName('test:testprop'), attrs=attrs)

        attrs: PropertyClassAttributesContainer = {
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.NAME: LangString(["Test enum@en", "Enumerationen@de"]),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.IN: {"yes", "maybe", "no"}
                }),
            PropertyClassAttribute.ORDER: 6
        }
        p2 = PropertyClass(con=self._connection,
                          graph=NCName('test'),
                          property_class_iri=QName('test:enumprop'), attrs=attrs)

        properties: List[Union[PropertyClass, QName]] = [
            QName("test:comment"),
            QName("test:test"),
            p1, p2
        ]

        rattrs: ResourceClassAttributesContainer = {
            ResourceClassAttribute.LABEL: LangString(["Test resource@en", "Resource de test@fr"]),
            ResourceClassAttribute.COMMENT: LangString("For testing purposes@en"),
            ResourceClassAttribute.CLOSED: True
        }
        r1 = ResourceClass(con=self._connection,
                           graph=NCName('test'),
                           owlclass_iri=QName("test:TestResource"),
                           attrs=rattrs,
                           properties=properties)
        self.assertEqual(r1[ResourceClassAttribute.LABEL], LangString(["Test resource@en", "Resource de test@fr"]))
        self.assertEqual(r1[ResourceClassAttribute.COMMENT], LangString("For testing purposes@en"))
        self.assertTrue(r1[ResourceClassAttribute.CLOSED])

        prop1 = r1[QName("test:comment")]
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, QName("test:comment"))
        self.assertEqual(prop1[PropertyClassAttribute.DATATYPE], XsdDatatypes.string)
        self.assertEqual(prop1[PropertyClassAttribute.NAME], LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(prop1[PropertyClassAttribute.DESCRIPTION], LangString("This is a test property@de"))
        self.assertEqual(prop1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(prop1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG], True)

        prop2 = r1[QName("test:test")]
        self.assertIsNone(prop2.internal)
        self.assertEqual(prop2.property_class_iri, QName("test:test"))
        self.assertEqual(prop2.get(PropertyClassAttribute.TO_NODE_IRI), QName('test:comment'))
        self.assertEqual(prop2.get(PropertyClassAttribute.DESCRIPTION), LangString("Property shape for testing purposes"))
        self.assertEqual(prop2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MIN_COUNT), 1)
        self.assertEqual(prop2.get(PropertyClassAttribute.ORDER), 3)

        prop3 = r1[QName("test:testprop")]
        self.assertEqual(prop3.internal, QName('test:TestResource'))
        self.assertEqual(prop3.property_class_iri, QName("test:testprop"))
        self.assertEqual(prop3.get(PropertyClassAttribute.PROPERTY_TYPE), OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop3.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertEqual(prop3.get(PropertyClassAttribute.NAME), LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(prop3.get(PropertyClassAttribute.ORDER), 5)
        self.assertEqual(prop3.get(PropertyClassAttribute.SUBPROPERTY_OF), QName("test:comment"))
        self.assertEqual(prop3[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MAX_COUNT), 1)
        self.assertEqual(prop3[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG], True)
        self.assertEqual(prop3[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN], {Language.EN, Language.DE, Language.FR, Language.IT})

        prop4 = r1[QName("test:enumprop")]
        self.assertEqual(prop4[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.IN],
                         {"yes", "maybe", "no"})

    #@unittest.skip('Work in progress')
    def test_reading(self):
        r1 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName('test:testMyRes'))
        self.assertEqual(r1.owl_class_iri, QName('test:testMyRes'))
        self.assertEqual(r1.version, SemanticVersion(1, 0, 0))
        self.assertEqual(r1.creator, AnyIRI('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(r1.created, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(r1.contributor, AnyIRI('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(r1.modified, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(r1.get(ResourceClassAttribute.LABEL), LangString(["My Resource@en", "Meine Ressource@de", "Ma Resource@fr"]))
        self.assertEqual(r1.get(ResourceClassAttribute.COMMENT), LangString("Resource for testing..."))
        self.assertEqual(r1.get(ResourceClassAttribute.CLOSED), True)

        prop1 = r1[QName('test:test')]
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, QName("test:test"))
        self.assertEqual(prop1.version, SemanticVersion(1, 0, 0))
        self.assertEqual(prop1.creator, AnyIRI('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop1.created, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(prop1.contributor, AnyIRI('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop1.modified, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(prop1.get(PropertyClassAttribute.PROPERTY_TYPE), OwlPropertyType.OwlObjectProperty)
        self.assertEqual(prop1.get(PropertyClassAttribute.TO_NODE_IRI), QName('test:comment'))
        self.assertEqual(prop1.get(PropertyClassAttribute.DESCRIPTION), LangString("Property shape for testing purposes"))
        self.assertEqual(prop1[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MIN_COUNT), 1)
        self.assertEqual(prop1.get(PropertyClassAttribute.ORDER), 3)

        prop2 = r1[QName('test:hasText')]
        self.assertEqual(prop2.internal, QName('test:testMyRes'))
        self.assertEqual(prop2.property_class_iri, QName("test:hasText"))
        self.assertEqual(prop2.version, SemanticVersion(1, 0, 0))
        self.assertEqual(prop2.creator, AnyIRI('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop2.created, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(prop2.contributor, AnyIRI('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop2.modified, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(prop2.get(PropertyClassAttribute.PROPERTY_TYPE), OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop2.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertEqual(prop2.get(PropertyClassAttribute.NAME), LangString(["A text", "Ein Text@de"]))
        self.assertEqual(prop2.get(PropertyClassAttribute.DESCRIPTION), LangString("A longer text..."))
        self.assertEqual(prop2.get(PropertyClassAttribute.ORDER), 1)
        self.assertEqual(prop2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MIN_COUNT), 1)
        self.assertEqual(prop2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MAX_COUNT), 1)

        prop3 = r1[QName('test:hasEnum')]
        self.assertEqual(prop3.get(PropertyClassAttribute.PROPERTY_TYPE), OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop3.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertEqual(prop3[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.IN),
                         {'red', 'green', 'blue', 'yellow'})

    #@unittest.skip('Work in progress')
    def test_creating(self):
        props1: PropertyClassAttributesContainer = {
            PropertyClassAttribute.SUBPROPERTY_OF: QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.NAME: LangString(["Test property@en", "Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("A property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 1
        }
        p1 = PropertyClass(con=self._connection,
                           graph=NCName('test'),
                           property_class_iri=QName('test:testone'),
                           attrs=props1)

        props2: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: QName('test:testMyRes'),
            PropertyClassAttribute.NAME: LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("An exclusive property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 2
        }
        p2 = PropertyClass(con=self._connection,
                           graph=NCName('test'),
                           property_class_iri=QName('test:testtwo'),
                           attrs=props2)

        props3: PropertyClassAttributesContainer = {
            PropertyClassAttribute.DATATYPE: XsdDatatypes.int,
            PropertyClassAttribute.NAME: LangString(["E.N.U.M@en"]),
            PropertyClassAttribute.DESCRIPTION: LangString("An exclusive enum testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.IN: {1, 2, 3}
                }),
            PropertyClassAttribute.ORDER: 3
        }
        p3 = PropertyClass(con=self._connection,
                           graph=NCName('test'),
                           property_class_iri=QName('test:testthree'),
                           attrs=props3)

        properties: List[Union[PropertyClass, QName]] = [
            QName("test:comment"),
            QName("test:test"),
            p1, p2, p3
        ]
        attrs: ResourceClassAttributesContainer = {
            ResourceClassAttribute.LABEL: LangString(["CreateResTest@en", "CréationResTeste@fr"]),
            ResourceClassAttribute.COMMENT: LangString("For testing purposes@en"),
            ResourceClassAttribute.CLOSED: True
        }
        r1 = ResourceClass(con=self._connection,
                           graph=NCName('test'),
                           owlclass_iri=QName("test:TestResource"),
                           attrs=attrs,
                           properties=properties)

        r1.create()

        r2 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName("test:TestResource"))
        self.assertEqual(r2.owl_class_iri, QName("test:TestResource"))
        self.assertEqual(r2[ResourceClassAttribute.LABEL], LangString(["CreateResTest@en", "CréationResTeste@fr"]))
        self.assertEqual(r2[ResourceClassAttribute.COMMENT], LangString("For testing purposes@en"))
        self.assertTrue(r2[ResourceClassAttribute.COMMENT])

        prop1 = r2[QName("test:comment")]
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, QName('test:comment'))
        self.assertEqual(prop1.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertTrue(prop1.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(prop1.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(prop1.get(PropertyClassAttribute.NAME), LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(prop1.get(PropertyClassAttribute.DESCRIPTION), LangString("This is a test property@de"))
        self.assertIsNone(prop1.get(PropertyClassAttribute.SUBPROPERTY_OF))
        self.assertEqual(prop1[PropertyClassAttribute.ORDER], 2)
        self.assertEqual(prop1.get(PropertyClassAttribute.PROPERTY_TYPE), OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop1.creator, AnyIRI('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(prop1.created, datetime.fromisoformat("2023-11-04T12:00:00Z"))

        prop2 = r2[QName("test:test")]
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop2.property_class_iri, QName('test:test'))
        self.assertEqual(prop2[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(prop2[PropertyClassAttribute.NAME], LangString("Test"))
        self.assertEqual(prop2[PropertyClassAttribute.DESCRIPTION], LangString("Property shape for testing purposes"))
        self.assertEqual(prop2[PropertyClassAttribute.TO_NODE_IRI], QName('test:comment'))
        self.assertEqual(prop2[PropertyClassAttribute.ORDER], 3)
        self.assertEqual(prop2[PropertyClassAttribute.PROPERTY_TYPE], OwlPropertyType.OwlObjectProperty)

        prop3 = r2[QName("test:testone")]
        self.assertEqual(prop3.internal, QName("test:TestResource"))
        self.assertEqual(prop3.property_class_iri, QName("test:testone"))
        self.assertEqual(prop3.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertEqual(prop3.get(PropertyClassAttribute.NAME), LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(prop3.get(PropertyClassAttribute.DESCRIPTION), LangString("A property for testing...@en"))
        self.assertEqual(prop3.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(prop3.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(prop3.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.LANGUAGE_IN], {Language.EN, Language.DE, Language.FR, Language.IT})
        self.assertTrue(prop3.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(prop3.get(PropertyClassAttribute.ORDER), 1)

        prop4 = r2[QName("test:testtwo")]
        self.assertEqual(prop4.internal, QName("test:TestResource"))
        self.assertEqual(prop4.property_class_iri, QName("test:testtwo"))
        self.assertEqual(prop4.get(PropertyClassAttribute.TO_NODE_IRI), QName('test:testMyRes'))
        self.assertEqual(prop4.get(PropertyClassAttribute.NAME), LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]))
        self.assertEqual(prop4.get(PropertyClassAttribute.DESCRIPTION), LangString("An exclusive property for testing...@en"))
        self.assertEqual(prop4.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(prop4.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.LANGUAGE_IN], {Language.EN, Language.DE, Language.FR, Language.IT})
        self.assertTrue(prop4.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(prop4.get(PropertyClassAttribute.ORDER), 2)

        prop5 = r2[QName("test:testthree")]
        self.assertEqual(prop5.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.IN], {1, 2, 3})

    #@unittest.skip('Work in progress')
    def test_double_creation(self):
        properties: List[Union[PropertyClass, QName]] = [
            QName("test:comment"),
            QName("test:test"),
        ]
        attrs: ResourceClassAttributesContainer = {
            ResourceClassAttribute.LABEL: LangString(["CreateResTest@en", "CréationResTeste@fr"]),
            ResourceClassAttribute.COMMENT: LangString("For testing purposes@en"),
            ResourceClassAttribute.CLOSED: True
        }
        r1 = ResourceClass(con=self._connection,
                           graph=NCName('test'),
                           owlclass_iri=QName("test:testMyResMinimal"),
                           attrs=attrs,
                           properties=properties)

        with self.assertRaises(OmasErrorAlreadyExists) as ex:
            r1.create()
        self.assertEqual(str(ex.exception), 'Object "test:testMyResMinimal" already exists.')


    #@unittest.skip('Work in progress')
    def test_updating_add(self):
        r1 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName("test:testMyResMinimal"))
        r1[ResourceClassAttribute.LABEL] = LangString(["Minimal Resource@en", "Kleinste Resource@de"])
        r1[ResourceClassAttribute.COMMENT] = LangString("Eine Beschreibung einer minimalen Ressource")
        r1[ResourceClassAttribute.SUBCLASS_OF] = QName('test:testMyRes')
        r1[ResourceClassAttribute.CLOSED] = True
        #
        # Add an external, shared property defined by its own sh:PropertyShape instance
        #
        r1[QName('test:test')] = None

        #
        # Adding an internal, private property
        #
        attrs: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: QName('test:Person'),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={PropertyRestrictionType.MAX_COUNT: 1}),
        }
        p = PropertyClass(con=self._connection,
                          graph=NCName('test'),
                          attrs=attrs)
        r1[QName('dcterms:creator')] = p

        attrs2: PropertyClassAttributesContainer = {
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={PropertyRestrictionType.IN: {'A', 'B', 'C', 'D'}}),
        }
        p2 = PropertyClass(con=self._connection,
                           graph=NCName('test'),
                           attrs=attrs2)
        r1[QName('test:color')] = p2
        r1.update()

        r2 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName("test:testMyResMinimal"))
        self.assertEqual(r2.get(ResourceClassAttribute.LABEL), LangString(["Minimal Resource@en", "Kleinste Resource@de"]))
        self.assertEqual(r2.get(ResourceClassAttribute.COMMENT), LangString("Eine Beschreibung einer minimalen Ressource"))
        self.assertEqual(r2.get(ResourceClassAttribute.SUBCLASS_OF), QName('test:testMyRes'))
        self.assertTrue(r2.get(ResourceClassAttribute.CLOSED))

        prop1 = r2[QName('test:test')]
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, QName('test:test'))
        self.assertEqual(prop1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(prop1[PropertyClassAttribute.NAME], LangString("Test"))
        self.assertEqual(prop1[PropertyClassAttribute.DESCRIPTION], LangString("Property shape for testing purposes"))
        self.assertEqual(prop1[PropertyClassAttribute.TO_NODE_IRI], QName('test:comment'))
        self.assertEqual(prop1[PropertyClassAttribute.ORDER], 3)
        self.assertEqual(prop1[PropertyClassAttribute.PROPERTY_TYPE], OwlPropertyType.OwlObjectProperty)

        prop2 = r2[QName('dcterms:creator')]
        self.assertEqual(prop2.internal, QName("test:testMyResMinimal"))
        self.assertEqual(prop2.get(PropertyClassAttribute.TO_NODE_IRI), QName('test:Person'))
        self.assertEqual(prop2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MAX_COUNT), 1)
        self.assertEqual(prop1[PropertyClassAttribute.PROPERTY_TYPE], OwlPropertyType.OwlObjectProperty)

        prop3 = r2[QName('test:color')]
        self.assertEqual(prop3.internal, QName("test:testMyResMinimal"))
        self.assertEqual(prop3[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.IN),
                         {'A', 'B', 'C', 'D'})

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
            QName('rdf:type'): 'owl:Restriction',
            QName('owl:onProperty'): 'dcterms:creator',
            QName('owl:maxCardinality'): 1
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
            QName('rdf:type'): 'owl:Restriction',
            QName('owl:onProperty'): 'test:test',
            QName('owl:minCardinality'): 1
        }
        for r in res:
            p = r['p']
            v = r['v']
            self.assertEqual(result[p], v)

    #@unittest.skip('Work in progress')
    def test_updating(self):
        r1 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName("test:testMyRes"))
        self.assertEqual(r1[QName('test:hasText')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(r1[QName('test:hasText')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(r1[QName('test:hasText')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN], {Language.EN, Language.DE})
        r1[ResourceClassAttribute.LABEL][Language.IT] = "La mia risorsa"
        r1[ResourceClassAttribute.CLOSED] = False
        r1[ResourceClassAttribute.SUBCLASS_OF] = QName('test:TopGaga')
        r1[QName('test:hasText')][PropertyClassAttribute.NAME][Language.FR] = "Un Texte Français"
        r1[QName('test:hasText')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MAX_COUNT] = 12
        r1[QName('test:hasText')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN] = {Language.DE, Language.FR, Language.IT}
        r1[QName('test:hasEnum')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.IN] = {'L', 'a', 'b'}
        r1.update()

        r2 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName("test:testMyRes"))
        self.assertEqual(r2.get(ResourceClassAttribute.LABEL), LangString(["My Resource@en", "Meine Ressource@de", "Ma Resource@fr", "La mia risorsa@it"]))
        self.assertFalse(r2.get(ResourceClassAttribute.CLOSED))
        self.assertEqual(r2.get(ResourceClassAttribute.SUBCLASS_OF), QName('test:TopGaga'))
        self.assertEqual(r2[QName('test:hasText')][PropertyClassAttribute.NAME], LangString(["A text", "Ein Text@de", "Un Texte Français@fr"]))
        self.assertEqual(r2[QName('test:hasText')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MAX_COUNT], 12)
        self.assertEqual(r2[QName('test:hasText')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN], {Language.DE, Language.FR, Language.IT})
        self.assertEqual(r2[QName('test:hasEnum')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.IN], {'L', 'a', 'b'})

    #@unittest.skip('Work in progress')
    def test_delete_props(self):
        attrs1: PropertyClassAttributesContainer = {
            PropertyClassAttribute.SUBPROPERTY_OF: QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.NAME: LangString(["Test property@en", "Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("A property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 1
        }
        p1 = PropertyClass(con=self._connection,
                           graph=NCName('test'),
                           property_class_iri=QName('test:propA'),
                           attrs=attrs1)

        attrs2: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: QName('test:testMyRes'),
            PropertyClassAttribute.NAME: LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("An exclusive property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 2
        }
        p2 = PropertyClass(con=self._connection,
                           graph=NCName('test'),
                           property_class_iri=QName('test:propB'),
                           attrs=attrs2)

        attrs3: PropertyClassAttributesContainer = {
            PropertyClassAttribute.DATATYPE: XsdDatatypes.int,
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.IN: {10, 20, 30}
                }),
        }
        p3 = PropertyClass(con=self._connection,
                           graph=NCName('test'),
                           property_class_iri=QName('test:propC'),
                           attrs=attrs3)

        properties: List[Union[PropertyClass, QName]] = [
            QName("test:comment"),
            QName("test:test"),
            p1, p2, p3
        ]
        attrs: ResourceClassAttributesContainer = {
            ResourceClassAttribute.LABEL: LangString(["CreateResTest@en", "CréationResTeste@fr"]),
            ResourceClassAttribute.COMMENT: LangString("For testing purposes@en"),
            ResourceClassAttribute.CLOSED: True
        }
        r1 = ResourceClass(con=self._connection,
                           graph=NCName('test'),
                           owlclass_iri=QName("test:TestResourceDelProps"),
                           attrs=attrs,
                           properties=properties)

        r1.create()

        r2 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName("test:TestResourceDelProps"))
        del r2[QName('test:propB')]
        del r2[QName("test:test")]  # OWL is not yet removed (rdfs:subClassOf is still there)
        del r2[QName('test:propC')]
        r2.update()

        r3 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName("test:TestResourceDelProps"))

        self.assertTrue(check_prop_empty(self._connection, self._context, Graph.SHACL, 'test:testMyResMinimal', 'test:propB'))
        self.assertTrue(check_prop_empty(self._connection, self._context, Graph.ONTO, 'test:testMyResMinimal', 'test:propB'))

        self.assertTrue(check_prop_empty(self._connection, self._context, Graph.SHACL, 'test:testMyResMinimal', 'test:test'))
        self.assertTrue(check_prop_empty(self._connection, self._context, Graph.ONTO, 'test:testMyResMinimal', 'test:test'))

        self.assertTrue(check_prop_empty(self._connection, self._context, Graph.SHACL, 'test:testMyResMinimal', 'test:propC'))
        self.assertTrue(check_prop_empty(self._connection, self._context, Graph.ONTO, 'test:testMyResMinimal', 'test:propC'))

    #@unittest.skip('Work in progress')
    def test_delete(self):
        attrs1: PropertyClassAttributesContainer = {
            PropertyClassAttribute.SUBPROPERTY_OF: QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.NAME: LangString(["Test property@en", "Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("A property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 1
        }
        p1 = PropertyClass(con=self._connection,
                           graph=NCName('test'),
                           property_class_iri=QName('test:deleteA'),
                           attrs=attrs1)

        attrs2: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: QName('test:testMyRes'),
            PropertyClassAttribute.NAME: LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("An exclusive property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 2
        }
        p2 = PropertyClass(con=self._connection,
                           graph=NCName('test'),
                           property_class_iri=QName('test:deleteB'),
                           attrs=attrs2)

        attrs3: PropertyClassAttributesContainer = {
            PropertyClassAttribute.DATATYPE: XsdDatatypes.int,
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.IN: {10, 20, 30}
                }),
        }
        p3 = PropertyClass(con=self._connection,
                           graph=NCName('test'),
                           property_class_iri=QName('test:deleteC'),
                           attrs=attrs3)

        properties: List[Union[PropertyClass, QName]] = [
            QName("test:comment"),
            QName("test:test"),
            p1, p2, p3
        ]
        attrs: ResourceClassAttributesContainer = {
            ResourceClassAttribute.LABEL: LangString(["DeleteResTest@en", "EffaçerResTeste@fr"]),
            ResourceClassAttribute.COMMENT: LangString("For testing purposes@en"),
            ResourceClassAttribute.CLOSED: True
        }
        r1 = ResourceClass(con=self._connection,
                           graph=NCName('test'),
                           owlclass_iri=QName("test:TestResourceDelete"),
                           attrs=attrs,
                           properties=properties)

        r1.create()
        del r1

        r2 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName("test:TestResourceDelete"))
        r2.delete()

        self.assertTrue(check_res_empty(self._connection, self._context, Graph.SHACL, 'test:TestResourceDelete'))
        self.assertTrue(check_res_empty(self._connection, self._context, Graph.ONTO, 'test:TestResourceDelete'))

    #@unittest.skip('Work in progress')
    def test_write_trig(self):
        project_id = PropertyClass(con=self._connection,
                                   graph=NCName('test'),
                                   property_class_iri=QName('test:projectId'),
                                   attrs={
                                       PropertyClassAttribute.DATATYPE: XsdDatatypes.NCName,
                                       PropertyClassAttribute.NAME: LangString([
                                           "Project ID@en", "Projekt ID@de"
                                       ]),
                                       PropertyClassAttribute.DESCRIPTION: LangString([
                                           "Unique ID for project@en", "Eindeutige ID für Projekt@de"
                                       ]),
                                       PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(restrictions={
                                           PropertyRestrictionType.MIN_COUNT: 1,
                                           PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT},
                                           PropertyRestrictionType.UNIQUE_LANG: True
                                       }),
                                       PropertyClassAttribute.ORDER: 1
                                   })
        project_name = PropertyClass(con=self._connection,
                                     graph=NCName('test'),
                                     property_class_iri=QName('test:projectName'),
                                     attrs={
                                         PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
                                         PropertyClassAttribute.NAME: LangString([
                                             "Project name@en", "Projektname@de"
                                         ]),
                                         PropertyClassAttribute.DESCRIPTION: LangString([
                                             "A description of the project@en", "EineBeschreibung des Projekts@de"
                                         ]),
                                         PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(restrictions={
                                             PropertyRestrictionType.MIN_COUNT: 1,
                                             PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT},
                                             PropertyRestrictionType.UNIQUE_LANG: True
                                         }),
                                         PropertyClassAttribute.ORDER: 2
                                     })

        properties: List[Union[PropertyClass, QName]] = [
            project_id, project_name
        ]
        attrs: ResourceClassAttributesContainer = {
            ResourceClassAttribute.LABEL: LangString(["Project@en", "Projekt@de"]),
            ResourceClassAttribute.COMMENT: LangString(["Definiton of a project@en", "Definition eines Projektes@de"]),
            ResourceClassAttribute.CLOSED: True
        }
        r1 = ResourceClass(con=self._connection,
                           graph=NCName('test'),
                           owlclass_iri=QName("test:Project"),
                           attrs=attrs,
                           properties=properties)
        r1.write_as_trig("gaga.trig")

