"""GraphDB-independent tests for archive import resolution and rollback."""

import unittest
from unittest.mock import Mock

from oldaplib.src.archive_import import (
    ArchiveImportError,
    apply_archive_import,
    prepare_archive_import,
    resolve_archive_document,
)
from oldaplib.src.archive_yaml import loads_archive_yaml
from oldaplib.src.helpers.oldaperror import OldapErrorNoPermission, OldapErrorNotFound
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName


YAML = """\
archive:
  version: 1
  language: de
  units:
    - id: root
      level: Fonds
      title: Bestand
      children:
        - id: child
          level: File
          title: Dossier
"""


class _ArchiveUnitClass:
    """Configurable fake ResourceInstance class returned by a factory."""

    name = Xsd_QName("shared:ArchiveUnit", validate=False)
    admin_create = True
    created_order: list[Iri] = []
    stored: dict[Iri, "_ArchiveUnitClass"] = {}
    fail_create: Iri | None = None
    fail_delete: Iri | None = None

    def __init__(self, *, iri: Iri, **values):
        self.iri = iri
        self.values = values

    def check_for_permissions(self, _permission):
        return self.admin_create, "missing ADMIN_CREATE"

    def create(self) -> None:
        if self.iri == self.fail_create:
            raise RuntimeError("simulated create failure")
        self.created_order.append(self.iri)
        self.stored[self.iri] = self

    def delete(self) -> None:
        if self.iri == self.fail_delete:
            raise RuntimeError("simulated rollback failure")
        self.stored.pop(self.iri, None)


class _ExternalParent:
    """Visible external ArchiveUnit with a configurable data permission."""

    name = Xsd_QName("shared:ArchiveUnit", validate=False)

    def __init__(self, allowed: bool = True):
        self.allowed = allowed

    def get_data_permission(self, _permission) -> bool:
        return self.allowed


class ArchiveImportTest(unittest.TestCase):
    """Verify deterministic resolution, preflight, apply, and rollback."""

    def setUp(self) -> None:
        _ArchiveUnitClass.admin_create = True
        _ArchiveUnitClass.created_order = []
        _ArchiveUnitClass.stored = {}
        _ArchiveUnitClass.fail_create = None
        _ArchiveUnitClass.fail_delete = None
        self.document = loads_archive_yaml(YAML)
        self.factory = Mock()
        self.factory.createObjectInstance.return_value = _ArchiveUnitClass
        self.factory.read.side_effect = self._read

    @staticmethod
    def _read(iri: Iri):
        if iri in _ArchiveUnitClass.stored:
            return _ArchiveUnitClass.stored[iri]
        raise OldapErrorNotFound(str(iri))

    def test_resolves_stable_project_iris_and_internal_parents(self) -> None:
        units = resolve_archive_document(self.document, "fasnacht")

        self.assertEqual([str(unit.iri) for unit in units], ["fasnacht:root", "fasnacht:child"])
        self.assertIsNone(units[0].parent_iri)
        self.assertEqual(units[1].parent_iri, Iri("fasnacht:root"))

    def test_preflight_rejects_missing_admin_create(self) -> None:
        _ArchiveUnitClass.admin_create = False

        with self.assertRaisesRegex(OldapErrorNoPermission, "ADMIN_CREATE"):
            prepare_archive_import(self.factory, "fasnacht", self.document)

    def test_preflight_rejects_create_only_collision(self) -> None:
        _ArchiveUnitClass.stored[Iri("fasnacht:root")] = _ArchiveUnitClass(
            iri=Iri("fasnacht:root")
        )

        with self.assertRaisesRegex(ValueError, "never overwritten"):
            prepare_archive_import(self.factory, "fasnacht", self.document)

    def test_preflight_rejects_missing_referenced_resource(self) -> None:
        document = loads_archive_yaml(
            YAML.replace("      title: Bestand", "      title: Bestand\n      creators:\n        - fasnacht:missing-agent")
        )

        with self.assertRaisesRegex(ValueError, "does not exist or is not visible"):
            prepare_archive_import(self.factory, "fasnacht", document)

    def test_external_parent_must_exist_be_archive_unit_and_allow_update(self) -> None:
        document = loads_archive_yaml(
            YAML.replace("      level: Fonds", "      level: Fonds\n      parent: fasnacht:parent")
        )
        parent_iri = Iri("fasnacht:parent")

        with self.assertRaisesRegex(ValueError, "does not exist"):
            prepare_archive_import(self.factory, "fasnacht", document)

        wrong_parent = Mock()
        wrong_parent.__class__.name = Xsd_QName("fasnacht:ArchiveObject", validate=False)
        self.factory.read.side_effect = lambda iri: wrong_parent if iri == parent_iri else self._read(iri)
        with self.assertRaisesRegex(ValueError, "not a shared:ArchiveUnit"):
            prepare_archive_import(self.factory, "fasnacht", document)

        denied_parent = _ExternalParent(allowed=False)
        self.factory.read.side_effect = lambda iri: denied_parent if iri == parent_iri else self._read(iri)
        with self.assertRaisesRegex(OldapErrorNoPermission, "DATA_UPDATE"):
            prepare_archive_import(self.factory, "fasnacht", document)

        allowed_parent = _ExternalParent()
        self.factory.read.side_effect = lambda iri: allowed_parent if iri == parent_iri else self._read(iri)
        plan = prepare_archive_import(self.factory, "fasnacht", document)
        self.assertEqual(plan.external_parent_iris, (parent_iri,))

    def test_apply_rechecks_and_creates_parents_before_children(self) -> None:
        plan = prepare_archive_import(self.factory, "fasnacht", self.document)

        created = apply_archive_import(self.factory, plan)

        self.assertEqual(created, (Iri("fasnacht:root"), Iri("fasnacht:child")))
        self.assertEqual(_ArchiveUnitClass.created_order, list(created))

    def test_apply_rolls_back_and_reports_rollback_failure(self) -> None:
        plan = prepare_archive_import(self.factory, "fasnacht", self.document)
        _ArchiveUnitClass.fail_create = Iri("fasnacht:child")
        _ArchiveUnitClass.fail_delete = Iri("fasnacht:root")

        with self.assertRaisesRegex(ArchiveImportError, "Rollback failed") as raised:
            apply_archive_import(self.factory, plan)

        self.assertEqual(raised.exception.created_iris, (Iri("fasnacht:root"),))
        self.assertEqual(len(raised.exception.rollback_failures), 1)


if __name__ == "__main__":
    unittest.main()
