"""Offline inventory tests for cursors, concurrent edits and read/write isolation."""

import hashlib
import unittest
from unittest.mock import Mock, patch
from oldaplib.src.archive_inventory import ArchiveInventory
from oldaplib.src.archive_policy import ArchiveConflict
from oldaplib.src.helpers.oldaperror import OldapErrorNoPermission, OldapErrorValue
from oldaplib.src.resource_transaction import resource_transaction


class InventoryCursorTest(unittest.TestCase):
    def setUp(self):
        self.inventory = object.__new__(ArchiveInventory)
        self.inventory._key = b"x" * 32
        self.payload = {
            "context": "c" * 64,
            "revision": "d" * 64,
            "last": ["archiveReference", "e" * 64],
        }

    def test_roundtrip(self):
        cursor = self.inventory._encode(self.payload)
        self.assertEqual(self.inventory._decode(cursor), self.payload)
        self.assertLess(len(cursor), 4096)

    def test_tampered_and_malformed_cursors_fail(self):
        cursor = self.inventory._encode(self.payload)
        for invalid in (
            "",
            "x" * 4097,
            None,
            cursor + "x",
            "ä." + "a" * 64,
            cursor.replace(".", "x", 1),
        ):
            with self.subTest(cursor=str(invalid)[:20]), self.assertRaises(
                OldapErrorValue
            ):
                self.inventory._decode(invalid)

    def test_another_signing_key_cannot_replay_cursor(self):
        cursor = self.inventory._encode(self.payload)
        self.inventory._key = b"y" * 32
        with self.assertRaises(OldapErrorValue):
            self.inventory._decode(cursor)

    def test_signed_invalid_payload_is_rejected(self):
        for payload in (
            {},
            {**self.payload, "extra": True},
            {**self.payload, "last": ["unsupported", "e" * 64]},
            {**self.payload, "last": ["archiveReference", "not-a-digest"]},
        ):
            with self.assertRaises(OldapErrorValue):
                self.inventory._decode(self.inventory._encode(payload))

    def test_long_unicode_identity_still_has_bounded_cursor(self):
        iri = "https://example.test/" + "界" * 2020
        payload = {
            **self.payload,
            "last": ["archiveReference", hashlib.sha256(iri.encode()).hexdigest()],
        }
        self.assertLess(len(self.inventory._encode(payload)), 4096)

    def test_invalid_page_input_fails_before_opening_transaction(self):
        for limit in (0, 101, True, "50", 1.5):
            with self.assertRaises(OldapErrorValue):
                self.inventory.page("urn:test", limit=limit)
        for iri in (None, "test:Folder", "https://x.test/>", "x" * 2049):
            with self.assertRaises(OldapErrorValue):
                self.inventory.page(iri)

    def test_missing_server_key_fails(self):
        for key in (b"", b"x" * 31, "x" * 32):
            with self.assertRaises(OldapErrorValue):
                ArchiveInventory(object(), "test", cursor_secret=key)


class InventoryPageReadTest(unittest.TestCase):
    """Run the page logic with an occupied writer gate and controlled read results."""

    folder_iri = "https://example.org/edition/folder"
    medium_iri = "https://example.org/edition/image"

    def setUp(self):
        self.inventory = object.__new__(ArchiveInventory)
        self.inventory._key = b"p" * 32
        self.inventory._con = Mock(userIri="https://example.org/user")
        repo = self.inventory.repository = Mock()
        repo.project.projectShortName = "edition"
        self.folder = Mock(iri=self.folder_iri)
        self.medium = Mock(iri=self.medium_iri)
        self.medium.get.side_effect = lambda prop: {"shared:originalName": {"002.jpg"}}.get(str(prop))
        repo.factory.read.side_effect = lambda iri: {
            self.folder_iri: self.folder, self.medium_iri: self.medium
        }[str(iri)]
        self.policy = repo._policy.return_value
        self.policy.is_admin.return_value = False
        self.medium.get_data_permission.return_value = False
        repo.folder_revision.return_value = "r1"
        self.row = {"kind": {"value": "stagingMedia"}, "media": {"value": self.medium_iri}}
        self.inventory._rows = Mock(return_value=[self.row])
        self.enterContext(patch("oldaplib.src.archive_inventory.is_a", return_value=True))
        tree = self.enterContext(patch("oldaplib.src.archive_inventory.StagingFolderTree")).return_value
        tree.path_to_root.return_value = [self.folder]
        self.enterContext(patch("oldaplib.src.resource_transaction.archive_coordination_enabled", return_value=True))
        self.gate = self.enterContext(patch(
            "oldaplib.src.resource_transaction.mutation_gate",
            side_effect=AssertionError("writer gate unavailable"),
        ))

    def test_regular_user_reads_image_while_writes_remain_blocked(self):
        page = self.inventory.page(self.folder_iri)
        self.assertEqual([(e["title"], e["canEditMetadata"]) for e in page["entries"]], [("002.jpg", False)])
        self.assertIsNone(page["nextCursor"])
        self.gate.assert_not_called()
        self.inventory._con.transaction_start.assert_not_called()
        with self.assertRaisesRegex(AssertionError, "writer gate unavailable"):
            with resource_transaction(self.inventory._con):
                self.fail("Write entered an occupied gate")

    def test_revision_change_rejects_empty_page_and_page_with_lookahead(self):
        for rows in ([], [self.row, self.row]):
            with self.subTest(rows=len(rows)):
                self.inventory.repository.folder_revision.side_effect = ["r1", "r2"]
                self.inventory._rows.return_value = rows
                with self.assertRaises(ArchiveConflict) as error:
                    self.inventory.page(self.folder_iri, limit=1)
                self.assertEqual(error.exception.code, "STALE_FOLDER")

    def test_changed_media_visibility_rejects_result_before_return(self):
        self.inventory._rows.side_effect = [[self.row], []]
        with self.assertRaises(ArchiveConflict) as error:
            self.inventory.page(self.folder_iri)
        self.assertEqual(error.exception.code, "STALE_FOLDER")

    def test_revoked_folder_access_rejects_result_before_return(self):
        self.policy.require_data.side_effect = [None, None, OldapErrorNoPermission("revoked")]
        with self.assertRaises(OldapErrorNoPermission):
            self.inventory.page(self.folder_iri)

    def test_previous_cursor_cannot_continue_after_folder_change(self):
        second = {"kind": {"value": "stagingMedia"}, "media": {"value": "https://example.org/z"}}
        self.inventory._rows.return_value = [self.row, second]
        cursor = self.inventory.page(self.folder_iri, limit=1)["nextCursor"]
        self.inventory.repository.folder_revision.return_value = "r2"
        with self.assertRaises(ArchiveConflict) as error:
            self.inventory.page(self.folder_iri, limit=1, cursor=cursor)
        self.assertEqual(error.exception.code, "STALE_FOLDER")


if __name__ == "__main__":
    unittest.main()
