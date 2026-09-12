"""Publication policy, authority and generic-write bypass regression tests."""

import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from oldaplib.src.archive_publication import (
    validate_definition,
    guard_publication,
    ArchivePublication,
)
from oldaplib.src.archive_policy import ArchivePolicy, ArchiveConflict
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.datapermissions import DataPermission as DP
from oldaplib.src.helpers.oldaperror import (
    OldapErrorConfiguration,
    OldapErrorNoPermission,
)
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName as Q

BASE = "https://museum.example/model/"
DEFINITION = dict(
    publisherRoleIris=[BASE + "Publisher"],
    rootClassIris=[BASE + "Object"],
    mediaClassIris=[BASE + "Media"],
    statusPropertyIri=BASE + "status",
    publishedStatusIri=BASE + "Public",
    mediaToRootPropertyIri=BASE + "depicts",
    publicRoleIri="http://oldap.org/base#Unknown",
    maxResources=100,
)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.con = SimpleNamespace(
            context_name="publication-tests", userIri=Iri("urn:test:creator")
        )
        Context(name=self.con.context_name)["museum"] = NamespaceIRI(BASE)
        self.project = SimpleNamespace(
            projectShortName="museum", projectIri=Iri("urn:project:museum")
        )
        self.policy = ArchivePolicy(
            self.con, self.project, True, publication=DEFINITION
        )

        class Media:
            name = Q("museum:Media")
            superclass = {}
            _con = self.con

            def __init__(self, status):
                self.status = status
                self.attachedToRoleAnnotation = {Q("museum:Publisher"): DP.DATA_UPDATE}

            def get(self, key):
                return (
                    {self.status}
                    if str(key) == "museum:status" and self.status
                    else None
                )

        self.Media = Media

    def test_generic_project_definition(self):
        validate_definition(DEFINITION)
        for key, value in [
            ("maxResources", True),
            ("maxResources", 501),
            ("publisherRoleIris", []),
            ("statusPropertyIri", "not an iri"),
        ]:
            with (
                self.subTest(key=key, value=value),
                self.assertRaises(OldapErrorConfiguration),
            ):
                validate_definition({**DEFINITION, key: value})
        with self.assertRaises(OldapErrorConfiguration):
            validate_definition({**DEFINITION, "extra": True})

    def test_creator_cannot_publish_via_generic_update(self):
        old = self.Media(Iri("museum:Draft"))
        new = self.Media(Iri("museum:Public"))
        with self.assertRaises(ArchiveConflict):
            guard_publication(new, "update", (), {}, self.policy, old)

    def test_generic_create_cannot_start_published(self):
        with self.assertRaises(ArchiveConflict):
            guard_publication(
                self.Media(Iri("museum:Public")), "create", (), {}, self.policy, None
            )

    def test_generic_acl_change_cannot_bypass_publication(self):
        old = self.Media(Iri("museum:Draft"))
        new = self.Media(Iri("museum:Draft"))
        new.attachedToRoleAnnotation[Q("oldap:Unknown")] = DP.DATA_VIEW
        with self.assertRaises(ArchiveConflict):
            guard_publication(new, "update", (), {}, self.policy, old)

    def test_metadata_only_update_of_published_resource_still_allowed(self):
        old = self.Media(Iri("museum:Public"))
        new = copy.copy(old)
        guard_publication(new, "update", (), {}, self.policy, old)

    def test_role_membership_is_required_even_for_creator_or_admin(self):
        service = object.__new__(ArchivePublication)
        service._con = self.con
        service.project = self.project
        with patch(
            "oldaplib.src.archive_publication.resource_query",
            return_value={"boolean": False},
        ) as query:
            with self.assertRaises(OldapErrorNoPermission):
                service._authorize(self.policy, DEFINITION)
            self.assertIn("oldap:isActive true", query.call_args.args[1])
            self.assertIn(BASE + "Publisher", query.call_args.args[1])

    def test_transform_rejects_explicit_or_inherited_public_state(self):
        for status, properties, grants in (
            ("Draft", {"museum:status": ["museum:Public"]}, {}),
            ("Public", {}, {}),
            ("Draft", {}, {"oldap:Unknown": "DATA_VIEW"}),
        ):
            with self.subTest(status=status, properties=properties, grants=grants):
                instance = self.Media(Iri("museum:" + status))
                instance.factory = SimpleNamespace(
                    createObjectInstance=lambda name: self.Media
                )
                with self.assertRaises(ArchiveConflict):
                    guard_publication(
                        instance,
                        "transform_class",
                        ("museum:Media",),
                        {"properties": properties, "attached_to_role": grants},
                        self.policy,
                        instance,
                    )

    def test_transform_to_private_media_remains_allowed(self):
        instance = self.Media(Iri("museum:Draft"))
        instance.factory = SimpleNamespace(createObjectInstance=lambda name: self.Media)
        guard_publication(
            instance,
            "transform_class",
            ("museum:Media",),
            {"properties": {"museum:status": ["museum:Draft"]}},
            self.policy,
            instance,
        )


