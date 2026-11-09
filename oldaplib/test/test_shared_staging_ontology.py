"""Structural contract tests for project-neutral staging-area quota policy."""

from pathlib import Path
import unittest

from rdflib import Dataset, Literal, Namespace, OWL, RDF, RDFS, XSD


SH = Namespace("http://www.w3.org/ns/shacl#")
SHARED = Namespace("http://oldap.org/shared#")


class TestSharedStagingOntology(unittest.TestCase):
    """Keep the staging quota aligned between SHACL and OWL."""

    @classmethod
    def setUpClass(cls) -> None:
        dataset = Dataset()
        dataset.parse(
            Path(__file__).parents[1] / "ontologies" / "shared.trig",
            format="trig",
        )
        cls.shacl = dataset.graph(SHARED.shacl)
        cls.ontology = dataset.graph(SHARED.onto)

    def test_staging_area_requires_one_positive_integer_quota(self) -> None:
        """Keep admission quota mandatory, singular, and byte-based."""
        quota_shapes = [
            shape
            for shape in self.shacl.objects(SHARED.StagingAreaShape, SH.property)
            if self.shacl.value(shape, SH.path) == SHARED.stagingQuotaBytes
        ]
        self.assertEqual(len(quota_shapes), 1)
        quota_shape = quota_shapes[0]
        self.assertEqual(self.shacl.value(quota_shape, SH.datatype), XSD.integer)
        self.assertEqual(
            self.shacl.value(quota_shape, SH.minCount),
            Literal(1, datatype=XSD.integer),
        )
        self.assertEqual(
            self.shacl.value(quota_shape, SH.maxCount),
            Literal(1, datatype=XSD.integer),
        )
        self.assertEqual(
            self.shacl.value(quota_shape, SH.minInclusive),
            Literal(1, datatype=XSD.integer),
        )

    def test_staging_quota_is_declared_as_integer_datatype_property(self) -> None:
        """Keep the OWL property aligned with its SHACL datatype."""
        self.assertIn(
            (SHARED.stagingQuotaBytes, RDF.type, OWL.DatatypeProperty),
            self.ontology,
        )
        self.assertIn(
            (SHARED.stagingQuotaBytes, RDFS.range, XSD.integer),
            self.ontology,
        )
