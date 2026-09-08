"""Offline capability, lifecycle and invariant tests across project subclasses."""

import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from oldaplib.src.archive_domain import guard_resource_operation
from oldaplib.src.archive_policy import (
    ArchiveConflict,
    ArchivePolicy,
    PreparationNoteArchived,
    _read_entries,
)
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import (
    OldapErrorConfiguration,
    OldapErrorInUse,
    OldapErrorNoPermission,
)
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName

BASE = "https://example.test/archive/"
STRUCTURE = BASE + "StructureEditor"
EDITOR = BASE + "Editor"
PROJECT = SimpleNamespace(
    projectIri=Iri("urn:as02:test:project"), projectShortName="test"
)


class PolicyConnection:
    context_name = "AS02-policy-tests"
    userIri = Iri("urn:as02:test:actor")

    def __init__(self):
        Context(name=self.context_name)["test"] = NamespaceIRI(BASE)
        self.userdata = SimpleNamespace(
            inProject={PROJECT.projectIri: {AdminPermission.ADMIN_CREATE}}
        )
        self.roles = {STRUCTURE}
        self.in_use = False
        self.siblings = []
        self.queries = []

    def query(self, query):
        self.queries.append(query)
        if "SELECT DISTINCT ?name" in query:
            return {
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": name}}
                        for name in self.siblings
                    ]
                }
            }
        if "oldap:hasRole" in query:
            return {"boolean": any(f"<{role}>" in query for role in self.roles)}
        if "shared:ArchiveLevel" in query:
            return {"boolean": True}
        return {"boolean": self.in_use}


class Resource:
    name = Xsd_QName("test:Other")
    superclass = {}

    def __init__(self, iri, data=None, *, permission=DataPermission.DATA_UPDATE):
        self.iri = Iri(iri)
        self.data = {Xsd_QName(key): set(value) for key, value in (data or {}).items()}
        self.data[Xsd_QName("oldap:lastModificationDate")] = {"2026-09-07T12:00:00Z"}
        self.changeset = {}
        self.permission = permission
        self.project = PROJECT
        self.attachedToRoleAnnotation = {
            Xsd_QName("test:Editor"): DataPermission.DATA_UPDATE
        }

    def get(self, key):
        return self.data.get(key)

    def get_data_permission(self, permission):
        return self.permission >= permission


class Unit(Resource):
    name = Xsd_QName("test:SpecialUnit")
    superclass = {
        Xsd_QName("test:Unit"): SimpleNamespace(
            superclass={Xsd_QName("shared:ArchiveUnit"): SimpleNamespace(superclass={})}
        )
    }


class Folder(Resource):
    name = Xsd_QName("test:Folder")
    superclass = {Xsd_QName("shared:StagingFolder"): SimpleNamespace(superclass={})}


class Area(Resource):
    name = Xsd_QName("test:Area")
    superclass = {Xsd_QName("shared:StagingArea"): SimpleNamespace(superclass={})}


class Media(Resource):
    name = Xsd_QName("test:ArchiveMedia")
    superclass = {Xsd_QName("shared:MediaObject"): SimpleNamespace(superclass={})}


class Draft(Resource):
    name = Xsd_QName("test:Draft")
    superclass = {
        Xsd_QName("shared:StagingMediaObject"): SimpleNamespace(
            superclass={Xsd_QName("shared:MediaObject"): SimpleNamespace(superclass={})}
        )
    }


class Resources:
    def __init__(self):
        self.items = {}

    def put(self, resource):
        resource.factory = self
        self.items[str(resource.iri)] = resource
        return resource

    def read(self, iri):
        return self.items[str(iri)]

    def createObjectInstance(self, name):
        return {str(Media.name): Media, str(Draft.name): Draft, str(Unit.name): Unit}[
            str(name)
        ]