class PublicationServiceTests(unittest.TestCase):
    """Exercise dependency review and transaction/idempotency decisions separately."""

    def setUp(self):
        from unittest.mock import Mock

        self.con = SimpleNamespace(
            context_name="publication-service-tests",
            userIri=Iri("urn:test:publisher"),
            transaction_update=Mock(),
        )
        Context(name=self.con.context_name)["museum"] = NamespaceIRI(BASE)
        self.project = SimpleNamespace(
            projectShortName="museum", projectIri=Iri("urn:project:museum")
        )
        self.policy = ArchivePolicy(
            self.con, self.project, True, publication=DEFINITION
        )

        class Record:
            properties = {Q("museum:status"): True}

            def __init__(self, kind, status="Draft", parents=(), permission=None):
                self.kind = kind
                self.data = {
                    "museum:status": {Iri("museum:" + status)},
                    "museum:depicts": set(map(Iri, parents)),
                }
                self.attachedToRoleAnnotation = {Q("museum:Publisher"): DP.DATA_UPDATE}
                if permission:
                    self.attachedToRoleAnnotation[Q("oldap:Unknown")] = permission

            @classmethod
            def resolved_properties(cls):
                return cls.properties

            def get(self, key):
                return self.data.get(str(key))

            def __setitem__(self, key, value):
                self.data[str(key)] = {value}

        self.Record = Record
        self.root = Record("root")
        self.medium = Record("media", parents=("urn:test:root",))
        self.records = {"urn:test:root": self.root, "urn:test:media": self.medium}
        self.service = object.__new__(ArchivePublication)
        self.service._con = self.con
        self.service.project = self.project
        self.service._configured = Mock(return_value=(self.policy, DEFINITION))
        self.service._authorize = Mock()
        self.service._read = Mock(side_effect=lambda iri, policy: self.records[iri])
        self.service._receipt = Mock(return_value=None)
        self.kind_patch = patch(
            "oldaplib.src.archive_publication._kind",
            side_effect=lambda obj, definition: obj.kind,
        )
        self.kind_patch.start()
        self.addCleanup(self.kind_patch.stop)
        self.rights_patch = patch.object(ArchivePolicy, "require_data")
        self.rights = self.rights_patch.start()
        self.addCleanup(self.rights_patch.stop)

        def query(con, statement):
            if "SELECT DISTINCT ?media" in statement:
                return {
                    "results": {"bindings": [{"media": {"value": "urn:test:media"}}]}
                }
            return {"results": {"bindings": []}}

        self.query_patch = patch(
            "oldaplib.src.archive_publication.resource_query", side_effect=query
        )
        self.query_patch.start()
        self.addCleanup(self.query_patch.stop)

    def review(self, permission="DATA_VIEW"):
        return self.service._review(
            "urn:test:root", permission, self.policy, DEFINITION
        )

    def test_review_contains_root_and_media_and_checks_update_for_both(self):
        resources, grants, revision = self.review()
        self.assertEqual(set(resources), set(self.records))
        self.assertEqual(grants["urn:test:media"], DP.DATA_VIEW)
        self.assertEqual(len(revision), 64)
        self.assertEqual(self.rights.call_count, 2)
        self.con.transaction_update.assert_not_called()

    def test_unpublished_other_root_blocks_entire_review(self):
        self.medium.data["museum:depicts"].add(Iri("urn:test:other"))
        self.records["urn:test:other"] = self.Record("root")
        with self.assertRaises(ArchiveConflict):
            self.review()
        self.con.transaction_update.assert_not_called()

    def test_restrictive_other_root_controls_media_grant(self):
        self.medium.data["museum:depicts"].add(Iri("urn:test:other"))
        self.records["urn:test:other"] = self.Record(
            "root", "Public", permission=DP.DATA_RESTRICTED
        )
        _, grants, _ = self.review()
        self.assertEqual(grants["urn:test:root"], DP.DATA_VIEW)
        self.assertEqual(grants["urn:test:media"], DP.DATA_RESTRICTED)

    def test_hidden_media_blocks_before_any_write(self):
        self.service._read.side_effect = OldapErrorNoPermission("hidden")
        with self.assertRaises(OldapErrorNoPermission):
            self.review()
        self.con.transaction_update.assert_not_called()

    def test_update_right_is_required_despite_publisher_role(self):
        self.rights.side_effect = OldapErrorNoPermission("update required")
        with self.assertRaises(OldapErrorNoPermission):
            self.review()

    def test_already_public_access_is_not_widened(self):
        self.records["urn:test:media"] = self.Record(
            "media", "Public", permission=DP.DATA_RESTRICTED
        )
        _, grants, _ = self.review()
        self.assertEqual(grants["urn:test:media"], DP.DATA_RESTRICTED)

    def test_resource_limit_and_write_grants_are_rejected(self):
        definition = {**DEFINITION, "maxResources": 1}
        with self.assertRaises(ArchiveConflict):
            self.service._review("urn:test:root", "DATA_VIEW", self.policy, definition)
        from oldaplib.src.helpers.oldaperror import OldapErrorValue

        with self.assertRaises(OldapErrorValue):
            self.review("DATA_PERMISSIONS")

    def test_stale_apply_never_writes(self):
        from contextlib import nullcontext
        from unittest.mock import Mock

        self.service._review = Mock(return_value=(self.records, {}, "a" * 64))
        with patch(
            "oldaplib.src.archive_publication.resource_transaction",
            return_value=nullcontext(),
        ):
            with self.assertRaises(ArchiveConflict):
                self.service.apply(
                    {
                        "resourceIri": "urn:test:root",
                        "permission": "DATA_VIEW",
                        "revision": "b" * 64,
                    },
                    "00000000-0000-4000-8000-000000000001",
                )
        self.con.transaction_update.assert_not_called()

    def test_exact_retry_uses_receipt_not_a_second_write(self):
        from contextlib import nullcontext
        from oldaplib.src.archive_repository import _digest

        request = {
            "resourceIri": "urn:test:root",
            "permission": "DATA_VIEW",
            "revision": "a" * 64,
        }
        result = {"state": "committed", "resourceIris": ["urn:test:root"]}
        self.service._receipt.return_value = {
            "requestDigest": _digest(request),
            "result": result,
        }
        with patch(
            "oldaplib.src.archive_publication.resource_transaction",
            return_value=nullcontext(),
        ):
            self.assertEqual(
                self.service.apply(request, "00000000-0000-4000-8000-000000000001"),
                result,
            )
            with self.assertRaises(ArchiveConflict):
                self.service.apply(
                    {**request, "permission": "DATA_RESTRICTED"},
                    "00000000-0000-4000-8000-000000000001",
                )
        self.con.transaction_update.assert_not_called()
