"""Reviewed, project-neutral archive adoption with stateless preflight and receipts.

Existing archive units are only referenced, never renamed/reparented as an import
side effect. Every read/check/write participates in the shared writer boundary.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import rfc8785

from oldaplib.src.archive_domain import DEFAULT, PARENT, is_a, single, audit_command
from oldaplib.src.archive_policy import canonical_iri
from oldaplib.src.archive_repository import ArchiveRepository, _conflict
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.datapermissions import DataPermission as DP
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import (
    OldapErrorValue,
    OldapErrorNoPermission,
)
from oldaplib.src.resource_transaction import resource_transaction, resource_query
from oldaplib.src.staging_folder_tree import StagingFolderTree
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_qname import Xsd_QName

SCHEMA = json.loads(
    Path(__file__)
    .with_name("schemas")
    .joinpath("archive_structure_v1.json")
    .read_text()
)
VALIDATORS = {
    name: Draft202012Validator({**SCHEMA, "$ref": "#/$defs/" + name})
    for name in ("ProposalRequest", "PreflightRequest", "ApplyRequest")
}
MAX_FOLDERS = 5000
MAX_MUTATIONS = 500
COMMAND = "structure-apply"


def digest(value):
    """Hash the RFC-8785 representation used by source and review contracts."""
    return hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def too_large(message):
    error = _conflict("TOO_LARGE", message)
    error.status = 413
    return error


def validate(body, schema):
    """Reject oversized/invalid closed protocol bodies before database work."""
    try:
        if len(rfc8785.dumps(body)) > 2_000_000:
            raise too_large("Select a smaller archive request.")
    except (ValueError, TypeError) as error:
        raise OldapErrorValue("Invalid JSON archive request.") from error
    if isinstance(body, dict) and isinstance(plan := body.get("plan"), dict):
        for field in ("newUnits", "mappings"):
            if isinstance(plan.get(field), list) and len(plan[field]) > MAX_MUTATIONS:
                raise too_large("The plan exceeds the supported action limit.")
    if next(VALIDATORS[schema].iter_errors(body), None) is not None:
        raise OldapErrorValue("The archive request does not match the v1 contract.")


def normal_plan(plan):
    """Normalize optional positions and order without changing editorial text."""
    result = deepcopy(plan)
    result["newUnits"] = sorted(
        ({**unit, "position": unit.get("position")} for unit in result["newUnits"]),
        key=lambda u: u["key"],
    )
    result["mappings"] = sorted(result["mappings"], key=lambda m: m["folderIri"])
    return result


def plan_order(plan):
    """Return parent-first units; reject duplicate keys, cycles and unused units."""
    units = {unit["key"]: unit for unit in plan["newUnits"]}
    if len(units) != len(plan["newUnits"]):
        raise OldapErrorValue("New unit keys must be unique.")
    folders = [mapping["folderIri"] for mapping in plan["mappings"]]
    if len(set(folders)) != len(folders):
        raise OldapErrorValue("Each source folder may have only one mapping action.")
    pending = dict(units)
    ordered = []
    known = set()
    while pending:
        ready = [
            key
            for key, unit in pending.items()
            if not unit["parent"]
            or "iri" in unit["parent"]
            or unit["parent"].get("key") in known
        ]
        if not ready:
            raise _conflict(
                "INVALID_HIERARCHY", "New unit parents contain a cycle or unknown key."
            )
        for key in ready:
            ordered.append(pending.pop(key))
            known.add(key)
    used = set()
    for mapping in plan["mappings"]:
        if mapping["action"] != "set" or "key" not in mapping["target"]:
            continue
        key = mapping["target"]["key"]
        if key not in units:
            raise OldapErrorValue("Mapping refers to an unknown new unit key.")
        while key is not None and key not in used:
            used.add(key)
            parent = units[key]["parent"]
            key = parent.get("key") if parent else None
    if used != set(units):
        raise OldapErrorValue("Every new unit must lead to a mapped target.")
    mutations = len(units) + sum(m["action"] != "skip" for m in plan["mappings"])
    if mutations > MAX_MUTATIONS:
        raise too_large(
            "The plan exceeds 500 mutating actions; select a smaller subtree."
        )
    return ordered


class ArchiveAdoption(ArchiveRepository):
    """Propose and atomically apply reviewed creates and explicit folder mappings."""

    def _term(self, iri):
        return Iri(Xsd_anyURI(iri)).toRdf

    def _query(self, query, policy):
        return resource_query(self._con, policy.context.sparql_context + query)[
            "results"
        ]["bindings"]

    def _visibility(self, subject):
        return f"""FILTER EXISTS {{
          {{ GRAPH {self.project.projectShortName}:data {{ {subject} oldap:createdBy {self._con.userIri.toRdf} }} }} UNION
          {{ GRAPH oldap:admin {{ {self._con.userIri.toRdf} oldap:hasRole ?accessRole . ?accessPermission oldap:permissionValue ?accessValue . FILTER(?accessValue >= 2) }}
             GRAPH {self.project.projectShortName}:data {{ {subject} oldap:attachedToRole ?accessRole . <<{subject} oldap:attachedToRole ?accessRole>> oldap:hasDataPermission ?accessPermission }} }}
        }}"""

    def _states(self, iris, policy):
        """Batch complete RDF/ACL and membership digests without disclosing hidden facts."""
        states = {iri: [] for iri in iris}
        if not states:
            return states
        terms = " ".join(self._term(iri) for iri in sorted(states))
        rows = self._query(
            f"""SELECT ?resource ?s ?p ?o WHERE {{ VALUES ?resource {{ {terms} }}
          GRAPH {self.project.projectShortName}:data {{
            {{ BIND(?resource AS ?s) ?resource ?p ?o }} UNION
            {{ ?s shared:inStagingFolder ?resource . BIND(shared:inStagingFolder AS ?p) BIND(?resource AS ?o) }} UNION
            {{ <<?resource oldap:attachedToRole ?s>> oldap:hasDataPermission ?o . BIND(oldap:hasDataPermission AS ?p) }}
          }} }}""",
            policy,
        )
        for row in rows:
            states[row["resource"]["value"]].append(
                {k: v for k, v in row.items() if k != "resource"}
            )
        return states

    @staticmethod
    def _revision(rows):
        # Match ArchiveRepository.folder_revision's canonical RDF row digest.
        from oldaplib.src.archive_repository import _digest

        return _digest(
            sorted(
                {
                    json.dumps(
                        row, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                    )
                    for row in rows
                }
            )
        )

    @staticmethod
    def _value(rows, iri, predicate):
        found = {
            row["o"]["value"]
            for row in rows
            if row["s"]["value"] == iri and row["p"]["value"] == predicate
        }
        if len(found) > 1:
            raise _conflict(
                "INVALID_HIERARCHY", "A source property has multiple values."
            )
        return next(iter(found), None)

    def _source(self, source_iri, policy):
        """Read the connected visible subtree, excluding protected inbox branches."""
        root = self.factory.read(Iri(Xsd_anyURI(source_iri)))
        if not is_a(root, "shared:StagingFolder"):
            raise OldapErrorValue("The source must be a private folder.")
        policy.require_data(root, DP.DATA_VIEW)
        area = single(root, "shared:inStagingArea")
        if area is None:
            raise _conflict("INVALID_HIERARCHY", "The source has no private area.")
        area = canonical_iri(policy.context, area)
        tree = StagingFolderTree(self._con, self.project)
        path = tree.path_to_root(root.iri)
        blocked = any(
            tree._portable_name_key(tree._name(node)) in {"trash", "mobile"}
            for node in path
        )
        ids = {source_iri}
        if not blocked:
            rows = self._query(
                f"""SELECT DISTINCT ?folder WHERE {{
              GRAPH {self.project.projectShortName}:data {{
                ?folder shared:inStagingFolder* {self._term(source_iri)} ; a ?class ; shared:inStagingArea {self._term(area)} .
                FILTER NOT EXISTS {{ ?folder shared:inStagingFolder* ?system . ?system schema:name ?name . FILTER(LCASE(STR(?name)) IN ("trash","mobile")) }}
              }} ?class rdfs:subClassOf* shared:StagingFolder . {self._visibility('?folder')}
            }} LIMIT {MAX_FOLDERS+1}""",
                policy,
            )
            ids.update(row["folder"]["value"] for row in rows)
        if len(ids) > MAX_FOLDERS:
            raise too_large(
                "The source exceeds 5000 visible folders; select a smaller subtree."
            )
        states = self._states(ids, policy)
        # Resolve fixed vocabulary once, not once per source folder/RDF row.
        parent_predicate = canonical_iri(policy.context, "shared:inStagingFolder")
        name_predicate = canonical_iri(policy.context, "schema:name")
        default_predicate = canonical_iri(policy.context, DEFAULT)
        parents = {
            iri: self._value(rows, iri, parent_predicate)
            for iri, rows in states.items()
        }
        excluded = {
            iri
            for iri, rows in states.items()
            if tree._portable_name_key(self._value(rows, iri, name_predicate) or "")
            in {"trash", "mobile"}
        }
        connected = {source_iri}
        while True:
            more = {
                iri
                for iri, parent in parents.items()
                if parent in connected
                and parent not in excluded
                and iri not in excluded
            } - connected
            if not more:
                break
            connected.update(more)
        mappings = {
            iri: self._value(states[iri], iri, default_predicate) for iri in connected
        }
        target_ids = {target for target in mappings.values() if target}
        visible_targets = set()
        if target_ids:
            terms = " ".join(self._term(iri) for iri in sorted(target_ids))
            visible_targets = {
                row["target"]["value"]
                for row in self._query(
                    f"""SELECT DISTINCT ?target WHERE {{
                VALUES ?target {{ {terms} }} GRAPH {self.project.projectShortName}:data {{ ?target a ?class }}
                ?class rdfs:subClassOf* shared:ArchiveUnit . {self._visibility('?target')} }}""",
                    policy,
                )
            }
        target_states = self._states(visible_targets, policy)
        folders = []
        for iri in sorted(connected):
            name = self._value(states[iri], iri, name_predicate)
            if name is None or len(name) > 1000:
                raise OldapErrorValue("The source contains an unsupported folder name.")
            target = mappings[iri]
            folders.append(
                {
                    "iri": iri,
                    "parentIri": parents[iri],
                    "name": name,
                    "revision": self._revision(states[iri]),
                    "defaultArchiveUnitIri": (
                        target if target in visible_targets else None
                    ),
                    "mappingState": (
                        "unmapped"
                        if target is None
                        else "mapped" if target in visible_targets else "unavailable"
                    ),
                    "protected": blocked or tree._is_reserved(name),
                }
            )
        snapshot = digest(
            {
                "folders": folders,
                "targets": {
                    iri: self._revision(target_states[iri])
                    for iri in sorted(visible_targets)
                },
            }
        )
        return {
            "sourceFolderIri": source_iri,
            "stagingAreaIri": area,
            "sourceSnapshot": snapshot,
            "folders": folders,
        }, states

    def proposal(self, body):
        """Return editable conservative suggestions without persisting resources.

        Args:
            body: Frozen ProposalRequest containing the selected sourceFolderIri.

        Returns:
            ProposalResponse with visible folder facts, snapshot, plan and warnings.

        Raises:
            OldapError: If access, coordination, source integrity or limits fail.
        """
        validate(body, "ProposalRequest")
        with resource_transaction(self._con):
            policy = self._policy()
            policy.require_structure()
            source, _ = self._source(body["sourceFolderIri"], policy)
            by_iri = {f["iri"]: f for f in source["folders"]}
            new = []
            mappings = []
            targets = {}
            unavailable = set()
            pending = dict(by_iri)
            while pending:
                ready = [
                    iri
                    for iri, row in pending.items()
                    if row["parentIri"] not in pending
                ]
                if not ready:
                    raise _conflict(
                        "INVALID_HIERARCHY", "Source hierarchy contains a cycle."
                    )
                for iri in sorted(ready):
                    row = pending.pop(iri)
                    parent = row["parentIri"]
                    if row["mappingState"] == "unavailable" or parent in unavailable:
                        unavailable.add(iri)
                        continue
                    if row["mappingState"] == "mapped":
                        targets[iri] = {"iri": row["defaultArchiveUnitIri"]}
                        continue
                    if row["protected"]:
                        continue
                    key = "folder-" + hashlib.sha256(iri.encode()).hexdigest()[:20]
                    targets[iri] = {"key": key}
                    new.append(
                        {
                            "key": key,
                            "name": {
                                LangString.defaultLanguage.name.lower(): row["name"]
                            },
                            "archiveLevel": (
                                "shared:Series"
                                if any(
                                    f["parentIri"] == iri and not f["protected"]
                                    for f in by_iri.values()
                                )
                                else "shared:File"
                            ),
                            "parent": targets.get(parent),
                            "position": None,
                        }
                    )
                    mappings.append(
                        {"folderIri": iri, "action": "set", "target": {"key": key}}
                    )
            plan = {
                "sourceFolderIri": source["sourceFolderIri"],
                "sourceSnapshot": source["sourceSnapshot"],
                "newUnits": new,
                "mappings": mappings,
            }
            warnings = []
            if unavailable:
                warnings.append(
                    {
                        "code": "MAPPING_UNAVAILABLE",
                        "message": "Unavailable mappings and their descendant suggestions were left unchanged.",
                    }
                )
            if not new:
                warnings.append(
                    {
                        "code": "NO_NEW_UNITS",
                        "message": "No eligible unmapped source folders require new archive units.",
                    }
                )
            if len(new) + len(mappings) > MAX_MUTATIONS:
                raise too_large(
                    "The proposal exceeds 500 mutating actions; select a smaller subtree."
                )
            return {**source, "suggestedPlan": normal_plan(plan), "warnings": warnings}

    def _review(self, raw_plan, policy):
        """Resolve model, rights and revisions; return review plus transaction-local inputs.

        The caller owns the writer boundary. Returned instances must be consumed
        within that boundary and discarded after rollback, never cached globally.
        """
        plan = normal_plan(raw_plan)
        ordered = plan_order(plan)
        policy.require_structure()
        source, states = self._source(plan["sourceFolderIri"], policy)
        if source["sourceSnapshot"] != plan["sourceSnapshot"]:
            raise _conflict(
                "STALE_REVIEW", "The source changed; create a fresh proposal."
            )
        folders = {row["iri"]: row for row in source["folders"]}
        existing = set()
        instances = {}
        for mapping in plan["mappings"]:
            row = folders.get(mapping["folderIri"])
            if row is None or row["protected"]:
                raise _conflict(
                    "INVALID_HIERARCHY",
                    "Mapping actions must use eligible folders in the reviewed subtree.",
                )
            if mapping["action"] == "skip":
                continue
            if row["mappingState"] == "unavailable":
                raise OldapErrorNoPermission(
                    "An unavailable mapping cannot be overwritten or cleared."
                )
            folder = self.factory.read(Iri(Xsd_anyURI(row["iri"])))
            policy.require_data(folder, DP.DATA_UPDATE)
            instances[row["iri"]] = folder
            if row["defaultArchiveUnitIri"]:
                existing.add(row["defaultArchiveUnitIri"])
            if mapping["action"] == "set" and "iri" in mapping["target"]:
                existing.add(mapping["target"]["iri"])
        for unit in ordered:
            if unit["parent"] and "iri" in unit["parent"]:
                existing.add(unit["parent"]["iri"])
        targets = {}
        queue = list(existing)
        while queue:
            iri = queue.pop()
            if iri in targets:
                continue
            if len(targets) >= MAX_FOLDERS:
                raise too_large(
                    "The existing target ancestry exceeds the supported limit."
                )
            target = self.factory.read(Iri(Xsd_anyURI(iri)))
            if not is_a(target, "shared:ArchiveUnit"):
                raise OldapErrorValue(
                    "Existing targets must be archive units in this project."
                )
            policy.require_data(
                target, DP.DATA_UPDATE if iri in existing else DP.DATA_VIEW
            )
            targets[iri] = target
            parent = single(target, PARENT)
            if parent:
                queue.append(canonical_iri(policy.context, parent))
        # Check existing ancestry, including malformed stored cycles, once per target.
        for iri in existing:
            seen = set()
            current = iri
            while current is not None:
                if current in seen:
                    raise _conflict(
                        "INVALID_HIERARCHY",
                        "Existing archive ancestry contains a cycle.",
                    )
                seen.add(current)
                parent = single(targets[current], PARENT)
                current = canonical_iri(policy.context, parent) if parent else None
        Unit = self.factory.createObjectInstance("shared:ArchiveUnit")
        units = {unit["key"]: unit for unit in ordered}
        grants = self._unit_grants(plan, units, states, policy)
        if ordered:
            allowed, _ = Unit(
                name=LangString("Permission check@en"), archiveLevel="shared:Series"
            ).check_for_permissions(AdminPermission.ADMIN_CREATE)
            if not allowed:
                raise OldapErrorNoPermission(
                    "Creating archive units requires ADMIN_CREATE."
                )
            # Validate vocabulary and source-derived ACLs before any mutation.
            for level in {unit["archiveLevel"] for unit in ordered}:
                if not resource_query(
                    self._con,
                    policy.context.sparql_context
                    + f"ASK {{ {self._term(canonical_iri(policy.context, level))} a shared:ArchiveLevel }}",
                )["boolean"]:
                    raise OldapErrorValue(
                        "An archive unit requires a valid shared:ArchiveLevel."
                    )
            for unit in ordered:
                Unit(
                    name=self._name(unit),
                    archiveLevel=unit["archiveLevel"],
                    attachedToRole=grants[unit["key"]],
                    **(
                        {"position": unit["position"]}
                        if unit["position"] is not None
                        else {}
                    ),
                )
        revisions = {
            iri: self._revision(rows)
            for iri, rows in self._states(targets, policy).items()
        }
        policy_state = {
            "enabled": policy.enabled,
            "structure": sorted(policy.structure_roles),
            "editorial": sorted(policy.editorial_roles),
            "media": sorted(policy.media_classes),
            "note": policy.note_property,
        }
        review = digest(
            {
                "plan": plan,
                "sourceSnapshot": source["sourceSnapshot"],
                "targets": revisions,
                "policy": policy_state,
            }
        )
        counts = {
            key: sum(m["action"] == key for m in plan["mappings"])
            for key in ("set", "clear", "skip")
        }
        counts["create"] = len(ordered)
        return (
            {"reviewDigest": review, "counts": counts, "warnings": []},
            plan,
            ordered,
            instances,
            grants,
        )

    @staticmethod
    def _name(unit):
        return LangString(
            [f"{text}@{language}" for language, text in unit["name"].items()]
        )

    def preflight(self, body):
        """Validate the exact model, rights and state without persisting a draft.

        Args:
            body: Frozen PreflightRequest containing the complete edited plan.

        Returns:
            PreflightResponse containing the review digest, counts and warnings.
        """
        validate(body, "PreflightRequest")
        with resource_transaction(self._con):
            return self._review(body["plan"], self._policy())[0]

    def _unit_grants(self, plan, units, states, policy):
        """Compute source-scoped grants once for the complete reviewed creation tree.

        Each folder's RDF roles are parsed once, then propagated to its new target
        and new ancestors. Structure grants retain at most DELETE, other roles
        UPDATE, and Unknown VIEW. Policy-only roles are never implicitly added.
        The returned grants belong to this review and are reused only inside its
        coordinated apply; they are not a cross-request permission cache.
        """
        grants = {key: {} for key in units}
        if not units:
            return grants
        permission_predicate = canonical_iri(policy.context, "oldap:hasDataPermission")
        unknown_role = canonical_iri(policy.context, "oldap:Unknown")
        roles = {}
        permissions = {}
        for mapping in plan["mappings"]:
            if mapping["action"] != "set" or "key" not in mapping["target"]:
                continue
            folder_grants = {}
            for row in states[mapping["folderIri"]]:
                if row["p"]["value"] != permission_predicate:
                    continue
                role = row["s"]["value"]
                permission_iri = row["o"]["value"]
                if permission_iri not in permissions:
                    permissions[permission_iri] = DP.from_qname(
                        policy.context.iri2qname(permission_iri)
                    )
                if role not in roles:
                    roles[role] = policy.context.iri2qname(role)
                cap = (
                    DP.DATA_DELETE if role in policy.structure_roles else DP.DATA_UPDATE
                )
                if role == unknown_role:
                    cap = DP.DATA_VIEW
                capped = min(permissions[permission_iri], cap)
                if role not in folder_grants or folder_grants[role] < capped:
                    folder_grants[role] = capped
            current = mapping["target"]["key"]
            while current is not None:
                for role, permission in folder_grants.items():
                    if (
                        role not in grants[current]
                        or grants[current][role] < permission
                    ):
                        grants[current][role] = permission
                parent = units[current]["parent"]
                current = parent.get("key") if parent else None
        return {
            key: {roles[role]: permission for role, permission in granted.items()}
            for key, granted in grants.items()
        }

    def _receipt_visible(self, record, policy):
        for iri in record["visibleIris"]:
            policy.require_data(self.factory.read(Iri(Xsd_anyURI(iri))), DP.DATA_VIEW)

    def apply(self, body, *, operation_id):
        """Commit reviewed mutations, structural audit and receipt atomically.

        Args:
            body: Frozen ApplyRequest containing plan, reviewDigest and confirm=true.
            operation_id: UUID identifying this caller/project/command request.

        Returns:
            Committed ApplyResponse, including exact currently visible retries.

        Raises:
            ArchiveConflict: If the review is stale or the key has different content.
            OldapError: If access, validation or coordination fails; writes roll back.
        """
        validate(body, "ApplyRequest")
        operation_id = self._operation_id(operation_id)
        request_digest = digest({**body, "plan": normal_plan(body["plan"])})
        with resource_transaction(self._con), audit_command(operation_id):
            policy = self._policy()
            replay = self._receipt(policy, operation_id, command=COMMAND)
            if replay is not None:
                if replay["requestDigest"] != request_digest:
                    raise _conflict(
                        "IDEMPOTENCY_CONFLICT",
                        "This operation ID belongs to a different request.",
                    )
                self._receipt_visible(replay, policy)
                return replay["result"]
            review, plan, ordered, folders, grants = self._review(body["plan"], policy)
            if review["reviewDigest"] != body["reviewDigest"]:
                raise _conflict(
                    "STALE_REVIEW",
                    "The reviewed targets or policy changed; preflight again.",
                )
            iris = {unit["key"]: Iri() for unit in ordered}
            Unit = self.factory.createObjectInstance("shared:ArchiveUnit")

            def resolve(target):
                return (
                    iris[target["key"]]
                    if "key" in target
                    else Iri(Xsd_anyURI(target["iri"]))
                )

            for unit in ordered:
                kwargs = {
                    "name": self._name(unit),
                    "archiveLevel": unit["archiveLevel"],
                    "attachedToRole": grants[unit["key"]],
                }
                if unit["parent"]:
                    kwargs["parentArchiveUnit"] = resolve(unit["parent"])
                if unit["position"] is not None:
                    kwargs["position"] = unit["position"]
                Unit(iri=iris[unit["key"]], **kwargs).create()
            changes = []
            for mapping in plan["mappings"]:
                if mapping["action"] == "skip":
                    continue
                folder = folders[mapping["folderIri"]]
                target = (
                    resolve(mapping["target"]) if mapping["action"] == "set" else None
                )
                if target is not None:
                    folder[Xsd_QName(DEFAULT)] = {target}
                elif single(folder, DEFAULT) is not None:
                    del folder[Xsd_QName(DEFAULT)]
                folder.update()
                changes.append(
                    {
                        "folderIri": mapping["folderIri"],
                        "targetIri": (
                            canonical_iri(policy.context, target) if target else None
                        ),
                    }
                )
            result = {
                "operationId": operation_id,
                "state": "committed",
                "reviewDigest": review["reviewDigest"],
                "createdUnits": [
                    {"key": key, "iri": canonical_iri(policy.context, iri)}
                    for key, iri in sorted(iris.items())
                ],
                "mappings": changes,
            }
            visible = {
                plan["sourceFolderIri"],
                *(row["iri"] for row in result["createdUnits"]),
                *(row["folderIri"] for row in changes),
                *(row["targetIri"] for row in changes if row["targetIri"]),
            }
            record = {
                "command": COMMAND,
                "actor": canonical_iri(policy.context, self._con.userIri),
                "project": str(self.project.projectShortName),
                "time": datetime.now(timezone.utc).isoformat(),
                "requestDigest": request_digest,
                "visibleIris": sorted(visible),
                "result": result,
            }
            encoded = json.dumps(
                json.dumps(record, sort_keys=True, separators=(",", ":"))
            )
            self._con.transaction_update(
                f"""INSERT DATA {{ GRAPH <urn:oldap:archive-operations> {{
              <{self._receipt_iri(policy,operation_id,command=COMMAND)}> <urn:oldap:archive:record> {encoded} . }} }}"""
            )
            return result