class ArchiveDomainTest(unittest.TestCase):
    def setUp(self):
        self.con = PolicyConnection()
        self.policy = ArchivePolicy(
            self.con,
            PROJECT,
            True,
            (STRUCTURE,),
            (EDITOR,),
            (BASE + "ArchiveMedia",),
            "http://schema.org/comment",
        )
        # Resolve the installed context's schema URI rather than assuming its scheme.
        self.policy = ArchivePolicy(
            self.con,
            PROJECT,
            True,
            (STRUCTURE,),
            (EDITOR,),
            (BASE + "ArchiveMedia",),
            str(self.policy.context.qname2iri(Xsd_QName("schema:comment"))),
        )
        self.factory = Resources()
        self.unit = self.factory.put(
            Unit(
                "urn:as02:test:unit",
                {
                    "schema:name": ["Archive"],
                    "shared:archiveLevel": [Iri("shared:Series")],
                },
            )
        )
        self.medium = self.factory.put(Media("urn:as02:test:media"))

    def changed(self, resource, prop, value):
        result = copy.copy(resource)
        result.data = dict(resource.data)
        result.data[Xsd_QName(prop)] = set(value)
        result.changeset = {Xsd_QName(prop): object()}
        return result

    def guard(self, current, operation="update", **kwargs):
        return guard_resource_operation(current, operation, (), kwargs, self.policy)

    def test_unit_update_right_without_structure_role_cannot_rename(self):
        self.con.roles.clear()
        with self.assertRaises(OldapErrorNoPermission):
            self.guard(self.changed(self.unit, "schema:name", ["Changed"]))

    def test_structure_role_without_data_right_cannot_rename(self):
        self.unit.permission = DataPermission.DATA_VIEW
        with self.assertRaises(OldapErrorNoPermission):
            self.guard(self.changed(self.unit, "schema:name", ["Changed"]))

    def test_transitive_unit_subclass_allows_capability_plus_update(self):
        current = self.changed(self.unit, "schema:name", ["Changed"])
        self.assertIs(self.guard(current), self.unit)

    def test_attachment_is_separate_from_structure_capability(self):
        self.con.roles.clear()
        current = self.changed(self.unit, "shared:hasMediaObject", [self.medium.iri])
        self.assertIs(self.guard(current), self.unit)

    def test_attachment_does_not_authorize_removal(self):
        self.con.roles.clear()
        self.unit.data[Xsd_QName("shared:hasMediaObject")] = {self.medium.iri}
        with self.assertRaises(OldapErrorNoPermission):
            self.guard(self.changed(self.unit, "shared:hasMediaObject", []))

    def test_attachment_requires_readable_catalogued_medium(self):
        self.con.roles.clear()
        self.medium.permission = DataPermission.DATA_RESTRICTED
        with self.assertRaises(OldapErrorNoPermission):
            self.guard(
                self.changed(self.unit, "shared:hasMediaObject", [self.medium.iri])
            )

    def test_hidden_incoming_reference_blocks_empty_delete(self):
        self.unit.permission = DataPermission.DATA_DELETE
        self.con.in_use = True
        with self.assertRaises(OldapErrorInUse):
            self.guard(self.unit, "delete")
        self.assertTrue(
            any(
                "GRAPH ?g" in query and "?subject ?predicate" in query
                for query in self.con.queries
            )
        )

    def test_cycle_rejected_even_for_admin(self):
        self.con.userdata.inProject[PROJECT.projectIri].add(
            AdminPermission.ADMIN_RESOURCES
        )
        child = self.factory.put(
            Unit("urn:as02:test:child", {"shared:parentArchiveUnit": [self.unit.iri]})
        )
        with self.assertRaises(ArchiveConflict):
            self.guard(self.changed(self.unit, "shared:parentArchiveUnit", [child.iri]))

    def test_note_write_and_clear_rejected_for_combined_editor_and_admin(self):
        self.con.roles = {EDITOR, STRUCTURE}
        self.con.userdata.inProject[PROJECT.projectIri].add(
            AdminPermission.ADMIN_RESOURCES
        )
        for field in ("schema:comment", self.policy.note_property):
            with self.subTest(field=field), self.assertRaises(PreparationNoteArchived):
                self.policy.check_note_payload(self.medium, {field: None})
        with self.assertRaises(PreparationNoteArchived):
            self.guard(self.changed(self.medium, "schema:comment", ["late@de"]))

    def test_other_catalogue_metadata_requires_editor_and_data_permission(self):
        current = self.changed(self.medium, "schema:name", ["Edited"])
        with self.assertRaises(OldapErrorNoPermission):
            self.guard(current)
        self.con.roles.add(EDITOR)
        self.assertIs(self.guard(current), self.medium)

    def test_archive_grants_cannot_preserve_contributor_delete(self):
        self.con.roles.add(EDITOR)
        current = self.changed(self.medium, "schema:name", ["Edited"])
        current.attachedToRoleAnnotation = {
            Xsd_QName("test:Contributor"): DataPermission.DATA_DELETE
        }
        with self.assertRaises(OldapErrorNoPermission):
            self.guard(current)

    def test_metadata_write_checks_authoritative_grants(self):
        self.con.roles.add(EDITOR)
        current = self.changed(self.medium, "schema:name", ["Edited"])
        self.medium.attachedToRoleAnnotation = {
            Xsd_QName("test:Contributor"): DataPermission.DATA_DELETE
        }
        with self.assertRaises(OldapErrorNoPermission):
            self.guard(current)

    def test_stale_instance_rejected_before_mutation(self):
        current = self.changed(self.unit, "schema:name", ["Changed"])
        current.data[Xsd_QName("oldap:lastModificationDate")] = {"stale"}
        with self.assertRaises(ArchiveConflict) as caught:
            self.guard(current)
        self.assertEqual(caught.exception.code, "STALE_REVIEW")

    def test_generic_reference_edit_is_rejected(self):
        folder = self.factory.put(Folder("urn:as02:test:folder"))
        with self.assertRaises(ArchiveConflict):
            self.guard(
                self.changed(folder, "shared:referencedMediaObject", [self.medium.iri])
            )

    def test_mapping_requires_target_update_even_with_structure_role(self):
        self.unit.permission = DataPermission.DATA_VIEW
        folder = self.factory.put(Folder("urn:as02:test:folder"))
        with self.assertRaises(OldapErrorNoPermission):
            self.guard(
                self.changed(folder, "shared:defaultArchiveUnit", [self.unit.iri])
            )

    def test_private_folder_cannot_cross_areas(self):
        first = self.factory.put(
            Folder(
                "urn:as02:test:first",
                {
                    "schema:name": ["First"],
                    "shared:inStagingArea": [Iri("urn:as02:test:area1")],
                },
            )
        )
        second = self.factory.put(
            Folder(
                "urn:as02:test:second",
                {
                    "schema:name": ["Second"],
                    "shared:inStagingArea": [Iri("urn:as02:test:area2")],
                },
            )
        )
        with self.assertRaises(ArchiveConflict):
            self.guard(self.changed(first, "shared:inStagingFolder", [second.iri]))

    def test_private_root_creation_requires_area_update(self):
        area = self.factory.put(Area("urn:as02:test:area"))
        top = self.factory.put(
            Folder(
                "urn:as02:test:top",
                {"schema:name": ["top"], "shared:inStagingArea": [area.iri]},
            )
        )
        self.assertIsNone(self.guard(top, "create"))
        area.permission = DataPermission.DATA_VIEW
        with self.assertRaises(OldapErrorNoPermission):
            self.guard(top, "create")

    def test_private_system_folder_identity_is_protected(self):
        top = self.factory.put(
            Folder(
                "urn:as02:test:top",
                {
                    "schema:name": ["top"],
                    "shared:inStagingArea": [Iri("urn:as02:test:area")],
                },
            )
        )
        for operation in ("update", "delete"):
            with self.subTest(operation=operation), self.assertRaises(ArchiveConflict):
                self.guard(self.changed(top, "schema:name", ["Other"]), operation)

    def test_catalogued_media_cannot_transform_back_to_draft(self):
        self.con.roles.add(EDITOR)
        with self.assertRaises(ArchiveConflict):
            self.guard(self.medium, "transform_class", target_class=Draft.name)

    def test_disabled_project_retains_legacy_behavior(self):
        disabled = ArchivePolicy(self.con, PROJECT, False)
        current = self.changed(self.unit, "schema:name", ["Changed"])
        self.con.roles.clear()
        self.assertIsNone(guard_resource_operation(current, "update", (), {}, disabled))


class ArchivePolicyFileTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "policy.json"
        self.entry = {
            "enabled": True,
            "structureEditorRoleIris": [STRUCTURE],
            "archiveEditorRoleIris": [EDITOR],
            "cataloguedMediaClassIris": [BASE + "ArchiveMedia"],
            "preparationNotePropertyIri": "https://schema.org/comment",
        }

    def tearDown(self):
        self.directory.cleanup()

    def read(self, value):
        self.path.write_text(json.dumps(value))
        return _read_entries(str(self.path))

    def test_valid_closed_file_supports_two_projects(self):
        self.assertEqual(
            set(self.read({"projects": {"one": self.entry, "two": self.entry}})),
            {"one", "two"},
        )

    def test_unknown_fields_and_non_boolean_flags_fail_closed(self):
        for entry in (
            {**self.entry, "extra": True},
            {**self.entry, "enabled": 1},
            {**self.entry, "structureEditorRoleIris": ["test:StructureEditor"]},
        ):
            with self.subTest(entry=entry), self.assertRaises(OldapErrorConfiguration):
                self.read({"projects": {"test": entry}})

    def test_duplicate_json_keys_fail_closed(self):
        self.path.write_text('{"projects":{},"projects":{}}')
        with self.assertRaises(OldapErrorConfiguration):
            _read_entries(str(self.path))

    def test_absent_and_malformed_files_fail_closed(self):
        with self.assertRaises(OldapErrorConfiguration):
            _read_entries(str(self.path))
        self.path.write_text("invalid")
        with self.assertRaises(OldapErrorConfiguration):
            _read_entries(str(self.path))


if __name__ == "__main__":
    unittest.main()
