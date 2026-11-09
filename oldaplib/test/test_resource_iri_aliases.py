"""Full IRI reads must survive permission-filtered QName normalization."""

import unittest
from oldaplib.src.objectfactory import _alias_requested_subjects
from oldaplib.src.helpers.context import Context
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName as Q


class SubjectAliasTests(unittest.TestCase):
    def test_known_full_iri_and_qname_share_existing_result(self):
        ctx = Context(name="as09-alias")
        ctx["alias"] = NamespaceIRI("https://example.test/alias/")
        node = {Q("rdf:type"): Q("shared:ArchiveUnit")}
        full = Iri("https://example.test/alias/unit")
        result = _alias_requested_subjects(
            ctx, {Q("alias:unit"): node}, [full, Iri("alias:unit")]
        )
        self.assertIs(result[full], node)
        self.assertIs(result[Q("alias:unit")], node)

    def test_denied_unknown_and_unrequested_resources_are_not_added(self):
        ctx = Context(name="as09-alias-denied")
        ctx["alias"] = NamespaceIRI("https://example.test/alias/")
        data = {Q("alias:other"): {Q("rdf:type"): Q("shared:ArchiveUnit")}}
        result = _alias_requested_subjects(
            ctx, data, [Iri("https://example.test/alias/denied"), Iri("urn:absent")]
        )
        self.assertEqual(set(result), {Q("alias:other")})


class ConstructIntegerTests(unittest.TestCase):
    def test_int_zero_is_not_decoded_as_an_empty_string(self):
        from rdflib import Graph, URIRef, Literal, XSD
        from oldaplib.src.helpers.construct_processor import ConstructProcessor
        from oldaplib.src.xsd.xsd_int import Xsd_int

        ctx = Context(name="as09-int-zero")
        graph = Graph()
        graph.add(
            (
                URIRef("urn:integer-resource"),
                URIRef("https://schema.org/position"),
                Literal(0, datatype=XSD.int),
            )
        )
        result = ConstructProcessor.process(ctx, graph)
        value = result[Iri("urn:integer-resource")][Q("schema:position")]
        self.assertIsInstance(value, Xsd_int)
        self.assertEqual(int(value), 0)
