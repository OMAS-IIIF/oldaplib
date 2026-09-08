"""Project-neutral invariants for archive and permanent private-folder resources.

Guards run inside the resource transaction and its persistent writer gate. They
apply equally to generic CRUD and dedicated commands, including model subclasses.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import json
from uuid import uuid4

from oldaplib.src.archive_policy import ArchiveConflict, ArchivePolicy, canonical_iri
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.helpers.oldaperror import (
    OldapErrorInUse,
    OldapErrorNoPermission,
    OldapErrorValue,
)
from oldaplib.src.resource_transaction import resource_query
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_qname import Xsd_QName

REFERENCE = "shared:referencedMediaObject"
DEFAULT = "shared:defaultArchiveUnit"
MEDIA = "shared:hasMediaObject"
PARENT = "shared:parentArchiveUnit"
FOLDER_PARENT = "shared:inStagingFolder"
AREA = "shared:inStagingArea"
STRUCTURAL = (
    "schema:name",
    "schema:position",
    "shared:archiveLevel",
    PARENT,
    DEFAULT,
    REFERENCE,
    MEDIA,
    FOLDER_PARENT,
    AREA,
)
_audit_command_id: ContextVar[str | None] = ContextVar(
    "archive_audit_command_id", default=None
)

_reference_command: ContextVar[bool] = ContextVar(
    "archive_reference_command", default=False
)


def is_a(instance, name):
    """Recognise a Shared class through the complete project model hierarchy."""
    from oldaplib.src.objectfactory import resource_class_is_or_extends

    return resource_class_is_or_extends(type(instance), name)


def values(instance, prop):
    """Normalize OLDAP's scalar metadata and collection-valued properties."""
    result = instance.get(Xsd_QName(prop, validate=False))
    if result is None:
        return ()
    if isinstance(result, (LangString, ObservableSet, set, list, tuple)):
        return result
    return (result,)


def single(instance, prop):
    items = values(instance, prop)
    if len(items) > 1:
        raise ArchiveConflict(f"Multiple values for {prop}.")
    return next(iter(items), None)


def structural_state(instance):
    """Return compact structural values for audit; never include media metadata."""
    result = {
        key: sorted(str(v) for v in values(instance, key))
        for key in STRUCTURAL
        if values(instance, key)
    }
    result["rdf:type"] = [str(instance.name)]
    result["oldap:attachedToRole"] = sorted(
        f"{role}={permission}"
        for role, permission in instance.attachedToRoleAnnotation.items()
    )
    return result


def _same(policy, left, right):
    if left is None or right is None:
        return left is right
    return canonical_iri(policy.context, left) == canonical_iri(policy.context, right)


def _read(instance, iri, expected):
    target = instance.factory.read(iri)
    if not is_a(target, expected):
        raise OldapErrorValue(f"Expected a {expected} resource.")
    return target


def _require_targets(policy, instance, previous, prop, expected):
    for iri in {*values(instance, prop), *(values(previous, prop) if previous else ())}:
        target = _read(instance, iri, expected)
        policy.require_data(target, DataPermission.DATA_UPDATE)


def _check_parent(policy, instance, parent_prop, expected):
    """Validate the complete prospective path while coordinated with all writers."""
    parent = single(instance, parent_prop)
    visited = {canonical_iri(policy.context, instance.iri)}
    for _ in range(5000):
        if parent is None:
            return
        canonical = canonical_iri(policy.context, parent)
        if canonical in visited:
            raise ArchiveConflict("The proposed hierarchy contains a cycle.")
        visited.add(canonical)
        node = _read(instance, parent, expected)
        if parent_prop == FOLDER_PARENT and not _same(
            policy, single(node, AREA), single(instance, AREA)
        ):
            raise ArchiveConflict("Private folders cannot move between StagingAreas.")
        parent = single(node, parent_prop)
    raise ArchiveConflict("The hierarchy exceeds the supported traversal limit.")


