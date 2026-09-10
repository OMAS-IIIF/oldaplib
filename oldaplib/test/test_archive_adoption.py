"""Frozen reviewed-adoption validation and normalization without live fixtures."""

from copy import deepcopy
import unittest

from oldaplib.src.archive_adoption import digest, normal_plan, plan_order, validate
from oldaplib.src.archive_policy import ArchiveConflict
from oldaplib.src.helpers.oldaperror import OldapErrorValue


class AdoptionPlanTest(unittest.TestCase):
    def setUp(self):
        self.plan = {
            "sourceFolderIri": "urn:as04:source",
            "sourceSnapshot": "a" * 64,
            "newUnits": [
                {
                    "key": "group",
                    "name": {"de": "Gruppe"},
                    "archiveLevel": "shared:Series",
                    "parent": None,
                },
                {
                    "key": "leaf",
                    "name": {"de": "Bilder"},
                    "archiveLevel": "shared:File",
                    "parent": {"key": "group"},
                },
            ],
            "mappings": [
                {
                    "folderIri": "urn:as04:folder",
                    "action": "set",
                    "target": {"key": "leaf"},
                }
            ],
        }

    def test_structure_only_mode_is_explicit_and_changes_review_identity(self):
        legacy = digest(normal_plan(self.plan))
        self.plan["applyMappings"] = False
        validate({"plan": self.plan}, "PreflightRequest")
        self.assertNotEqual(legacy, digest(normal_plan(self.plan)))
        self.assertEqual(len(plan_order(self.plan)), 2)

    def test_structure_only_apply_does_not_mutate_folders_and_records_origins(self):
        from contextlib import nullcontext
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch
        from uuid import uuid4
        from oldaplib.src.archive_adoption import ArchiveAdoption

        for apply_mappings in (False, True):
            with self.subTest(applyMappings=apply_mappings):
                plan = normal_plan({**self.plan, "applyMappings": apply_mappings})
                repo = ArchiveAdoption.__new__(ArchiveAdoption)
                repo._con = MagicMock()
                repo._con.userIri = "urn:actor"
                repo.factory = MagicMock()
                repo.project = SimpleNamespace(projectShortName="example")
                repo._policy = MagicMock(return_value=SimpleNamespace(context=None))
                repo._receipt = MagicMock(return_value=None)
                repo._receipt_iri = MagicMock(return_value="urn:receipt")
                folder = MagicMock()
                repo._review = MagicMock(
                    return_value=(
                        {"reviewDigest": "b" * 64},
                        plan,
                        plan_order(plan),
                        {"urn:as04:folder": folder},
                        {"group": {}, "leaf": {}},
                    )
                )
                with (
                    patch(
                        "oldaplib.src.archive_adoption.resource_transaction",
                        return_value=nullcontext(),
                    ),
                    patch(
                        "oldaplib.src.archive_adoption.audit_command",
                        return_value=nullcontext(),
                    ),
                    patch(
                        "oldaplib.src.archive_adoption.canonical_iri",
                        side_effect=lambda context, value: str(value),
                    ),
                ):
                    result = repo.apply(
                        {"plan": plan, "reviewDigest": "b" * 64, "confirm": True},
                        operation_id=str(uuid4()),
                    )
                self.assertEqual(len(result["createdUnits"]), 2)
                self.assertEqual(folder.update.call_count, int(apply_mappings))
                self.assertEqual(folder.__setitem__.call_count, int(apply_mappings))
                self.assertEqual(len(result["mappings"]), int(apply_mappings))
                self.assertIn(
                    "sourceCorrespondence",
                    repo._con.transaction_update.call_args.args[0],
                )
                self.assertIn(
                    "urn:as04:folder", repo._con.transaction_update.call_args.args[0]
                )

    def test_default_hints_require_unique_origin_and_current_target_visibility(self):
        from contextlib import nullcontext
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch
        import json
        from oldaplib.src.archive_adoption import ArchiveAdoption

        link = {"folderIri": "urn:test:folder", "targetIri": "urn:test:target"}
        record = {
            "command": "structure-apply",
            "project": "test",
            "applyMappings": False,
            "sourceCorrespondence": [link],
        }
        for scenario in (
            "visible",
            "deleted_or_hidden",
            "ambiguous",
            "other_project",
            "already_mapped",
            "incomplete",
        ):
            with self.subTest(scenario=scenario):
                repo = ArchiveAdoption.__new__(ArchiveAdoption)
                repo._con = MagicMock()
                repo.project = SimpleNamespace(projectShortName="test")
                repo._policy = MagicMock(return_value=MagicMock())
                repo._visibility = MagicMock(return_value="")
                source = {
                    "sourceFolderIri": "urn:test:folder",
                    "stagingAreaIri": "urn:test:area",
                    "sourceSnapshot": "a" * 64,
                    "folders": [
                        {
                            "iri": "urn:test:folder",
                            "parentIri": None,
                            "name": "Folder",
                            "revision": "a" * 64,
                            "defaultArchiveUnitIri": (
                                "urn:test:old" if scenario == "already_mapped" else None
                            ),
                            "mappingState": (
                                "mapped" if scenario == "already_mapped" else "unmapped"
                            ),
                            "protected": False,
                        }
                    ],
                }
                repo._source = MagicMock(return_value=(source, {}))
                item = deepcopy(record)
                if scenario == "other_project":
                    item["project"] = "private"
                if scenario == "ambiguous":
                    item["sourceCorrespondence"].append(
                        {**link, "targetIri": "urn:test:other"}
                    )
                receipts = [{"record": {"value": json.dumps(item)}}] * (
                    1001 if scenario == "incomplete" else 1
                )
                repo._query = MagicMock(
                    side_effect=[
                        receipts,
                        (
                            []
                            if scenario == "deleted_or_hidden"
                            else [{"target": {"value": "urn:test:target"}}]
                        ),
                    ]
                )
                with patch(
                    "oldaplib.src.archive_adoption.resource_transaction",
                    return_value=nullcontext(),
                ):
                    result = repo.default_proposal(
                        {"sourceFolderIri": "urn:test:folder"}
                    )
                self.assertEqual(
                    len(result["suggestedPlan"]["mappings"]), int(scenario == "visible")
                )
                self.assertEqual(result["suggestedPlan"]["newUnits"], [])
                repo._con.transaction_update.assert_not_called()
                if scenario == "incomplete":
                    self.assertEqual(result["warnings"][0]["code"], "HINT_LIMIT")

    def test_grouping_and_many_folders_per_target(self):
        self.plan["mappings"].append(
            {"folderIri": "urn:as04:other", "action": "set", "target": {"key": "leaf"}}
        )
        validate({"plan": self.plan}, "PreflightRequest")
        self.assertEqual([u["key"] for u in plan_order(self.plan)], ["group", "leaf"])

    def test_normalization_equates_reordered_arrays_and_absent_position(self):
        reordered = deepcopy(self.plan)
        reordered["newUnits"].reverse()
        for unit in reordered["newUnits"]:
            unit["position"] = None
        self.assertEqual(digest(normal_plan(self.plan)), digest(normal_plan(reordered)))
        reordered["newUnits"][0]["name"]["de"] = "Anders"
        self.assertNotEqual(
            digest(normal_plan(self.plan)), digest(normal_plan(reordered))
        )
        self.assertNotIn("position", self.plan["newUnits"][0])

    def test_cycles_and_unknown_parents(self):
        for parent in ("leaf", "missing"):
            self.plan["newUnits"][0]["parent"] = {"key": parent}
            with self.assertRaises(ArchiveConflict) as caught:
                plan_order(self.plan)
            self.assertEqual(caught.exception.code, "INVALID_HIERARCHY")

    def test_unused_unit_and_unknown_mapping_key(self):
        for mappings in (
            [],
            [
                {
                    "folderIri": "urn:as04:folder",
                    "action": "set",
                    "target": {"key": "missing"},
                }
            ],
        ):
            self.plan["mappings"] = mappings
            with self.assertRaises(OldapErrorValue):
                plan_order(self.plan)

    def test_duplicate_keys_and_folder_actions(self):
        for field in ("newUnits", "mappings"):
            plan = deepcopy(self.plan)
            plan[field].append(plan[field][0])
            with self.assertRaises(OldapErrorValue):
                plan_order(plan)

    def test_mapping_only_clear_skip_and_existing_target(self):
        self.plan["newUnits"] = []
        self.plan["mappings"] = [
            {"folderIri": "urn:as04:one", "action": "clear"},
            {"folderIri": "urn:as04:two", "action": "skip"},
            {
                "folderIri": "urn:as04:three",
                "action": "set",
                "target": {"iri": "urn:as04:unit"},
            },
        ]
        validate({"plan": self.plan}, "PreflightRequest")
        self.assertEqual(plan_order(self.plan), [])

    def test_closed_schema_invalid_targets_levels_and_confirmation(self):
        for change in (
            lambda p: p.update(extra=True),
            lambda p: p["newUnits"][0].update(archiveLevel="project:Custom"),
            lambda p: p["newUnits"][0].update(name={"de": ""}),
            lambda p: p["mappings"][0].update(
                target={"key": "leaf", "iri": "urn:as04:unit"}
            ),
            lambda p: p["mappings"][0].update(action="clear"),
        ):
            plan = deepcopy(self.plan)
            change(plan)
            with self.assertRaises(OldapErrorValue):
                validate({"plan": plan}, "PreflightRequest")
        with self.assertRaises(OldapErrorValue):
            validate(
                {"plan": self.plan, "reviewDigest": "b" * 64, "confirm": False},
                "ApplyRequest",
            )

    def test_combined_mutation_limit_and_skip_budget(self):
        self.plan["mappings"] += [
            {"folderIri": f"urn:as04:{i}", "action": "clear"} for i in range(497)
        ]
        self.assertEqual(len(plan_order(self.plan)), 2)  # 2 creates + 498 mappings
        self.plan["mappings"].append({"folderIri": "urn:as04:extra", "action": "clear"})
        with self.assertRaises(ArchiveConflict) as caught:
            plan_order(self.plan)
        self.assertEqual(caught.exception.status, 413)
        self.plan["mappings"][-1]["action"] = "skip"
        self.assertEqual(len(plan_order(self.plan)), 2)

    def test_raw_action_and_byte_limits(self):
        for body in (
            {"sourceFolderIri": "x" * 2_000_001},
            {"plan": {**self.plan, "mappings": [{}] * 501}},
        ):
            with self.assertRaises(ArchiveConflict) as caught:
                validate(body, "PreflightRequest")
            self.assertEqual(caught.exception.status, 413)

    def test_source_roles_only_and_public_write_cap(self):
        from types import SimpleNamespace
        from oldaplib.src.archive_adoption import ArchiveAdoption
        from oldaplib.src.archive_policy import canonical_iri
        from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
        from oldaplib.src.enums.datapermissions import DataPermission as DP
        from oldaplib.src.helpers.context import Context
        from oldaplib.src.xsd.xsd_qname import Xsd_QName

        context = Context(name="AS04-grants-unit")
        context["fixture"] = NamespaceIRI("https://example.test/roles/")
        roles = {
            "fixture:Structure": DP.DATA_PERMISSIONS,
            "fixture:Contributor": DP.DATA_DELETE,
            "fixture:Restricted": DP.DATA_RESTRICTED,
            "oldap:Unknown": DP.DATA_PERMISSIONS,
        }
        policy = SimpleNamespace(
            grant_editor_roles_on_creation=False,
            context=context,
            structure_roles=(
                canonical_iri(context, "fixture:Structure"),
                canonical_iri(context, "fixture:UnrelatedStructure"),
            ),
        )
        rows = [
            {
                "s": {"value": canonical_iri(context, role)},
                "p": {"value": canonical_iri(context, "oldap:hasDataPermission")},
                "o": {"value": canonical_iri(context, permission.toRdf)},
            }
            for role, permission in roles.items()
        ]
        service = object.__new__(ArchiveAdoption)
        grants = service._unit_grants(
            self.plan,
            {u["key"]: u for u in self.plan["newUnits"]},
            {"urn:as04:folder": rows},
            policy,
        )["group"]
        self.assertEqual(grants[Xsd_QName("fixture:Structure")], DP.DATA_DELETE)
        self.assertEqual(grants[Xsd_QName("fixture:Contributor")], DP.DATA_UPDATE)
        self.assertEqual(grants[Xsd_QName("fixture:Restricted")], DP.DATA_RESTRICTED)
        self.assertEqual(grants[Xsd_QName("oldap:Unknown")], DP.DATA_VIEW)
        self.assertNotIn(Xsd_QName("fixture:UnrelatedStructure"), grants)

    def test_project_creation_rule_grants_all_new_units_without_folder_grants(self):
        from types import SimpleNamespace
        from oldaplib.src.archive_adoption import ArchiveAdoption
        from oldaplib.src.helpers.context import Context
        from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
        from oldaplib.src.enums.datapermissions import DataPermission as DP
        from oldaplib.src.xsd.xsd_qname import Xsd_QName as Q

        context = Context(name="AS09-adoption-grants")
        context["fixture"] = NamespaceIRI("https://example.test/roles/")
        policy = SimpleNamespace(
            context=context,
            enabled=True,
            grant_editor_roles_on_creation=True,
            structure_roles=("https://example.test/roles/Structure",),
        )
        states = {"urn:as04:folder": []}
        grants = object.__new__(ArchiveAdoption)._unit_grants(
            self.plan, {u["key"]: u for u in self.plan["newUnits"]}, states, policy
        )
        self.assertTrue(grants)
        for values in grants.values():
            self.assertEqual(values, {Q("fixture:Structure"): DP.DATA_DELETE})
        self.assertEqual(states, {"urn:as04:folder": []})

    def test_grouping_unions_readers_without_sharing_sibling_grants(self):
        from types import SimpleNamespace
        from oldaplib.src.archive_adoption import ArchiveAdoption
        from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
        from oldaplib.src.enums.datapermissions import DataPermission as DP
        from oldaplib.src.helpers.context import Context
        from oldaplib.src.xsd.xsd_qname import Xsd_QName

        context = Context(name="AS04-grants-union")
        context["fixture"] = NamespaceIRI("https://example.test/roles/")
        self.plan["newUnits"].append({**self.plan["newUnits"][1], "key": "other"})
        self.plan["mappings"].append(
            {
                "folderIri": "urn:as04:second",
                "action": "set",
                "target": {"key": "other"},
            }
        )

        def rows(role):
            return [
                {
                    "s": {"value": "https://example.test/roles/" + role},
                    "p": {"value": "http://oldap.org/base#hasDataPermission"},
                    "o": {"value": "http://oldap.org/base#DATA_VIEW"},
                }
            ]

        service = object.__new__(ArchiveAdoption)
        grants = service._unit_grants(
            self.plan,
            {u["key"]: u for u in self.plan["newUnits"]},
            {"urn:as04:folder": rows("First"), "urn:as04:second": rows("Second")},
            SimpleNamespace(
                context=context,
                structure_roles=(),
                grant_editor_roles_on_creation=False,
            ),
        )
        first, second = Xsd_QName("fixture:First"), Xsd_QName("fixture:Second")
        self.assertEqual(grants["group"], {first: DP.DATA_VIEW, second: DP.DATA_VIEW})
        self.assertEqual(grants["leaf"], {first: DP.DATA_VIEW})
        self.assertEqual(grants["other"], {second: DP.DATA_VIEW})

    def test_canonical_iri_keeps_validation_for_prebuilt_unvalidated_values(self):
        from oldaplib.src.archive_policy import canonical_iri
        from oldaplib.src.helpers.context import Context
        from oldaplib.src.xsd.iri import Iri

        context = Context(name="AS04-canonical-input")
        self.assertEqual(
            canonical_iri(context, "oldap:Unknown"),
            canonical_iri(context, Iri("oldap:Unknown", validate=False)),
        )
        malformed = Iri("oldap:Unknown", validate=False)
        # Simulate a malformed already-decoded object at the typed boundary.
        malformed._Iri__value = "oldap:bad name"
        for bad in ("oldap:bad name", malformed):
            with self.assertRaises(OldapErrorValue):
                canonical_iri(context, bad)

    def test_canonical_unicode_and_nonfinite_numbers(self):
        self.assertEqual(digest({"ä": 1, "z": 2}), digest({"z": 2, "ä": 1}))
        with self.assertRaises(OldapErrorValue):
            validate({"value": float("nan")}, "ProposalRequest")
