"""Structural tests for the shared archive ontology.

The tests keep the SHACL and OWL halves of ``shared.trig`` aligned without
requiring a running GraphDB instance.
"""

from pathlib import Path
import unittest

from rdflib import Dataset, Literal, Namespace, OWL, RDF, RDFS, XSD
from rdflib.collection import Collection
from rdflib.term import Identifier


SH = Namespace("http://www.w3.org/ns/shacl#")
SHARED = Namespace("http://oldap.org/shared#")
OLDAP = Namespace("http://oldap.org/base#")
SCHEMA = Namespace("https://schema.org/")
DCTERMS = Namespace("http://purl.org/dc/terms/")


class TestSharedArchiveOntology(unittest.TestCase):
    """Verify the archive vocabulary in both named graphs of ``shared.trig``."""

    @classmethod
    def setUpClass(cls) -> None:
        """Parse the bundled ontology once for all structural assertions."""
        ontology_path = Path(__file__).parents[1] / "ontologies" / "shared.trig"
        cls.dataset = Dataset()
        cls.dataset.parse(ontology_path, format="trig")
        cls.shacl = cls.dataset.graph(SHARED.shacl)
        cls.onto = cls.dataset.graph(SHARED.onto)

    def _property_shape(self, path: Identifier) -> Identifier:
        """Return the ArchiveUnit property shape for an RDF property path."""
        for property_shape in self.shacl.objects(SHARED.ArchiveUnitShape, SH.property):
            if self.shacl.value(property_shape, SH.path) == path:
                return property_shape
        self.fail(f"ArchiveUnitShape has no property shape for {path}")

    def test_archive_unit_shape_has_minimal_properties(self) -> None:
        """The SHACL shape exposes only the agreed minimal archive fields."""
        self.assertIn((SHARED.ArchiveUnitShape, SH.targetClass, SHARED.ArchiveUnit), self.shacl)

        expected_paths = {
            SCHEMA.name,
            SHARED.archiveLevel,
            SHARED.parentArchiveUnit,
            SCHEMA.identifier,
            SCHEMA.description,
            DCTERMS.temporal,
            SCHEMA.materialExtent,
            DCTERMS.creator,
            DCTERMS.provenance,
            SCHEMA.conditionsOfAccess,
            SCHEMA.about,
            SCHEMA.position,
            SHARED.hasMediaObject,
        }
        actual_paths = {
            self.shacl.value(property_shape, SH.path)
            for property_shape in self.shacl.objects(SHARED.ArchiveUnitShape, SH.property)
        }
        self.assertEqual(actual_paths, expected_paths)

        name_shape = self._property_shape(SCHEMA.name)
        self.assertEqual(self.shacl.value(name_shape, SH.minCount), Literal(1))
        self.assertEqual(self.shacl.value(name_shape, SH.uniqueLang), Literal(True))

        parent_shape = self._property_shape(SHARED.parentArchiveUnit)
        self.assertEqual(self.shacl.value(parent_shape, SH.maxCount), Literal(1))

        temporal_shape = self._property_shape(DCTERMS.temporal)
        self.assertEqual(self.shacl.value(temporal_shape, SH.maxCount), Literal(1))
        self.assertEqual(self.shacl.value(temporal_shape, SH["class"]), OLDAP.Dating)

        extent_shape = self._property_shape(SCHEMA.materialExtent)
        self.assertEqual(self.shacl.value(extent_shape, SH.datatype), RDF.langString)
        self.assertEqual(self.shacl.value(extent_shape, SH.uniqueLang), Literal(True))

        creator_shape = self._property_shape(DCTERMS.creator)
        self.assertEqual(self.shacl.value(creator_shape, SH["class"]), DCTERMS.Agent)
        self.assertIsNone(self.shacl.value(creator_shape, SH.maxCount))

        for path in (DCTERMS.provenance, SCHEMA.conditionsOfAccess):
            text_shape = self._property_shape(path)
            self.assertEqual(self.shacl.value(text_shape, SH.datatype), RDF.langString)
            self.assertEqual(self.shacl.value(text_shape, SH.uniqueLang), Literal(True))
            self.assertIsNone(self.shacl.value(text_shape, SH.minCount))

        about_shape = self._property_shape(SCHEMA.about)
        self.assertEqual(self.shacl.value(about_shape, SH["class"]), OLDAP.Thing)
        self.assertIsNone(self.shacl.value(about_shape, SH.minCount))
        self.assertIsNone(self.shacl.value(about_shape, SH.maxCount))

    def test_shared_graph_versions_match(self) -> None:
        """The SHACL and OWL graphs advertise the same ontology version."""
        shacl_version = self.shacl.value(SHARED.shapes, SCHEMA.version)
        ontology_version = self.onto.value(SHARED.ontology, OWL.versionInfo)
        self.assertEqual(shacl_version, ontology_version)
        self.assertEqual(shacl_version, Literal("0.6.0", datatype=XSD.string))

    def test_archive_levels_are_fixed_named_individuals(self) -> None:
        """SHACL and OWL use the same closed set of stable archive levels."""
        expected_levels = [
            SHARED.ArchiveGroup,
            SHARED.Fonds,
            SHARED.Subfonds,
            SHARED.Series,
            SHARED.Subseries,
            SHARED.File,
            SHARED.Item,
        ]

        level_shape = self._property_shape(SHARED.archiveLevel)
        self.assertEqual(self.shacl.value(level_shape, SH.minCount), Literal(1))
        self.assertEqual(self.shacl.value(level_shape, SH.maxCount), Literal(1))
        self.assertEqual(self.shacl.value(level_shape, SH["class"]), SHARED.ArchiveLevel)
        level_list = self.shacl.value(level_shape, SH["in"])
        self.assertIsNotNone(level_list)
        self.assertEqual(list(Collection(self.shacl, level_list)), expected_levels)

        for level in expected_levels:
            self.assertIn((level, RDF.type, OWL.NamedIndividual), self.onto)
            self.assertIn((level, RDF.type, SHARED.ArchiveLevel), self.onto)

    def test_archive_owl_definitions_match_shape(self) -> None:
        """OWL declares the class and the domains and ranges used by SHACL."""
        self.assertIn((SHARED.ArchiveUnit, RDFS.subClassOf, OLDAP.Thing), self.onto)
        self.assertIn((SHARED.ArchiveLevel, RDF.type, OWL.Class), self.onto)

        expected_properties = {
            SHARED.archiveLevel: SHARED.ArchiveLevel,
            SHARED.parentArchiveUnit: SHARED.ArchiveUnit,
            SHARED.hasMediaObject: SHARED.MediaObject,
        }
        for property_iri, range_iri in expected_properties.items():
            self.assertIn((property_iri, RDF.type, OWL.ObjectProperty), self.onto)
            self.assertIn((property_iri, RDFS.domain, SHARED.ArchiveUnit), self.onto)
            self.assertIn((property_iri, RDFS.range, range_iri), self.onto)

        self.assertIn((DCTERMS.temporal, RDF.type, OWL.ObjectProperty), self.onto)
        self.assertIn((DCTERMS.creator, RDF.type, OWL.ObjectProperty), self.onto)
        self.assertIn((DCTERMS.provenance, RDF.type, OWL.DatatypeProperty), self.onto)
        self.assertIn((SCHEMA.conditionsOfAccess, RDF.type, OWL.DatatypeProperty), self.onto)
        self.assertIn((SCHEMA.about, RDF.type, OWL.ObjectProperty), self.onto)
        self.assertNotIn((SCHEMA.about, RDFS.domain, SHARED.ArchiveUnit), self.onto)
        self.assertNotIn((SCHEMA.about, RDFS.range, OLDAP.Thing), self.onto)
        self.assertIn((SCHEMA.materialExtent, RDF.type, OWL.DatatypeProperty), self.onto)

    def test_reused_properties_are_registered_with_their_ontologies(self) -> None:
        """Every reused external property is registered under its own vocabulary."""
        expected_registrations = {
            SHARED.schema: {"materialExtent", "conditionsOfAccess"},
            SHARED.dcterms: {"provenance"},
        }
        for ontology, property_names in expected_registrations.items():
            for property_name in property_names:
                value = Literal(property_name, datatype=XSD.NCName)
                self.assertIn(
                    (ontology, OLDAP.proposedDatatypePropertyClass, value),
                    self.shacl,
                )

        about = Literal("about", datatype=XSD.NCName)
        self.assertIn(
            (SHARED.schema, OLDAP.proposedObjectPropertyClass, about),
            self.shacl,
        )


if __name__ == "__main__":
    unittest.main()