def _empty(policy, instance):
    """Check incoming references and outgoing content without visibility filters."""
    iri = Iri(Xsd_anyURI(canonical_iri(policy.context, instance.iri))).toRdf
    query = policy.context.sparql_context + f"""ASK {{ GRAPH ?g {{
        {{ ?subject ?predicate {iri} }} UNION
        {{ {iri} (shared:hasMediaObject|shared:referencedMediaObject) ?content }}
    }} }}"""
    if resource_query(policy.connection, query)["boolean"]:
        raise OldapErrorInUse("The resource is not empty or is still referenced.")


def _folder_integrity(policy, instance, previous, operation):
    from oldaplib.src.staging_folder_tree import StagingFolderTree

    name_key = StagingFolderTree._portable_name_key
    name = name_key(str(single(instance, "schema:name") or ""))
    old_name = (
        name_key(str(single(previous, "schema:name") or "")) if previous else None
    )
    # Shared folder names are xsd:string, unlike multilingual archive labels.
    reserved = {"top", "mobile", "trash"}
    if operation != "create" and old_name in reserved:
        changed = (
            {str(key) for key in instance.changeset} if operation == "update" else set()
        )
        if operation == "delete" or changed.intersection(
            {"schema:name", FOLDER_PARENT, AREA}
        ):
            raise ArchiveConflict("System folder identity and placement are protected.")
    if previous and not _same(policy, single(instance, AREA), single(previous, AREA)):
        raise ArchiveConflict("Private folders cannot move between StagingAreas.")
    parent = single(instance, FOLDER_PARENT)
    if parent is not None:
        parent_node = _read(instance, parent, "shared:StagingFolder")
        parent_name = name_key(str(single(parent_node, "schema:name") or ""))
        if parent_name == "mobile":
            raise ArchiveConflict("Folders cannot be created or moved below Mobile.")
        if name in {"mobile", "trash"} and parent_name != "top":
            raise ArchiveConflict("System inboxes must be direct children of top.")
    if parent is None and name != "top":
        raise ArchiveConflict("A private folder root must be the reserved top folder.")
    if name == "top" and parent is not None:
        raise ArchiveConflict("The top folder must be a root.")
    if previous and name in reserved and name != old_name:
        raise ArchiveConflict(
            "Reserved system folder names cannot be assigned by renaming."
        )
    _check_parent(policy, instance, FOLDER_PARENT, "shared:StagingFolder")
    # Check all siblings, including unreadable ones, rather than visible search.
    area = single(instance, AREA)
    if area is None:
        raise ArchiveConflict("A private folder requires a StagingArea.")
    if operation == "create" and parent is None:
        area_node = _read(instance, area, "shared:StagingArea")
        policy.require_data(area_node, DataPermission.DATA_UPDATE)
    parent_pattern = (
        f"?other shared:inStagingFolder {Iri(Xsd_anyURI(canonical_iri(policy.context, parent))).toRdf} ."
        if parent is not None
        else "FILTER NOT EXISTS { ?other shared:inStagingFolder ?parent }"
    )
    query = policy.context.sparql_context + f"""SELECT DISTINCT ?name WHERE {{
        GRAPH {instance.project.projectShortName}:data {{
            ?other a ?folderClass ; shared:inStagingArea {Iri(Xsd_anyURI(canonical_iri(policy.context, area))).toRdf}; schema:name ?name .
            {parent_pattern}
            FILTER (?other != {instance.iri.toRdf})
        }}
        ?folderClass rdfs:subClassOf* shared:StagingFolder .
    }}"""
    rows = resource_query(policy.connection, query)["results"]["bindings"]
    if any(name_key(row["name"]["value"]) == name for row in rows):
        raise ArchiveConflict("A sibling folder already has this name.")


