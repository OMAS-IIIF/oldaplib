"""Validate optional private-repository links without GraphDB or project fixtures.

Only the actual StagingFolder shape is selected for instance validation: media
and archive-unit descriptions have separate required metadata outside this test's
scope. Target class checks still use the real Shared ontology and project-style
subclass declarations. No RDF range inference is used to mask invalid targets.
"""

from pathlib import Path
import unittest

from owlrl import DeductiveClosure, RDFS_Semantics
from pyshacl import validate
from rdflib import BNode, Dataset, Graph, Literal, Namespace, OWL, RDF, RDFS

SH = Namespace("http://www.w3.org/ns/shacl#")
SHARED = Namespace("http://oldap.org/shared#")
SCHEMA = Namespace("https://schema.org/")
EX = Namespace("https://example.org/repository/")


class TestSharedRepositoryOntology(unittest.TestCase):
    """Keep folder links optional, independently typed and project-neutral."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the real vocabulary and the complete folder-shape blank-node closure."""
        dataset = Dataset()
        dataset.parse(
            Path(__file__).parents[1] / "ontologies" / "shared.trig", format="trig"
        )
        cls.ontology = dataset.graph(SHARED.onto)
        shapes = dataset.graph(SHARED.shacl)
        cls.folder_shapes = Graph()
        pending = [SHARED.StagingFolderShape]
        visited = set()
        while pending:
            subject = pending.pop()
            if subject in visited:
                continue
            visited.add(subject)
            for triple in shapes.triples((subject, None, None)):
                cls.folder_shapes.add(triple)
                if isinstance(triple[2], BNode):
                    pending.append(triple[2])

    def _folder(self, folder=EX.folder) -> Graph:
        """Return a legacy-valid folder with no new relationships."""
        graph = Graph()
        graph.add((folder, RDF.type, SHARED.StagingFolder))
        graph.add((folder, SCHEMA.name, Literal("Original working folder")))
        graph.add((folder, SHARED.inStagingArea, EX.area))
        graph.add((EX.area, RDF.type, SHARED.StagingArea))
        return graph

    def _assert_conforms(self, graph: Graph, expected: bool = True) -> None:
        """Check SHACL class/cardinality constraints without inferring range types."""
        conforms, _, report = validate(
            graph,
            shacl_graph=self.folder_shapes,
            ont_graph=self.ontology,
            inference="none",
        )
        self.assertEqual(conforms, expected, report)

    def test_old_folders_remain_valid_without_links(self) -> None:
        """Existing data requires neither a mapping nor a media reference."""
        self._assert_conforms(self._folder())

    def test_new_shapes_match_owl_and_have_multilingual_labels(self) -> None:
        """The two links have precise ranges and no minimum cardinality."""
        for path, target, maximum in (
            (SHARED.defaultArchiveUnit, SHARED.ArchiveUnit, 1),
            (SHARED.referencedMediaObject, SHARED.MediaObject, None),
        ):
            with self.subTest(property=path):
                matches = list(self.folder_shapes.subjects(SH.path, path))
                self.assertEqual(len(matches), 1)
                shape = matches[0]
                self.assertEqual(self.folder_shapes.value(shape, SH["class"]), target)
                self.assertIsNone(self.folder_shapes.value(shape, SH.minCount))
                actual_max = self.folder_shapes.value(shape, SH.maxCount)
                self.assertEqual(
                    actual_max, None if maximum is None else Literal(maximum)
                )
                for triple in (
                    (path, RDF.type, OWL.ObjectProperty),
                    (path, RDFS.domain, SHARED.StagingFolder),
                    (path, RDFS.range, target),
                ):
                    self.assertIn(triple, self.ontology)
                self.assertEqual(
                    {
                        label.language
                        for label in self.ontology.objects(path, RDFS.label)
                    },
                    {"en", "de", "fr", "it"},
                )
                self.assertTrue(list(self.ontology.objects(path, RDFS.comment)))

    def test_one_default_and_multiple_references_are_valid(self) -> None:
        """One folder can suggest one unit while containing several media references."""
        graph = self._folder()
        graph.add((EX.unit, RDF.type, SHARED.ArchiveUnit))
        graph.add((EX.folder, SHARED.defaultArchiveUnit, EX.unit))
        for medium in (EX.photo, EX.audio):
            graph.add((medium, RDF.type, SHARED.MediaObject))
            graph.add((EX.folder, SHARED.referencedMediaObject, medium))
        self._assert_conforms(graph)

    def test_two_defaults_are_rejected(self) -> None:
        """Conflicting placement defaults are invalid even when both targets are units."""
        graph = self._folder()
        for unit in (EX.unit, EX.otherUnit):
            graph.add((unit, RDF.type, SHARED.ArchiveUnit))
            graph.add((EX.folder, SHARED.defaultArchiveUnit, unit))
        self._assert_conforms(graph, False)

    def test_wrong_target_types_and_literals_are_rejected(self) -> None:
        """Neither links to the wrong resource kind nor literal links are accepted."""
        for predicate, wrong_class in (
            (SHARED.defaultArchiveUnit, SHARED.MediaObject),
            (SHARED.referencedMediaObject, SHARED.ArchiveUnit),
        ):
            for target in (EX.wrong, Literal("not a resource")):
                with self.subTest(predicate=predicate, target=target):
                    graph = self._folder()
                    graph.add((EX.wrong, RDF.type, wrong_class))
                    graph.add((EX.folder, predicate, target))
                    self._assert_conforms(graph, False)

    def test_folders_can_share_targets(self) -> None:
        """Defaults and media are not globally unique or owned by one folder."""
        graph = self._folder() + self._folder(EX.secondFolder)
        graph.add((EX.unit, RDF.type, SHARED.ArchiveUnit))
        graph.add((EX.photo, RDF.type, SHARED.MediaObject))
        for folder in (EX.folder, EX.secondFolder):
            graph.add((folder, SHARED.defaultArchiveUnit, EX.unit))
            graph.add((folder, SHARED.referencedMediaObject, EX.photo))
        self._assert_conforms(graph)

    def test_project_subclasses_are_valid_targets(self) -> None:
        """Independent project models can specialize both targets, including transitively."""
        for project in (
            Namespace("https://example.org/photos/"),
            Namespace("https://example.org/museum/"),
        ):
            with self.subTest(project=project):
                graph = self._folder()
                graph.add((project.Collection, RDFS.subClassOf, SHARED.ArchiveUnit))
                graph.add((project.Image, RDFS.subClassOf, project.Representation))
                graph.add((project.Representation, RDFS.subClassOf, SHARED.MediaObject))
                graph.add((EX.unit, RDF.type, project.Collection))
                graph.add((EX.photo, RDF.type, project.Image))
                graph.add((EX.folder, SHARED.defaultArchiveUnit, EX.unit))
                graph.add((EX.folder, SHARED.referencedMediaObject, EX.photo))
                self._assert_conforms(graph)

    def test_references_do_not_turn_folders_into_archive_units(self) -> None:
        """RDFS domain inference must preserve the distinction between both hierarchies."""
        graph = self._folder() + self.ontology
        graph.add((EX.folder, SHARED.referencedMediaObject, EX.photo))
        graph.add((EX.folder, SHARED.defaultArchiveUnit, EX.unit))
        DeductiveClosure(RDFS_Semantics).expand(graph)
        self.assertNotIn((EX.folder, RDF.type, SHARED.ArchiveUnit), graph)
        self.assertIn((EX.photo, RDF.type, SHARED.MediaObject), graph)
        self.assertNotIn((EX.unit, SHARED.hasMediaObject, EX.photo), graph)


if __name__ == "__main__":
    unittest.main()
