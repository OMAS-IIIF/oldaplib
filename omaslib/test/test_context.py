import unittest

from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, AnyIRI
from omaslib.src.helpers.omaserror import OmasError


class TestContext(unittest.TestCase):

    def test_context_constructor(self):
        context1 = Context(name="TEST")
        context2 = Context(name="TEST")
        context3 = Context(name="GAGA")
        self.assertTrue(context1 is context2)
        self.assertFalse(context1 is context3)
        self.assertEqual(context1['rdf'], NamespaceIRI('http://www.w3.org/1999/02/22-rdf-syntax-ns#'))
        with self.assertRaises(OmasError) as ex:
            gaga = context1['gaga']
        self.assertEqual(ex.exception.message, 'Unknown prefix "gaga"')

    def test_context_add(self):
        context = Context(name="TEST")
        context['test'] = "http://rdf.test.org/test/"
        self.assertEqual(context['test'], NamespaceIRI("http://rdf.test.org/test/"))
        context['test2'] = "http://rdf.test.org/test2#"
        self.assertEqual(context['test2'], NamespaceIRI("http://rdf.test.org/test2#"))
        with self.assertRaises(OmasError) as ex:
            context['test3'] = "http://rdf.test.org/test"
        self.assertEqual(ex.exception.message, "NamespaceIRI must end with '/' or '#'!")

    def test_context_del(self):
        context = Context(name="del")
        del context['rdfs']
        with self.assertRaises(OmasError) as ex:
            gaga = context['rdfs']
        self.assertEqual(ex.exception.message, 'Unknown prefix "rdfs"')
        with self.assertRaises(OmasError) as ex:
            del context['gugus']
        self.assertEqual(ex.exception.message, 'Unknown prefix "gugus"')

    def test_context_iri2qname(self):
        context = Context(name="iri2qname")
        qn = context.iri2qname(AnyIRI('http://www.w3.org/2000/01/rdf-schema#label'))
        self.assertEqual(qn, 'rdfs:label')
        qn = context.iri2qname(AnyIRI('http://www.w3.org/2004/02/skos/core#node'))
        self.assertEqual(qn, 'skos:node')
        qn = context.iri2qname(AnyIRI('http://www.gaga.org#label'))
        self.assertIsNone(qn)
        with self.assertRaises(OmasError) as ex:
            qn = context.iri2qname('waseliwas/soll')
        self.assertEqual(ex.exception.message, 'Invalid string "waseliwas/soll" for anyIRI')