def guard_resource_operation(instance, operation, args, kwargs, policy):
    """Validate an ordinary ResourceInstance write and return its prior state."""
    if not policy.enabled:
        return None
    previous = None if operation == "create" else instance.factory.read(instance.iri)
    if previous is not None:
        if instance.name != previous.name or single(
            instance, "oldap:lastModificationDate"
        ) != single(previous, "oldap:lastModificationDate"):
            error = ArchiveConflict(
                "The resource changed; read it again before editing."
            )
            error.code = "STALE_REVIEW"
            raise error
    fields = (
        {str(key) for key in instance.changeset} if operation == "update" else set()
    )
    if operation == "transform_class":
        policy.check_note_payload(instance, kwargs.get("properties") or {})
        expected_source = kwargs.get("expected_source_class")
        if expected_source is not None and not _same(
            policy, instance.name, expected_source
        ):
            raise ArchiveConflict(
                "The resource class changed; reload it before transforming."
            )
        target = instance.factory.createObjectInstance(
            args[0] if args else kwargs["target_class"]
        )
        if is_a(instance, "shared:ArchiveUnit") or is_a(
            instance, "shared:StagingFolder"
        ):
            raise ArchiveConflict("Structural resources cannot be transformed.")
        from oldaplib.src.objectfactory import resource_class_is_or_extends

        if resource_class_is_or_extends(
            target, "shared:ArchiveUnit"
        ) or resource_class_is_or_extends(target, "shared:StagingFolder"):
            raise ArchiveConflict("Use structure creation for structural resources.")
        if is_a(instance, "shared:StagingMediaObject") and not policy.is_catalogued(
            target
        ):
            raise ArchiveConflict(
                "Staging media can transform only to a configured catalogue class."
            )
        if is_a(instance, "shared:StagingArea") or resource_class_is_or_extends(
            target, "shared:StagingArea"
        ):
            raise ArchiveConflict("StagingAreas cannot be transformed.")
        link = kwargs.get("link_from_iri")
        if link is not None:
            linked = instance.factory.read(Iri(link))
            link_property = canonical_iri(
                policy.context, kwargs.get("link_from_property")
            )
            if is_a(linked, "shared:ArchiveUnit"):
                if link_property != canonical_iri(
                    policy.context, MEDIA
                ) or not policy.is_catalogued(target):
                    raise ArchiveConflict(
                        "Archive attachment requires configured catalogued media."
                    )
                policy.require_data(linked, DataPermission.DATA_UPDATE)
            if is_a(linked, "shared:StagingFolder") and link_property in {
                canonical_iri(policy.context, REFERENCE),
                canonical_iri(policy.context, DEFAULT),
            }:
                raise ArchiveConflict(
                    "A generic transform cannot create private references or mappings."
                )
        if policy.is_catalogued(instance):
            policy.check_note_payload(instance, kwargs.get("properties") or {})
            policy.require_editor()
            if not policy.is_catalogued(target):
                raise ArchiveConflict(
                    "Catalogued media cannot return to a preparation class."
                )
        if policy.is_catalogued(target):
            grants = kwargs.get("attached_to_role")
            if grants is None:
                grants = previous.attachedToRoleAnnotation
            else:
                grants = {
                    key: (
                        value
                        if isinstance(value, DataPermission)
                        else DataPermission.from_string(value)
                    )
                    for key, value in grants.items()
                }
            policy.validate_archive_grants(grants)
        return previous

    if policy.is_catalogued(instance):
        policy.check_note_payload(instance, fields)
        policy.require_editor()
        policy.validate_archive_grants(instance.attachedToRoleAnnotation)
        if previous is not None and "oldap:attachedToRole" not in fields:
            # Validate persisted grants too: metadata-only writes must not rely
            # on an incomplete or manually altered caller-side ACL snapshot.
            policy.validate_archive_grants(previous.attachedToRoleAnnotation)
    if is_a(instance, "shared:ArchiveUnit"):
        attachment_only = (
            operation == "update"
            and fields == {MEDIA}
            and set(values(previous, MEDIA)).issubset(values(instance, MEDIA))
        )
        if not attachment_only:
            policy.require_structure()
        if operation != "create":
            policy.require_data(
                previous,
                (
                    DataPermission.DATA_DELETE
                    if operation == "delete"
                    else DataPermission.DATA_UPDATE
                ),
            )
        if operation == "delete":
            _empty(policy, instance)
        else:
            level = single(instance, "shared:archiveLevel")
            if (
                level is None
                or not resource_query(
                    policy.connection,
                    policy.context.sparql_context
                    + f"ASK {{ {Iri(Xsd_anyURI(canonical_iri(policy.context, level))).toRdf} a shared:ArchiveLevel }}",
                )["boolean"]
            ):
                raise OldapErrorValue(
                    "An archive unit requires a valid shared:ArchiveLevel."
                )
            _check_parent(policy, instance, PARENT, "shared:ArchiveUnit")
            if operation == "create" or PARENT in fields:
                _require_targets(
                    policy, instance, previous, PARENT, "shared:ArchiveUnit"
                )
            previous_media = set(values(previous, MEDIA)) if previous else set()
            for media in set(values(instance, MEDIA)) - previous_media:
                target = _read(instance, media, "shared:MediaObject")
                if not policy.is_catalogued(target):
                    raise ArchiveConflict(
                        "Archive units can attach only catalogued media."
                    )
                policy.require_data(target, DataPermission.DATA_VIEW)
    elif is_a(instance, "shared:StagingArea"):
        if operation == "delete":
            raise ArchiveConflict(
                "Use the atomic empty-StagingArea deletion operation."
            )
    elif is_a(instance, "shared:StagingMediaObject"):
        if previous and not _same(
            policy, single(instance, AREA), single(previous, AREA)
        ):
            raise ArchiveConflict("Staging media cannot move between StagingAreas.")
        if operation == "create" or FOLDER_PARENT in fields:
            _require_targets(
                policy, instance, previous, FOLDER_PARENT, "shared:StagingFolder"
            )
            folder = single(instance, FOLDER_PARENT)
            if folder is not None and not _same(
                policy,
                single(_read(instance, folder, "shared:StagingFolder"), AREA),
                single(instance, AREA),
            ):
                raise ArchiveConflict("The staging folder belongs to another area.")
    elif is_a(instance, "shared:StagingFolder"):
        if (
            operation == "create" and values(instance, REFERENCE)
        ) or REFERENCE in fields:
            if not _reference_command.get():
                raise ArchiveConflict(
                    "Use the reference move operation to change private references."
                )
        if DEFAULT in fields or (
            operation in {"create", "delete"} and values(instance, DEFAULT)
        ):
            policy.require_structure()
            _require_targets(policy, instance, previous, DEFAULT, "shared:ArchiveUnit")
            if previous:
                policy.require_data(previous, DataPermission.DATA_UPDATE)
        _folder_integrity(policy, instance, previous, operation)
        if operation == "create" or FOLDER_PARENT in fields:
            _require_targets(
                policy, instance, previous, FOLDER_PARENT, "shared:StagingFolder"
            )
        if operation == "delete":
            _empty(policy, instance)
    return previous


