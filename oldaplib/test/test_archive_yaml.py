"""GraphDB-independent tests for the canonical archive YAML document model."""

import tempfile
import unittest
from pathlib import Path

from oldaplib.src.archive_yaml import (
    ArchiveDocument,
    dump_archive_yaml,
    dumps_archive_yaml,
    load_archive_yaml,
    loads_archive_yaml,
    archive_yaml_hash,
)


COMPLETE_YAML = """\
archive:
  version: 1
  language: de
  units:
    - id: bmg
      level: Fonds
      title:
        de: Archiv BMG
        en: BMG Archive
      parent: fasnacht:archive-group
      identifier: BMG
      description: Unterlagen der BMG.
      date:
        start: "1911"
        end: "2026"
        verbatim: seit 1911
      extent:
        de: 18 Laufmeter
        en: 18 linear metres
      creators:
        - fasnacht:BMG
      provenance: Vom Verein geführt.
      access_conditions: Benutzung nach Voranmeldung.
      about:
        - fasnacht:BMG
      position: 1
      children:
        - id: bmg-protokolle
          level: Series
          title: Protokolle
"""


class ArchiveYamlTest(unittest.TestCase):
    """Verify in-memory/file parsing, semantics, and stable serialization."""

    def test_loads_minimal_document(self) -> None:
        document = loads_archive_yaml(
            """archive:\n  version: 1\n  language: en\n  units:\n    - id: root\n      level: Fonds\n      title: Root\n"""
        )

        self.assertIsInstance(document, ArchiveDocument)
        self.assertEqual(document.units[0].unit_id, "root")
        self.assertEqual(document.units[0].title, "Root")

    def test_loads_complete_multilingual_document(self) -> None:
        document = loads_archive_yaml(COMPLETE_YAML)

        root = document.units[0]
        self.assertEqual(root.title, {"de": "Archiv BMG", "en": "BMG Archive"})
        self.assertEqual(root.extent, {"de": "18 Laufmeter", "en": "18 linear metres"})
        self.assertEqual(root.children[0].unit_id, "bmg-protokolle")
        self.assertEqual(root.date.start, "1911")

    def test_file_interfaces_and_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.yaml"
            target = Path(directory) / "target.yaml"
            source.write_text(COMPLETE_YAML, encoding="utf-8")

            document = load_archive_yaml(source)
            dump_archive_yaml(document, target)

            self.assertEqual(load_archive_yaml(target), document)
            self.assertEqual(loads_archive_yaml(dumps_archive_yaml(document)), document)
            self.assertTrue(target.read_text(encoding="utf-8").startswith("archive:\n"))

    def test_rejects_invalid_version_level_id_and_iri(self) -> None:
        invalid_documents = (
            (COMPLETE_YAML.replace("version: 1", "version: 2"), "version"),
            (COMPLETE_YAML.replace("level: Fonds", "level: Collection", 1), "level"),
            (COMPLETE_YAML.replace("id: bmg-protokolle", "id: invalid/id"), "NCName"),
            (COMPLETE_YAML.replace("fasnacht:archive-group", "not an iri"), "Invalid IRI"),
        )
        for text, message in invalid_documents:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                loads_archive_yaml(text)

    def test_rejects_duplicate_ids_and_nested_external_parent(self) -> None:
        duplicate = COMPLETE_YAML.replace("id: bmg-protokolle", "id: bmg")
        nested_parent = COMPLETE_YAML.replace(
            "          level: Series",
            "          level: Series\n          parent: fasnacht:other",
        )

        with self.assertRaisesRegex(ValueError, "Duplicate"):
            loads_archive_yaml(duplicate)
        with self.assertRaisesRegex(ValueError, "must not define"):
            loads_archive_yaml(nested_parent)

    def test_rejects_yaml_aliases_before_expansion(self) -> None:
        text = "archive: &archive\n  version: 1\n  language: de\n  units: *archive\n"

        with self.assertRaisesRegex(ValueError, "aliases are not allowed"):
            loads_archive_yaml(text)

    def test_document_hash_binds_exact_text(self) -> None:
        self.assertEqual(archive_yaml_hash(COMPLETE_YAML), archive_yaml_hash(COMPLETE_YAML))
        self.assertNotEqual(archive_yaml_hash(COMPLETE_YAML), archive_yaml_hash(COMPLETE_YAML + "\n"))


if __name__ == "__main__":
    unittest.main()
