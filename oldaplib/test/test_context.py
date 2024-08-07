import unittest

from oldaplib.src.helpers.context import Context
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.helpers.oldaperror import OldapError


class TestContext(unittest.TestCase):

    def test_context_constructor(self):
        context1 = Context(name="TEST")
        context2 = Context(name="TEST")
        context3 = Context(name="GAGA")
        self.assertTrue(context1 is context2)
        self.assertFalse(context1 is context3)
        self.assertEqual(context1['rdf'], NamespaceIRI('http://www.w3.org/1999/02/22-rdf-syntax-ns#'))
        with self.assertRaises(OldapError) as ex:
            gaga = context1['gaga']
        self.assertEqual(str(ex.exception), 'Unknown prefix "gaga"')

    def test_context_add(self):
        context = Context(name="TEST")
        context['test'] = "http://rdf.test.org/test/"
        self.assertEqual(context['test'], NamespaceIRI("http://rdf.test.org/test/"))
        context['test2'] = "http://rdf.test.org/test2#"
        self.assertEqual(context['test2'], NamespaceIRI("http://rdf.test.org/test2#"))
        with self.assertRaises(OldapError) as ex:
            context['test3'] = "http://rdf.test.org/test"
        self.assertEqual(str(ex.exception), "NamespaceIRI must end with '/' or '#'!")

    def test_context_del(self):
        context = Context(name="del")
        del context['rdfs']
        with self.assertRaises(OldapError) as ex:
            gaga = context['rdfs']
        self.assertEqual(str(ex.exception), 'Unknown prefix "rdfs"')
        with self.assertRaises(OldapError) as ex:
            del context['gugus']
        self.assertEqual(str(ex.exception), 'Unknown prefix "gugus"')

    def test_context_in_use(self):
        self.assertFalse(Context.in_use("in_use"))
        context = Context(name="in_use")
        self.assertTrue(Context.in_use("in_use"))

    def test_context_iri2qname(self):
        context = Context(name="iri2qname")
        qn = context.iri2qname(Xsd_anyURI('http://www.w3.org/2000/01/rdf-schema#label'))
        self.assertEqual(qn, 'rdfs:label')
        qn = context.iri2qname(Xsd_anyURI('http://www.w3.org/2004/02/skos/core#node'))
        self.assertEqual(qn, 'skos:node')
        qn = context.iri2qname(Xsd_anyURI('http://www.gaga.org#label'))
        self.assertIsNone(qn)
        with self.assertRaises(OldapError) as ex:
            qn = context.iri2qname('waseliwas/soll')
        self.assertEqual(str(ex.exception), 'Invalid string "waseliwas/soll" for anyURI')

    def test_context_qname2iri(self):
        context = Context(name='qname2iri')
        self.assertEqual(context.qname2iri(Xsd_QName('skos:gaga')), 'http://www.w3.org/2004/02/skos/core#gaga')
        with self.assertRaises(OldapError) as ex:
            qn = context.iri2qname('gaga')
        self.assertEqual(str(ex.exception), 'Invalid string "gaga" for anyURI')
        self.assertIsNone(context.iri2qname('abc:def'))
        t = Xsd_QName('xml:integer')
        self.assertEqual(context.qname2iri(t), 'http://www.w3.org/XML/1998/namespace#integer')

    def test_context_sparql(self):
        context = Context(name='sparql')
        context['test'] = "http://www.test.org/gaga#"
        expected ="""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX xml: <http://www.w3.org/XML/1998/namespace#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX schema: <http://schema.org/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX oldap: <http://oldap.org/base#>
PREFIX shared: <http://oldap.org/shared#>
PREFIX test: <http://www.test.org/gaga#>
"""
        self.assertEqual(context.sparql_context, expected)

    def test_context_turtle(self):
        context = Context(name='turtle')
        context['test'] = "http://www.test.org/gaga#"
        expected = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix schema: <http://schema.org/> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix oldap: <http://oldap.org/base#> .
@prefix shared: <http://oldap.org/shared#> .
@prefix test: <http://www.test.org/gaga#> .
"""
        self.maxDiff = None
        self.assertEqual(context.turtle_context, expected)