def audit_resource_operation(instance, previous, operation, policy):
    """Commit compact structural history in the same transaction as the change."""
    if not policy.enabled or not (
        is_a(instance, "shared:ArchiveUnit") or is_a(instance, "shared:StagingFolder")
    ):
        return
    before = structural_state(previous) if previous else None
    after = None if operation == "delete" else structural_state(instance)
    if before == after:
        return
    record = {
        "actor": canonical_iri(policy.context, policy.connection.userIri),
        "project": str(policy.project.projectShortName),
        "time": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "iri": canonical_iri(policy.context, instance.iri),
        "before": before,
        "after": after,
    }
    if _audit_command_id.get() is not None:
        record["operationId"] = _audit_command_id.get()
    payload = json.dumps(json.dumps(record, sort_keys=True, separators=(",", ":")))
    policy.connection.transaction_update(
        f"""INSERT DATA {{ GRAPH <urn:oldap:archive-operations> {{
        <urn:oldap:archive:audit:{uuid4()}> <urn:oldap:archive:record> {payload} . }} }}"""
    )


@contextmanager
def reference_command():
    """Internal scope permitting only the domain command's folder-edge updates."""
    token = _reference_command.set(True)
    try:
        yield
    finally:
        _reference_command.reset(token)


@contextmanager
def audit_command(operation_id: str):
    """Associate composed structural audit records with their committed command."""
    token = _audit_command_id.set(operation_id)
    try:
        yield
    finally:
        _audit_command_id.reset(token)
