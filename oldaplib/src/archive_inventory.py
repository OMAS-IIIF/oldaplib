"""Permission-filtered mixed private-folder inventory with signed keyset cursors."""

import base64
import hashlib
import hmac
import json
import re

from oldaplib.src.archive_domain import AREA, is_a, single, values
from oldaplib.src.archive_policy import canonical_iri
from oldaplib.src.archive_repository import ArchiveRepository, _conflict
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.oldaperror import (
    OldapErrorNotFound,
    OldapErrorNoPermission,
    OldapErrorValue,
)
from oldaplib.src.resource_transaction import resource_transaction, resource_query
from oldaplib.src.staging_folder_tree import StagingFolderTree
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI


class ArchiveInventory:
    """Read direct media children without exposing hidden identifiers or counts.

    Args:
        connection: Task-local authenticated OLDAP connection.
        project: Project understood by ResourceInstanceFactory.
        cursor_secret: Stable server-owned bytes (at least 32); shared by readers.
            The HTTP adapter derives purpose-specific bytes from its access key.
            Direct library callers can supply their own server-owned signing key.
    """

    def __init__(self, connection, project, *, cursor_secret: bytes):
        if not isinstance(cursor_secret, bytes) or len(cursor_secret) < 32:
            raise OldapErrorValue(
                "Inventory requires a server-owned cursor key of at least 32 bytes."
            )
        self.repository = ArchiveRepository(connection, project)
        self._con = connection
        self._key = cursor_secret

    def _encode(self, payload):
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        encoded = base64.urlsafe_b64encode(raw).rstrip(b"=")
        signature = hmac.new(
            self._key, b"oldap:archive-inventory:v1:" + encoded, hashlib.sha256
        ).hexdigest()
        return encoded.decode() + "." + signature

    def _decode(self, cursor):
        try:
            if not isinstance(cursor, str) or len(cursor) > 4096:
                raise ValueError()
            encoded, signature = cursor.rsplit(".", 1)
            expected = hmac.new(
                self._key,
                b"oldap:archive-inventory:v1:" + encoded.encode("ascii"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, signature):
                raise ValueError()
            result = json.loads(
                base64.b64decode(
                    encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True
                )
            )
            if not isinstance(result, dict) or set(result) != {
                "context",
                "revision",
                "last",
            }:
                raise ValueError()
            if (
                not isinstance(result["last"], list)
                or len(result["last"]) != 2
                or not all(isinstance(v, str) for v in result["last"])
                or result["last"][0] not in {"stagingMedia", "archiveReference"}
                or not re.fullmatch(r"[0-9a-f]{64}", result["last"][1])
            ):
                raise ValueError()
            return result
        except (ValueError, TypeError, UnicodeError) as error:
            raise OldapErrorValue("Invalid inventory cursor.") from error

    def page(self, folder_iri, *, limit=50, cursor=None):
        """Return the closed v1 inventory response inside a stable read boundary.

        Cursors bind caller/project/folder/revision/last key. Fresh permissions are
        checked on every page; reference capabilities never authorize media writes.
        A stale folder produces STALE_FOLDER rather than mixing two snapshots.
        """
        if type(limit) is not int or not 1 <= limit <= 100:
            raise OldapErrorValue("Inventory limit must be between 1 and 100.")
        if (
            not isinstance(folder_iri, str)
            or len(folder_iri) > 2048
            or not re.fullmatch(r'(?:https?://|urn:)[^\s<>"{}|\\^`]+', folder_iri)
        ):
            raise OldapErrorValue("Inventory requires an absolute folder IRI.")
        decoded = self._decode(cursor) if cursor is not None else None
        with resource_transaction(self._con):
            policy = self.repository._policy()
            folder = self.repository.factory.read(Iri(Xsd_anyURI(folder_iri)))
            if not is_a(folder, "shared:StagingFolder"):
                raise OldapErrorValue("Inventory requires a private folder.")
            policy.require_data(folder, DataPermission.DATA_VIEW)
            identity = {
                "actor": canonical_iri(policy.context, self._con.userIri),
                "project": str(self.repository.project.projectShortName),
                "folder": canonical_iri(policy.context, folder.iri),
            }
            context_digest = hashlib.sha256(
                json.dumps(identity, sort_keys=True).encode()
            ).hexdigest()
            if decoded is not None and decoded["context"] != context_digest:
                raise OldapErrorValue(
                    "Inventory cursor belongs to a different context."
                )
            revision = self.repository.folder_revision(folder, policy)
            if decoded is not None and decoded["revision"] != revision:
                raise _conflict(
                    "STALE_FOLDER", "The folder changed; reload its inventory."
                )
            rows = self._rows(
                policy, folder, limit + 1, decoded["last"] if decoded else None
            )
            selected = rows[:limit]
            tree = StagingFolderTree(self._con, self.repository.project)
            path = tree.path_to_root(folder.iri)
            in_trash = any(
                tree._portable_name_key(tree._name(node)) == "trash" for node in path
            )
            folder_update = policy.is_admin() or folder.get_data_permission(
                DataPermission.DATA_UPDATE
            )
            entries = []
            for row in selected:
                try:
                    medium = self.repository.factory.read(
                        Iri(Xsd_anyURI(row["media"]["value"]))
                    )
                    policy.require_data(medium, DataPermission.DATA_VIEW)
                except (OldapErrorNotFound, OldapErrorNoPermission):
                    continue
                reference = row["kind"]["value"] == "archiveReference"
                if reference and not policy.is_catalogued(medium):
                    continue
                if not reference and not is_a(medium, "shared:StagingMediaObject"):
                    continue
                title_values = values(medium, "schema:name") or values(
                    medium, "shared:originalName"
                )
                title = sorted(str(v) for v in title_values)[0] if title_values else ""
                can_update = not reference and (
                    policy.is_admin()
                    or medium.get_data_permission(DataPermission.DATA_UPDATE)
                )
                can_delete = not reference and (
                    policy.is_admin()
                    or medium.get_data_permission(DataPermission.DATA_DELETE)
                )
                entries.append(
                    {
                        "kind": row["kind"]["value"],
                        "mediaIri": row["media"]["value"],
                        "title": title[:1000],
                        "canDownloadOriginal": str(
                            single(medium, "shared:mediaAccessMode")
                        )
                        == "local"
                        and bool(values(medium, "shared:assetId"))
                        and bool(values(medium, "shared:path")),
                        "canEditMetadata": bool(can_update),
                        "canMove": bool(
                            folder_update and not in_trash and (reference or can_update)
                        ),
                        "canDeleteMedia": bool(can_delete),
                    }
                )
            next_cursor = None
            if len(rows) > limit:
                last = selected[-1]
                next_cursor = self._encode(
                    {
                        "context": context_digest,
                        "revision": revision,
                        "last": [
                            last["kind"]["value"],
                            hashlib.sha256(last["media"]["value"].encode()).hexdigest(),
                        ],
                    }
                )
            return {
                "folderIri": identity["folder"],
                "revision": revision,
                "entries": entries,
                "nextCursor": next_cursor,
                "warnings": [],
            }

    def _rows(self, policy, folder, limit, last):
        """Page visible identities in SPARQL before reading any media metadata."""
        folder_term = Iri(Xsd_anyURI(canonical_iri(policy.context, folder.iri))).toRdf
        area = single(folder, AREA)
        if area is None:
            raise _conflict("INVALID_HIERARCHY", "The folder has no private area.")
        area_term = Iri(Xsd_anyURI(canonical_iri(policy.context, area))).toRdf
        graph = f"{self.repository.project.projectShortName}:data"
        after = ""
        if last is not None:
            # Hash the last IRI in the cursor so even a maximum-length Unicode
            # IRI fits the frozen cursor limit. Resolve it only inside the same
            # revision-bound folder; do not expose a formerly visible identity.
            relation = (
                f"{folder_term} shared:referencedMediaObject ?media"
                if last[0] == "archiveReference"
                else f"?media shared:inStagingFolder {folder_term}"
            )
            lookup = (
                policy.context.sparql_context
                + f"SELECT DISTINCT ?media WHERE {{ GRAPH {graph} {{ {relation} }} FILTER(SHA256(STR(?media)) = {json.dumps(last[1])}) }} LIMIT 2"
            )
            matches = resource_query(self._con, lookup)["results"]["bindings"]
            if len(matches) != 1:
                raise _conflict(
                    "STALE_FOLDER",
                    "The cursor position no longer exists; reload the inventory.",
                )
            kind, media = map(json.dumps, (last[0], matches[0]["media"]["value"]))
            after = (
                f"FILTER (?kind > {kind} || (?kind = {kind} && STR(?media) > {media}))"
            )
        catalogues = " ".join(f"<{iri}>" for iri in policy.media_classes)
        query = (
            policy.context.sparql_context + f"""SELECT DISTINCT ?kind ?media WHERE {{
          {{ GRAPH {graph} {{ ?media a ?class ; shared:inStagingFolder {folder_term} ; shared:inStagingArea {area_term} }}
             ?class rdfs:subClassOf* shared:StagingMediaObject . BIND("stagingMedia" AS ?kind) }}
          UNION
          {{ GRAPH {graph} {{ {folder_term} shared:referencedMediaObject ?media . ?media a ?class }}
             VALUES ?catalogue {{ {catalogues} }} ?class rdfs:subClassOf* ?catalogue . BIND("archiveReference" AS ?kind) }}
          FILTER EXISTS {{
            {{ GRAPH {graph} {{ ?media oldap:createdBy {self._con.userIri.toRdf} }} }} UNION
            {{ GRAPH oldap:admin {{ {self._con.userIri.toRdf} oldap:hasRole ?role . ?permission oldap:permissionValue ?value . FILTER (?value >= 2) }}
               GRAPH {graph} {{ ?media oldap:attachedToRole ?role . <<?media oldap:attachedToRole ?role>> oldap:hasDataPermission ?permission }} }}
          }}
          {after}
        }} ORDER BY ?kind STR(?media) LIMIT {limit}"""
        )
        return resource_query(self._con, query)["results"]["bindings"]
