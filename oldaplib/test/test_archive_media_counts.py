"""Execute the aggregation against RDF fixtures; isolate the existing ACL predicate."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from rdflib import Dataset
from oldaplib.src.archive_adoption import ArchiveAdoption

PREFIXES = """PREFIX shared: <urn:shared:>
PREFIX ex: <urn:example:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX oldap: <urn:oldap:>
"""


class MediaCountsTest(unittest.TestCase):
    def setUp(self):
        self.repo = ArchiveAdoption.__new__(ArchiveAdoption)
        self.repo.project = SimpleNamespace(projectShortName="ex")
        self.policy = SimpleNamespace(media_classes=["urn:example:ArchiveMedia"])
        self.data = Dataset(default_union=True)
        self.data.parse(
            data=PREFIXES + """
        ex:Photo rdfs:subClassOf shared:StagingMediaObject .
        ex:ArchivePhoto rdfs:subClassOf ex:ArchiveMedia .
        ex:data {
          ex:one a ex:Photo, shared:StagingMediaObject, ex:ArchivePhoto ; shared:inStagingFolder ex:root ; shared:inStagingArea ex:area .
          ex:root shared:referencedMediaObject ex:one, ex:archived, ex:hidden, ex:notMedia .
          ex:archived a ex:ArchivePhoto .
          ex:hidden a ex:ArchivePhoto .
          ex:notMedia a ex:Other .
          ex:foreign a ex:Photo ; shared:inStagingFolder ex:root ; shared:inStagingArea ex:otherArea .
          ex:child shared:inStagingFolder ex:root .
          ex:childMedia a ex:Photo ; shared:inStagingFolder ex:child ; shared:inStagingArea ex:area .
        }
        """,
            format="trig",
        )
        # The production method uses the exact existing inventory/adoption visibility predicate.
        self.repo._visibility = Mock(return_value="FILTER(?media != ex:hidden)")

        def query(text, policy):
            return [
                {
                    "folder": {"value": str(row.folder)},
                    "count": {"value": str(row.countValue)},
                }
                for row in self.data.query(
                    PREFIXES + text.replace("AS ?count)", "AS ?countValue)")
                )
            ]

        self.repo._query = Mock(side_effect=query)

    def test_visible_direct_distinct_media_and_references_in_one_query(self):
        result = self.repo._direct_media_counts(
            [
                {"iri": "urn:example:root"},
                {"iri": "urn:example:child"},
                {"iri": "urn:example:empty"},
            ],
            "urn:example:area",
            self.policy,
        )
        self.assertEqual(
            result,
            {"urn:example:root": 2, "urn:example:child": 1, "urn:example:empty": 0},
        )
        self.repo._query.assert_called_once()
        self.repo._visibility.assert_called_once_with("?media")

    def test_many_empty_folders_still_use_one_query(self):
        result = self.repo._direct_media_counts(
            [{"iri": f"urn:empty:{i}"} for i in range(100)],
            "urn:example:area",
            self.policy,
        )
        self.assertEqual(set(result.values()), {0})
        self.repo._query.assert_called_once()

    def test_empty_scope_needs_no_query(self):
        self.assertEqual(
            self.repo._direct_media_counts([], "urn:example:area", self.policy), {}
        )
        self.repo._query.assert_not_called()


class MediaCountContractTest(unittest.TestCase):
    def test_count_is_optional_nonnegative_and_integer(self):
        from jsonschema import Draft202012Validator
        from oldaplib.src.archive_adoption import SCHEMA

        validator = Draft202012Validator({**SCHEMA, "$ref": "#/$defs/FolderRow"})
        row = {
            "iri": "urn:test:folder",
            "parentIri": None,
            "name": "Folder",
            "revision": "a" * 64,
            "defaultArchiveUnitIri": None,
            "mappingState": "unmapped",
            "protected": False,
        }
        self.assertTrue(validator.is_valid(row))
        self.assertTrue(validator.is_valid({**row, "directMediaCount": 0}))
        for value in (-1, 0.5, "3", True):
            self.assertFalse(validator.is_valid({**row, "directMediaCount": value}))
