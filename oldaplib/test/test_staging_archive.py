"""Tests for project-neutral Staging-folder archive proposals."""

import unittest

from oldaplib.src.archive_yaml import dumps_archive_yaml, loads_archive_yaml
from oldaplib.src.staging_archive import (
    StagingFolderSnapshot,
    staging_folders_to_archive_proposal,
)


class StagingArchiveProposalTest(unittest.TestCase):
    """Verify technical-folder collapse, levels, IDs, ordering, and warnings."""

    def test_collapses_system_folders_without_converting_media(self) -> None:
        proposal = staging_folders_to_archive_proposal(
            [
                StagingFolderSnapshot("top", "top", None),
                StagingFolderSnapshot("mobile", "Mobile", "top", visible_media_count=2),
                StagingFolderSnapshot("trash", "Trash", "top"),
                StagingFolderSnapshot("events", "Anlässe 2026", "top", position=2),
                StagingFolderSnapshot("sub", "Basler Fasnacht", "events", visible_media_count=3),
                StagingFolderSnapshot("ignored", "Gelöscht", "trash", visible_media_count=1),
            ]
        )

        root = proposal.document.units[0]
        self.assertEqual(root.title, "Anlässe 2026")
        self.assertEqual(root.level, "Series")
        self.assertEqual(root.children[0].level, "File")
        self.assertNotIn("Gelöscht", dumps_archive_yaml(proposal.document))
        self.assertIn("TECHNICAL_FOLDER_MEDIA", {warning.code for warning in proposal.warnings})
        self.assertEqual(loads_archive_yaml(dumps_archive_yaml(proposal.document)), proposal.document)

    def test_duplicate_names_get_stable_distinct_ncname_ids_and_warnings(self) -> None:
        folders = [
            StagingFolderSnapshot("top", "top", None),
            StagingFolderSnapshot("one", "Fotos", "top"),
            StagingFolderSnapshot("two", "Fotos", "top"),
        ]

        first = staging_folders_to_archive_proposal(folders)
        second = staging_folders_to_archive_proposal(folders)

        ids = [unit.unit_id for unit in first.document.units]
        self.assertEqual(first, second)
        self.assertEqual(len(set(ids)), 2)
        self.assertTrue(all(unit_id.startswith("fotos-") for unit_id in ids))
        self.assertIn("DUPLICATE_NAME", {warning.code for warning in first.warnings})
        self.assertIn("EMPTY_FOLDER", {warning.code for warning in first.warnings})

    def test_warns_for_orphans_mixed_and_deep_folders(self) -> None:
        folders = [StagingFolderSnapshot("orphan", "Orphan", "hidden", visible_media_count=1)]
        parent = "orphan"
        for depth in range(7):
            iri = f"level-{depth}"
            folders.append(StagingFolderSnapshot(iri, f"Level {depth}", parent))
            parent = iri

        proposal = staging_folders_to_archive_proposal(folders)
        codes = {warning.code for warning in proposal.warnings}

        self.assertIn("ORPHANED_FOLDER", codes)
        self.assertIn("MIXED_FOLDER", codes)
        self.assertIn("DEEP_HIERARCHY", codes)


if __name__ == "__main__":
    unittest.main()
