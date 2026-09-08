"""Closed, server-owned project policy for archive domain operations.

The policy adds capabilities to normal OLDAP instance permissions. It never
changes grants or treats a configured role as a replacement for data rights.
No project-specific classes or namespaces are embedded in this module.
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import (
    OldapError,
    OldapErrorConfiguration,
    OldapErrorNoPermission,
    OldapErrorValue,
)
from oldaplib.src.project import Project
from oldaplib.src.resource_transaction import resource_query
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


class ArchiveConflict(OldapError):
    """A domain invariant or reviewed revision prevents the requested change."""

    status = 409
    code = "INVALID_HIERARCHY"


class PreparationNoteArchived(ArchiveConflict):
    """Preparation notes, including delayed clears, are immutable after transfer."""

    def __init__(self):
        super().__init__(
            "Dieses Medium ist bereits archiviert. Die Vorbereitungsnotiz kann nicht mehr geändert werden."
        )


def _closed_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise OldapErrorConfiguration("Archive policy contains duplicate keys.")
        result[key] = value
    return result


def canonical_iri(context: Context, value) -> str:
    """Resolve a QName through trusted context or validate an absolute IRI."""
    if str(value).startswith(("http://", "https://", "urn:")):
        return str(Xsd_anyURI(str(value), validate=True))
    supplied_iri = isinstance(value, Iri)
    iri = value if supplied_iri else Iri(str(value), validate=True)
    if not iri.is_qname:
        return str(iri)
    # String input was already validated by Iri. Do not rebuild its QName's XML
    # validators a second time. Supplied Iri objects may have validate=False, so
    # retain the explicit validation for those callers.
    qname = Xsd_QName(str(iri), validate=True) if supplied_iri else iri.as_qname
    return str(context.qname2iri(qname))


def _absolute(value):
    if (
        not isinstance(value, str)
        or value != value.strip()
        or urlsplit(value).scheme not in {"http", "https", "urn"}
    ):
        raise OldapErrorConfiguration(
            "Archive policy requires canonical absolute IRIs."
        )
    if not Iri(Xsd_anyURI(value, validate=True)).is_fulliri:
        raise OldapErrorConfiguration("Archive policy requires absolute IRIs.")
    return value


def _read_entries(path: str) -> dict:
    try:
        raw = Path(path).read_bytes()
        if len(raw) > 1_000_000:
            raise OldapErrorConfiguration("Archive policy is too large.")
        data = json.loads(raw, object_pairs_hook=_closed_object)
        if (
            not isinstance(data, dict)
            or set(data) != {"projects"}
            or not isinstance(data["projects"], dict)
        ):
            raise OldapErrorConfiguration(
                "Archive policy requires only a projects object."
            )
        expected = {
            "enabled",
            "structureEditorRoleIris",
            "archiveEditorRoleIris",
            "cataloguedMediaClassIris",
            "preparationNotePropertyIri",
        }
        for project, entry in data["projects"].items():
            Xsd_NCName(project, validate=True)
            if (
                not isinstance(entry, dict)
                or set(entry) != expected
                or type(entry["enabled"]) is not bool
            ):
                raise OldapErrorConfiguration(
                    "Archive project policy has invalid fields."
                )
            _absolute(entry["preparationNotePropertyIri"])
            for key in (
                "structureEditorRoleIris",
                "archiveEditorRoleIris",
                "cataloguedMediaClassIris",
            ):
                values = entry[key]
                if not isinstance(values, list) or not values or len(values) > 100:
                    raise OldapErrorConfiguration(
                        f"Archive policy {key} requires 1..100 IRIs."
                    )
                checked = [_absolute(value) for value in values]
                if len(set(checked)) != len(checked):
                    raise OldapErrorConfiguration(
                        "Archive policy contains duplicate IRIs."
                    )
        return data["projects"]
    except OldapErrorConfiguration:
        raise
    except (OSError, ValueError, TypeError, OldapError) as error:
        raise OldapErrorConfiguration("Archive policy cannot be validated.") from error


@dataclass(frozen=True)
class ArchivePolicy:
    """Resolved policy bound to one project and its authenticated connection."""

    connection: object
    project: Project
    enabled: bool
    structure_roles: tuple[str, ...] = ()
    editorial_roles: tuple[str, ...] = ()
    media_classes: tuple[str, ...] = ()
    note_property: str | None = None

    @classmethod
    def load(cls, connection, project):
        """Read and validate policy; absent projects retain legacy behavior."""
        path = os.getenv("OLDAP_ARCHIVE_POLICY_FILE")
        project = (
            project
            if isinstance(project, Project)
            else Project.read(connection, project)
        )
        if not path:
            return cls(connection, project, False)
        entry = _read_entries(path).get(str(project.projectShortName))
        if entry is None:
            return cls(connection, project, False)
        policy = cls(
            connection,
            project,
            entry["enabled"],
            tuple(entry["structureEditorRoleIris"]),
            tuple(entry["archiveEditorRoleIris"]),
            tuple(entry["cataloguedMediaClassIris"]),
            entry["preparationNotePropertyIri"],
        )
        policy._validate_resources()
        return policy

    @property
    def context(self):
        return Context(name=self.connection.context_name)

    def _validate_resources(self):
        from oldaplib.src.objectfactory import (
            ResourceInstanceFactory,
            resource_class_is_or_extends,
        )

        try:
            factory = ResourceInstanceFactory(self.connection, self.project)
            for iri in (*self.structure_roles, *self.editorial_roles):
                query = (
                    self.context.sparql_context
                    + f"""ASK {{ GRAPH oldap:admin {{
                    <{iri}> a oldap:Role ; oldap:definedByProject {self.project.projectIri.toRdf} . }} }}"""
                )
                if not resource_query(self.connection, query)["boolean"]:
                    raise OldapErrorConfiguration(
                        "An archive policy role does not belong to the project."
                    )
            for iri in self.media_classes:
                qname = self.context.iri2qname(iri)
                if qname is None:
                    raise OldapErrorConfiguration(
                        "Unknown archive policy class namespace."
                    )
                model = factory.createObjectInstance(qname)
                if not resource_class_is_or_extends(
                    model, "shared:MediaObject"
                ) or resource_class_is_or_extends(model, "shared:StagingMediaObject"):
                    raise OldapErrorConfiguration(
                        "Catalogued classes must be non-staging MediaObject classes."
                    )
            # The preparation field may intentionally be absent from the target
            # class. Its attempted write/clear must still receive the lifecycle
            # rejection before model conversion, without an ontology addition.
            note_query = (
                self.context.sparql_context
                + f"ASK {{ GRAPH ?g {{ ?shape sh:path <{self.note_property}> }} }}"
            )
            if not resource_query(self.connection, note_query)["boolean"]:
                raise OldapErrorConfiguration(
                    "Preparation-note property is not defined by a loaded shape."
                )
        except OldapErrorConfiguration:
            raise
        except OldapError as error:
            raise OldapErrorConfiguration(
                "Archive policy references cannot be resolved."
            ) from error

    def is_admin(self) -> bool:
        actor = self.connection.userdata
        system = actor.inProject.get(Iri("oldap:SystemProject")) or ()
        project = actor.inProject.get(self.project.projectIri) or ()
        return (
            AdminPermission.ADMIN_OLDAP in system
            or AdminPermission.ADMIN_RESOURCES in project
        )

    def has_role(self, roles: tuple[str, ...]) -> bool:
        if self.is_admin():
            return True
        if not roles:
            return False
        values = " ".join(f"<{iri}>" for iri in roles)
        query = (
            self.context.sparql_context
            + f"""ASK {{ GRAPH oldap:admin {{
            VALUES ?role {{ {values} }} {self.connection.userIri.toRdf} oldap:hasRole ?role . }} }}"""
        )
        return resource_query(self.connection, query)["boolean"]

    def require_structure(self):
        """Require the dedicated capability; object rights are checked separately."""
        if self.enabled and not self.has_role(self.structure_roles):
            raise OldapErrorNoPermission("Archive structure editing is not permitted.")

    def require_editor(self):
        if self.enabled and not self.has_role(self.editorial_roles):
            raise OldapErrorNoPermission("Archive media editing is not permitted.")

    def is_catalogued(self, instance_or_class) -> bool:
        from oldaplib.src.objectfactory import resource_class_is_or_extends

        model = (
            instance_or_class
            if isinstance(instance_or_class, type)
            else type(instance_or_class)
        )
        return any(
            resource_class_is_or_extends(model, self.context.iri2qname(iri))
            for iri in self.media_classes
        )

    def check_note_payload(self, instance, fields):
        """Reject attempted writes before value conversion, including absent clears."""
        if (
            self.enabled
            and self.is_catalogued(instance)
            and any(
                canonical_iri(self.context, field) == self.note_property
                for field in fields
            )
        ):
            raise PreparationNoteArchived()

    def require_data(self, instance, permission: DataPermission):
        if not self.is_admin() and not instance.get_data_permission(permission):
            raise OldapErrorNoPermission(
                "The required resource permission is unavailable."
            )

    def validate_archive_grants(self, grants):
        """Prevent transfer/create from retaining private-contributor write grants."""
        for role, permission in grants.items():
            if (
                permission is not None
                and permission >= DataPermission.DATA_EXTEND
                and canonical_iri(self.context, role) not in self.editorial_roles
            ):
                raise OldapErrorNoPermission(
                    "Archive media write grants must use configured editorial roles."
                )
