"""Cursor security and bounded-input tests independent of database fixtures."""

import hashlib
import json
import unittest
from unittest.mock import patch
from oldaplib.src.archive_inventory import ArchiveInventory
from oldaplib.src.helpers.oldaperror import OldapErrorValue


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


if __name__ == "__main__":
    unittest.main()
