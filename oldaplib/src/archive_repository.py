"""Atomic private-reference relocation with durable, actor-scoped receipts."""

from datetime import datetime, timezone
import hashlib
import json
import re
from uuid import UUID

from oldaplib.src.archive_domain import (
    REFERENCE,
    AREA,
    is_a,
    single,
    values,
    reference_command,
)
from oldaplib.src.archive_policy import ArchiveConflict, canonical_iri
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.oldaperror import (
    OldapErrorNotFound,
    OldapErrorNoPermission,
    OldapErrorValue,
)
from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.resource_transaction import (
    resource_transaction,
    resource_query,
    archive_policy_for,
)
from oldaplib.src.staging_folder_tree import StagingFolderTree
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_qname import Xsd_QName

RECEIPT_GRAPH = "urn:oldap:archive-operations"


def _digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


def _conflict(code, message):
    error = ArchiveConflict(message)
    error.code = code
    if code == "INVALID_HIERARCHY":
        error.status = 400
    return error


class ArchiveRepository:
    """Move folder-owned references without requiring media write permission.

    The same underlying media and archive-unit resources remain untouched.
    Exact retry results and the request digest are committed with the mutation.
    """

    def __init__(self, connection, project):
        self._con = connection
        self.factory = ResourceInstanceFactory(connection, project)
        self.project = self.factory._project

    def _policy(self):
        policy = archive_policy_for(self._con, self.project)
        if policy is None or not policy.enabled:
            raise OldapErrorNoPermission("Archive repository operations are disabled.")
        return policy

    def folder_revision(self, folder, policy=None):
        """Hash canonical RDF state and folder ACL/membership, including hidden edges.

        The digest conveys no hidden identifiers. Permission to read the folder
        must be established before exposing this value to an ordinary caller.
        """
        policy = policy or self._policy()
        iri = Iri(Xsd_anyURI(canonical_iri(policy.context, folder.iri))).toRdf
        query = (
            policy.context.sparql_context
            + f"""SELECT ?s ?p ?o WHERE {{ GRAPH {self.project.projectShortName}:data {{
            {{ BIND({iri} AS ?s) {iri} ?p ?o }} UNION
            {{ ?s shared:inStagingFolder {iri} . BIND(shared:inStagingFolder AS ?p) BIND({iri} AS ?o) }} UNION
            {{ <<{iri} oldap:attachedToRole ?s>> oldap:hasDataPermission ?o . BIND(oldap:hasDataPermission AS ?p) }}
        }} }}"""
        )
        rows = resource_query(self._con, query)["results"]["bindings"]
        canonical_rows = sorted(
            {
                json.dumps(
                    row, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                )
                for row in rows
            }
        )
        return _digest(canonical_rows)

    def _receipt_iri(self, policy, operation_id, *, command="reference-move"):
        return "urn:oldap:archive:operation:" + _digest(
            [
                canonical_iri(policy.context, self._con.userIri),
                str(self.project.projectShortName),
                command,
                operation_id,
            ]
        )

    def _receipt(self, policy, operation_id, *, command="reference-move"):
        iri = self._receipt_iri(policy, operation_id, command=command)
        query = f"SELECT ?record WHERE {{ GRAPH <{RECEIPT_GRAPH}> {{ <{iri}> <urn:oldap:archive:record> ?record }} }}"
        rows = resource_query(self._con, query)["results"]["bindings"]
        if not rows:
            return None
        if len(rows) != 1:
            raise _conflict(
                "IDEMPOTENCY_CONFLICT", "Operation receipt is inconsistent."
            )
        return json.loads(rows[0]["record"]["value"])

    @staticmethod
    def _operation_id(value):
        try:
            if not isinstance(value, str) or str(UUID(value)) != value.lower():
                raise ValueError()
        except ValueError as error:
            raise OldapErrorValue(
                "Idempotency-Key must be a canonical UUID."
            ) from error
        return str(UUID(value))

    def _visible(self, policy, data, *, writing):
        medium = self.factory.read(Iri(Xsd_anyURI(data["mediaIri"])))
        source = self.factory.read(Iri(Xsd_anyURI(data["sourceFolderIri"])))
        target = self.factory.read(Iri(Xsd_anyURI(data["targetFolderIri"])))
        if not policy.is_catalogued(medium) or not all(
            is_a(folder, "shared:StagingFolder") for folder in (source, target)
        ):
            raise OldapErrorValue(
                "Reference moves require catalogued media and private folders."
            )
        policy.require_data(medium, DataPermission.DATA_VIEW)
        for folder in (source, target):
            policy.require_data(
                folder,
                DataPermission.DATA_UPDATE if writing else DataPermission.DATA_VIEW,
            )
        if single(source, AREA) is None or canonical_iri(
            policy.context, single(source, AREA)
        ) != canonical_iri(policy.context, single(target, AREA)):
            raise _conflict(
                "INVALID_HIERARCHY", "References cannot move between StagingAreas."
            )
        return source, target

    def _protected_paths(self, source, target):
        tree = StagingFolderTree(self._con, self.project)
        for folder in (source, target):
            path = tree.path_to_root(folder.iri)
            if any(
                tree._portable_name_key(tree._name(node)) == "trash" for node in path
            ):
                raise _conflict(
                    "INVALID_HIERARCHY", "Trash is not a reference-move location."
                )
        if tree._portable_name_key(tree._name(target)) == "mobile":
            raise _conflict(
                "INVALID_HIERARCHY", "The Mobile inbox is reserved for capture uploads."
            )

    def move_reference(self, request, *, operation_id):
        """Validate and atomically relocate one edge, or return its exact receipt.

        Args:
            request: Closed v1 body with media/source/target IRIs and two SHA-256
                folder revisions. No metadata or role fields are accepted.
            operation_id: Canonical UUID from the HTTP Idempotency-Key header.
        """
        operation_id = self._operation_id(operation_id)
        expected = {
            "mediaIri",
            "sourceFolderIri",
            "targetFolderIri",
            "sourceRevision",
            "targetRevision",
        }
        if not isinstance(request, dict) or set(request) != expected:
            raise OldapErrorValue("Invalid reference move fields.")
        if not all(
            isinstance(request[key], str)
            and re.fullmatch(r"[0-9a-f]{64}", request[key])
            for key in ("sourceRevision", "targetRevision")
        ):
            raise OldapErrorValue("Reference moves require SHA-256 folder revisions.")
        for key in ("mediaIri", "sourceFolderIri", "targetFolderIri"):
            value = request[key]
            if (
                not isinstance(value, str)
                or len(value) > 2048
                or not re.fullmatch(r'(?:https?://|urn:)[^\s<>"{}|\\^`]+', value)
            ):
                raise OldapErrorValue(
                    "Reference move IRIs must be absolute and at most 2048 characters."
                )
        with resource_transaction(self._con):
            policy = self._policy()
            data = dict(request)
            for key in ("mediaIri", "sourceFolderIri", "targetFolderIri"):
                data[key] = canonical_iri(policy.context, data[key])
            fingerprint = _digest(data)
            replay = self._receipt(policy, operation_id)
            if replay is not None:
                if replay["requestDigest"] != fingerprint:
                    raise _conflict(
                        "IDEMPOTENCY_CONFLICT",
                        "This operation ID belongs to a different request.",
                    )
                self._visible(policy, data, writing=False)
                return replay["result"]
            source, target = self._visible(policy, data, writing=True)
            self._protected_paths(source, target)
            for folder, field in (
                (source, "sourceRevision"),
                (target, "targetRevision"),
            ):
                if self.folder_revision(folder, policy) != data[field]:
                    raise _conflict(
                        "STALE_FOLDER", "A folder changed; reload its inventory."
                    )
            source_edges = {
                canonical_iri(policy.context, iri) for iri in values(source, REFERENCE)
            }
            target_edges = {
                canonical_iri(policy.context, iri) for iri in values(target, REFERENCE)
            }
            if data["mediaIri"] not in source_edges:
                raise _conflict(
                    "STALE_FOLDER", "The source reference no longer exists."
                )
            if data["sourceFolderIri"] != data["targetFolderIri"]:
                with reference_command():
                    remaining = source_edges - {data["mediaIri"]}
                    prop = Xsd_QName(REFERENCE)
                    if remaining:
                        source[prop] = {Iri(Xsd_anyURI(iri)) for iri in remaining}
                    else:
                        del source[prop]
                    source.update()
                    if data["mediaIri"] not in target_edges:
                        target[prop] = {
                            Iri(Xsd_anyURI(iri))
                            for iri in target_edges | {data["mediaIri"]}
                        }
                        target.update()
            result = {
                "operationId": operation_id,
                "state": "committed",
                "mediaIri": data["mediaIri"],
                "sourceFolderIri": data["sourceFolderIri"],
                "targetFolderIri": data["targetFolderIri"],
                "sourceRevision": self.folder_revision(source, policy),
                "targetRevision": self.folder_revision(target, policy),
            }
            record = {
                "requestDigest": fingerprint,
                "actor": canonical_iri(policy.context, self._con.userIri),
                "project": str(self.project.projectShortName),
                "command": "reference-move",
                "time": datetime.now(timezone.utc).isoformat(),
                "before": {
                    "sourceRevision": data["sourceRevision"],
                    "targetRevision": data["targetRevision"],
                },
                "result": result,
            }
            encoded = json.dumps(
                json.dumps(record, sort_keys=True, separators=(",", ":"))
            )
            self._con.transaction_update(
                f"""INSERT DATA {{ GRAPH <{RECEIPT_GRAPH}> {{ <{self._receipt_iri(policy, operation_id)}> <urn:oldap:archive:record> {encoded} . }} }}"""
            )
            return result

    def operation(self, operation_id):
        """Read a committed owner-scoped receipt after checking current visibility."""
        operation_id = self._operation_id(operation_id)
        policy = self._policy()
        receipt = self._receipt(policy, operation_id)
        adoption = self._receipt(policy, operation_id, command="structure-apply")
        if receipt is not None and adoption is not None:
            raise _conflict(
                "IDEMPOTENCY_CONFLICT",
                "This ID identifies more than one command; replay the original command.",
            )
        if adoption is not None:
            from oldaplib.src.archive_adoption import ArchiveAdoption

            ArchiveAdoption(self._con, self.project)._receipt_visible(adoption, policy)
            return adoption["result"]
        if receipt is None:
            raise OldapErrorNotFound("Operation not found.")
        self._visible(policy, receipt["result"], writing=False)
        return receipt["result"]
