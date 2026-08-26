"""Project resolution and create-only application of archive YAML documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from oldaplib.src.archive_yaml import ArchiveDocument, ArchiveText, ArchiveUnit
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import (
    OldapError,
    OldapErrorNoPermission,
    OldapErrorNotFound,
)
from oldaplib.src.objectfactory import (
    ResourceInstance,
    ResourceInstanceFactory,
    resource_class_is_or_extends,
)
from oldaplib.src.xsd.dating import Dating
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


@dataclass(frozen=True)
class ArchiveUnitSpec:
    """One project-resolved archive unit in parent-before-child order."""

    unit_id: str
    iri: Iri
    level: str
    title: LangString
    parent_iri: Iri | None
    parent_is_external: bool = False
    identifier: str | None = None
    description: LangString | None = None
    dating: Dating | None = None
    extent: LangString | None = None
    creators: tuple[Iri, ...] = ()
    provenance: LangString | None = None
    access_conditions: LangString | None = None
    about: tuple[Iri, ...] = ()
    position: int | None = None


@dataclass(frozen=True)
class ArchiveImportPlan:
    """Fully resolved and preflighted create-only archive import plan."""

    project_id: str
    project_shortname: Xsd_NCName
    document: ArchiveDocument
    units: tuple[ArchiveUnitSpec, ...]
    external_parent_iris: tuple[Iri, ...] = field(default_factory=tuple)


class ArchiveImportError(OldapError):
    """Report an apply failure together with exact rollback results."""

    def __init__(
        self,
        message: str,
        *,
        created_iris: tuple[Iri, ...],
        rollback_failures: tuple[str, ...],
    ) -> None:
        super().__init__(message)
        self.created_iris = created_iris
        self.rollback_failures = rollback_failures


def _lang_string(value: ArchiveText, default_language: str) -> LangString:
    """Resolve editable text to the OLDAP LangString representation."""

    values = (
        [f"{value}@{default_language}"]
        if isinstance(value, str)
        else [f"{text}@{language}" for language, text in value.items()]
    )
    return LangString(values)


def _optional_lang_string(value: ArchiveText | None, language: str) -> LangString | None:
    """Resolve optional editable text to a LangString."""

    return None if value is None else _lang_string(value, language)


def _project_iri(project_shortname: Xsd_NCName, unit_id: str) -> Iri:
    """Build the deterministic project QName for one YAML identifier."""

    return Iri(Xsd_QName(project_shortname, Xsd_NCName(unit_id, validate=True)))


def resolve_archive_document(
    document: ArchiveDocument,
    project_shortname: Xsd_NCName | str,
) -> tuple[ArchiveUnitSpec, ...]:
    """Resolve a nested document into a project-specific parent-first sequence."""

    shortname = (
        project_shortname
        if isinstance(project_shortname, Xsd_NCName)
        else Xsd_NCName(project_shortname, validate=True)
    )
    units: list[ArchiveUnitSpec] = []

    def visit(unit: ArchiveUnit, nested_parent: Iri | None, *, top_level: bool) -> None:
        unit_iri = _project_iri(shortname, unit.unit_id)
        external_parent = Iri(unit.parent, validate=True) if top_level and unit.parent else None
        date = unit.date
        units.append(
            ArchiveUnitSpec(
                unit_id=unit.unit_id,
                iri=unit_iri,
                level=unit.level,
                title=_lang_string(unit.title, document.language),
                parent_iri=external_parent or nested_parent,
                parent_is_external=external_parent is not None,
                identifier=unit.identifier,
                description=_optional_lang_string(unit.description, document.language),
                dating=(
                    None
                    if date is None
                    else Dating(
                        dateStart=date.start,
                        dateEnd=date.end,
                        verbatimDate=date.verbatim,
                        inCalendar=date.calendar,
                    )
                ),
                extent=_optional_lang_string(unit.extent, document.language),
                creators=tuple(Iri(value, validate=True) for value in unit.creators),
                provenance=_optional_lang_string(unit.provenance, document.language),
                access_conditions=_optional_lang_string(unit.access_conditions, document.language),
                about=tuple(Iri(value, validate=True) for value in unit.about),
                position=unit.position,
            )
        )
        for child in unit.children:
            visit(child, unit_iri, top_level=False)

    for root in document.units:
        visit(root, None, top_level=True)
    return tuple(units)


def _read_existing(factory: ResourceInstanceFactory, iri: Iri) -> ResourceInstance | None:
    """Read a visible resource, returning ``None`` only for a true not-found result."""

    try:
        return factory.read(iri)
    except OldapErrorNotFound:
        return None


def _instance_is_or_extends(instance: ResourceInstance, expected: Xsd_QName) -> bool:
    """Return whether a dynamic OLDAP instance has the expected base class."""
    return resource_class_is_or_extends(instance.__class__, expected)


def _unit_values(unit: ArchiveUnitSpec) -> dict[str, Any]:
    """Build ResourceInstance constructor values for one resolved unit."""

    values: dict[str, Any] = {
        "schema:name": unit.title,
        "shared:archiveLevel": Iri(f"shared:{unit.level}", validate=False),
    }
    optional_values = {
        "shared:parentArchiveUnit": unit.parent_iri,
        "schema:identifier": unit.identifier,
        "schema:description": unit.description,
        "dcterms:temporal": unit.dating,
        "schema:materialExtent": unit.extent,
        "dcterms:creator": set(unit.creators) if unit.creators else None,
        "dcterms:provenance": unit.provenance,
        "schema:conditionsOfAccess": unit.access_conditions,
        "schema:about": set(unit.about) if unit.about else None,
        "schema:position": unit.position,
    }
    values.update({key: value for key, value in optional_values.items() if value is not None})
    return values


def prepare_archive_import(
    factory: ResourceInstanceFactory,
    project_id: str,
    document: ArchiveDocument,
    *,
    project_shortname: Xsd_NCName | str | None = None,
) -> ArchiveImportPlan:
    """Resolve and preflight a create-only import without writing data.

    The authenticated user must have ``ADMIN_CREATE`` in the target project.
    Every existing attachment point must be visible and grant ``DATA_UPDATE``.
    Permission exceptions raised by OLDAP reads are intentionally preserved.
    """

    shortname = Xsd_NCName(project_shortname or project_id, validate=True)
    units = resolve_archive_document(document, shortname)
    ArchiveUnitClass = factory.createObjectInstance("shared:ArchiveUnit")
    permission_probe = ArchiveUnitClass(iri=units[0].iri, **_unit_values(units[0]))
    allowed, message = permission_probe.check_for_permissions(AdminPermission.ADMIN_CREATE)
    if not allowed:
        raise OldapErrorNoPermission(message)

    for unit in units:
        if _read_existing(factory, unit.iri) is not None:
            raise ValueError(
                f'Archive unit "{unit.unit_id}" already exists as {unit.iri}; '
                "existing resources are never overwritten."
            )

    external_parents = sorted(
        {
            unit.parent_iri
            for unit in units
            if unit.parent_is_external and unit.parent_iri is not None
        },
        key=str,
    )
    for parent_iri in external_parents:
        parent = _read_existing(factory, parent_iri)
        if parent is None:
            raise ValueError(f'External parent archive unit "{parent_iri}" does not exist.')
        if not _instance_is_or_extends(
            parent, Xsd_QName("shared:ArchiveUnit", validate=False)
        ):
            raise ValueError(f'External parent "{parent_iri}" is not a shared:ArchiveUnit.')
        if not parent.get_data_permission(DataPermission.DATA_UPDATE):
            raise OldapErrorNoPermission(
                f'No DATA_UPDATE permission on external archive parent "{parent_iri}".'
            )

    referenced_resources: set[tuple[Iri, Xsd_QName]] = set()
    for unit in units:
        referenced_resources.update(
            (iri, Xsd_QName("dcterms:Agent", validate=False)) for iri in unit.creators
        )
        referenced_resources.update(
            (iri, Xsd_QName("oldap:Thing", validate=False)) for iri in unit.about
        )
    for referenced_iri, expected_class in sorted(
        referenced_resources, key=lambda entry: (str(entry[0]), str(entry[1]))
    ):
        referenced = _read_existing(factory, referenced_iri)
        if referenced is None:
            raise ValueError(f'Referenced resource "{referenced_iri}" does not exist or is not visible.')
        if not _instance_is_or_extends(referenced, expected_class):
            raise ValueError(
                f'Referenced resource "{referenced_iri}" is not a {expected_class}.'
            )

    return ArchiveImportPlan(
        project_id=project_id,
        project_shortname=shortname,
        document=document,
        units=units,
        external_parent_iris=tuple(external_parents),
    )


def apply_archive_import(
    factory: ResourceInstanceFactory,
    plan: ArchiveImportPlan,
) -> tuple[Iri, ...]:
    """Recheck and create a plan, rolling back completed nodes on failure.

    The complete preflight is repeated immediately before the first write so
    stale permissions, parents, and collisions cannot silently pass apply.

    Raises:
        ArchiveImportError: If creation fails. ``created_iris`` and
            ``rollback_failures`` expose partial rollback outcomes.
        OldapErrorNoPermission: If the repeated preflight rejects permissions.
        ValueError: If the repeated preflight finds stale data.
    """

    checked_plan = prepare_archive_import(
        factory,
        plan.project_id,
        plan.document,
        project_shortname=plan.project_shortname,
    )
    ArchiveUnitClass = factory.createObjectInstance("shared:ArchiveUnit")
    created: list[Iri] = []
    try:
        for unit in checked_plan.units:
            instance = ArchiveUnitClass(iri=unit.iri, **_unit_values(unit))
            instance.create()
            created.append(unit.iri)
    except Exception as error:
        rollback_failures: list[str] = []
        for iri in reversed(created):
            try:
                factory.read(iri).delete()
            except Exception as rollback_error:
                rollback_failures.append(f"{iri}: {rollback_error}")
        rollback_note = (
            f" Rollback failed for: {'; '.join(rollback_failures)}"
            if rollback_failures
            else " Created units were rolled back."
        )
        raise ArchiveImportError(
            f"Archive import failed: {error}.{rollback_note}",
            created_iris=tuple(created),
            rollback_failures=tuple(rollback_failures),
        ) from error
    return tuple(created)
