"""Unit tests for cycle-safe Staging folder moves."""

import unittest
from unittest.mock import patch

from oldaplib.src.helpers.oldaperror import (
    OldapErrorAlreadyExists,
    OldapErrorInconsistency,
    OldapErrorValue,
)
from oldaplib.src.staging_folder_tree import StagingFolderTree
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName


AREA = Iri("urn:uuid:00000000-0000-0000-0000-000000000001")


class FakeFolder:
    """Minimal mutable resource instance used by the tree service."""

    name = Xsd_QName("shared:StagingFolder", validate=False)

    def __init__(self, iri: str, folder_name: str, parent: str | None, area: Iri = AREA):
        self.iri = Iri(iri)
        self.values = {
            "schema:name": {folder_name},
            "shared:inStagingArea": {area},
        }
        if parent:
            self.values["shared:inStagingFolder"] = {Iri(parent)}
        self.updated = False

    def get(self, prop):
        return self.values.get(str(prop))

    def __setitem__(self, prop, value):
        self.values[str(prop)] = {value}

    def update(self):
        self.updated = True


class FakeFactory:
    """Read fake folders by IRI."""

    def __init__(self, folders):
        self.folders = {folder.iri: folder for folder in folders}

    def read(self, iri):
        return self.folders[iri]


def tree_with(*folders: FakeFolder) -> StagingFolderTree:
    """Construct a service without loading a project data model."""
    tree = StagingFolderTree.__new__(StagingFolderTree)
    tree._con = object()
    tree._project = "test"
    tree._factory = FakeFactory(folders)
    return tree


class TestStagingFolderTree(unittest.TestCase):
    """Verify subtree moves and their integrity boundaries."""

    def setUp(self):
        self.top = FakeFolder("urn:uuid:00000000-0000-0000-0000-000000000010", "top", None)
        self.source = FakeFolder(
            "urn:uuid:00000000-0000-0000-0000-000000000011",
            "Imported ZIP",
            str(self.top.iri),
        )
        self.child = FakeFolder(
            "urn:uuid:00000000-0000-0000-0000-000000000012",
            "Child",
            str(self.source.iri),
        )
        self.target = FakeFolder(
            "urn:uuid:00000000-0000-0000-0000-000000000013",
            "Correct destination",
            str(self.top.iri),
        )

    @patch("oldaplib.src.staging_folder_tree.ResourceInstance.search", return_value=[])
    def test_move_changes_only_the_subtree_root_parent(self, search):
        tree = tree_with(self.top, self.source, self.child, self.target)

        moved = tree.move(self.source.iri, self.target.iri)

        self.assertIs(moved, self.source)
        self.assertEqual(
            moved.get(StagingFolderTree.PARENT_PROPERTY),
            {self.target.iri},
        )
        self.assertTrue(moved.updated)
        self.assertEqual(
            self.child.get(StagingFolderTree.PARENT_PROPERTY),
            {self.source.iri},
        )
        search.assert_called_once()

    def test_move_rejects_a_descendant_target(self):
        tree = tree_with(self.top, self.source, self.child, self.target)

        with self.assertRaises(OldapErrorInconsistency):
            tree.move(self.source.iri, self.child.iri)

    def test_move_rejects_system_folders_and_cross_area_targets(self):
        trash = FakeFolder(
            "urn:uuid:00000000-0000-0000-0000-000000000015",
            "Trash",
            str(self.top.iri),
        )
        other_area = FakeFolder(
            "urn:uuid:00000000-0000-0000-0000-000000000014",
            "Other",
            None,
            Iri("urn:uuid:00000000-0000-0000-0000-000000000002"),
        )
        tree = tree_with(self.top, self.source, self.target, trash, other_area)

        with self.assertRaises(OldapErrorValue):
            tree.move(self.top.iri, self.target.iri)
        with self.assertRaises(OldapErrorValue):
            tree.move(self.source.iri, trash.iri)
        with self.assertRaises(OldapErrorValue):
            tree.move(self.source.iri, other_area.iri)

    @patch("oldaplib.src.staging_folder_tree.ResourceInstance.search")
    def test_move_rejects_portable_name_collision(self, search):
        search.return_value = [{
            "iri": Iri("urn:uuid:00000000-0000-0000-0000-000000000099"),
            "schema:name": {"IMPORTED ZIP. "},
        }]
        tree = tree_with(self.top, self.source, self.target)

        with self.assertRaises(OldapErrorAlreadyExists):
            tree.move(self.source.iri, self.target.iri)


if __name__ == "__main__":
    unittest.main()
