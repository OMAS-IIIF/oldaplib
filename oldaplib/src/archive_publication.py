"""Project-configured, revision-bound publication of roots and related media.

Only this command changes publication state/public grants on opted-in classes.
It never accepts arbitrary metadata or role assignments. The durable resource
transaction commits the complete set and its idempotency receipt together.
"""

from datetime import datetime, timezone
import json

from oldaplib.src.archive_domain import single, values
from oldaplib.src.archive_policy import ArchiveConflict, canonical_iri, _absolute

from oldaplib.src.archive_repository import ArchiveRepository, RECEIPT_GRAPH, _digest
from oldaplib.src.enums.datapermissions import DataPermission as DP
from oldaplib.src.helpers.oldaperror import (
    OldapErrorConfiguration,
    OldapErrorNoPermission,
    OldapErrorNotFound,
    OldapErrorValue,
)
from oldaplib.src.resource_transaction import resource_transaction, resource_query
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_qname import Xsd_QName as Q


class PublicationConflict(ArchiveConflict):
    """A publication invariant or reviewed revision prevents the command."""

    code = "PUBLICATION_CONFLICT"


def validate_definition(definition):
    """Validate closed, project-neutral configuration without database access."""
    lists = ("publisherRoleIris", "rootClassIris", "mediaClassIris")
    scalar = (
        "statusPropertyIri",
        "publishedStatusIri",
        "mediaToRootPropertyIri",
        "publicRoleIri",
    )
    if not isinstance(definition, dict) or set(definition) != set(
        lists + scalar + ("maxResources",)
    ):
        raise OldapErrorConfiguration("Invalid publication policy fields.")
    for key in lists:
        entries = definition[key]
        if (
            not isinstance(entries, list)
            or not 1 <= len(entries) <= 100
            or any(not isinstance(entry, str) for entry in entries)
            or len(set(entries)) != len(entries)
        ):
            raise OldapErrorConfiguration(
                "Publication role/class lists must be nonempty and unique."
            )
        for iri in entries:
            _absolute(iri)
    if set(definition["rootClassIris"]) & set(definition["mediaClassIris"]):
        raise OldapErrorConfiguration(
            "Publication root and media classes must be distinct."
        )
    for key in scalar:
        _absolute(definition[key])
    if (
        type(definition["maxResources"]) is not int
        or not 1 <= definition["maxResources"] <= 500
    ):
        raise OldapErrorConfiguration("Publication maxResources must be 1..500.")


def validate_resources(policy, factory):
    """Reject unresolved or unsafe publication configuration before any mutation.

    Roles must exist, publisher roles belong to this project, and each target
    model must define the configured status (and media relation where relevant).
    Model assignment during review validates the configured published value.
    """
    definition = policy.publication
    for role in definition["publisherRoleIris"]:
        query = (
            policy.context.sparql_context
            + f"ASK {{ GRAPH oldap:admin {{ <{role}> a oldap:Role ; oldap:definedByProject {policy.project.projectIri.toRdf} }} }}"
        )
        if not resource_query(policy.connection, query)["boolean"]:
            raise OldapErrorConfiguration(
                "A publisher role does not belong to the project."
            )
    query = (
        policy.context.sparql_context
        + f"ASK {{ GRAPH oldap:admin {{ <{definition['publicRoleIri']}> a oldap:Role }} }}"
    )
    if not resource_query(policy.connection, query)["boolean"]:
        raise OldapErrorConfiguration("The public role does not exist.")
    names = {}
    for key in ("statusPropertyIri", "mediaToRootPropertyIri"):
        qname = policy.context.iri2qname(definition[key])
        if qname is None or str(qname).startswith("oldap:"):
            raise OldapErrorConfiguration(
                "Publication properties must be resolved domain properties."
            )
        names[key] = Q(qname)
    if names["statusPropertyIri"] == names["mediaToRootPropertyIri"]:
        raise OldapErrorConfiguration(
            "Status and relation properties must be distinct."
        )
    for key in ("rootClassIris", "mediaClassIris"):
        for iri in definition[key]:
            qname = policy.context.iri2qname(iri)
            if qname is None:
                raise OldapErrorConfiguration("Publication class namespace is unknown.")
            model = factory.createObjectInstance(qname)
            # Factory models expose their property definitions on the class.
            if names["statusPropertyIri"] not in model.resolved_properties():
                raise OldapErrorConfiguration(
                    "Publication status is missing from a configured class."
                )
            if (
                key == "mediaClassIris"
                and names["mediaToRootPropertyIri"] not in model.resolved_properties()
            ):
                raise OldapErrorConfiguration(
                    "Publication relation is missing from a media class."
                )


def _iri(value):
    return Iri(Xsd_anyURI(_absolute(value)))


def _kind(instance, definition):
    from oldaplib.src.objectfactory import resource_class_is_or_extends
    from oldaplib.src.helpers.context import Context

    model = instance if isinstance(instance, type) else type(instance)
    context = Context(name=instance._con.context_name)
    for kind, key in (("media", "mediaClassIris"), ("root", "rootClassIris")):
        if any(
            resource_class_is_or_extends(model, context.iri2qname(iri))
            for iri in definition[key]
        ):
            return kind
    return None


def _public_permission(instance, policy, definition):
    for role, permission in (instance.attachedToRoleAnnotation or {}).items():
        if canonical_iri(policy.context, role) == definition["publicRoleIri"]:
            return permission
    return None


def guard_publication(instance, operation, args, kwargs, policy, previous):
    """Prevent generic writes from bypassing the configured publication command.

    Creator and administrative CRUD shortcuts deliberately do not bypass this
    domain guard. Unconfigured classes/projects retain their prior semantics.
    """
    definition = policy.publication
    if not definition:
        return
    target = instance
    if operation == "transform_class":
        # transform target resolution is performed by the surrounding domain guard.
        target_name = args[0] if args else kwargs.get("target_class")
        if target_name:
            target = instance.factory.createObjectInstance(target_name)
    if not _kind(target, definition) and not _kind(instance, definition):
        return
    status_key = Q(policy.context.iri2qname(definition["statusPropertyIri"]))
    if operation == "transform_class":
        # A transformation can preserve inherited status and role attachments.
        # Reject already public sources, including transitions out of the scope.
        persisted = previous if previous is not None else instance
        old_status = single(persisted, str(status_key))
        if (
            old_status is not None
            and canonical_iri(policy.context, old_status)
            == definition["publishedStatusIri"]
        ) or _public_permission(persisted, policy, definition) is not None:
            raise PublicationConflict(
                "Public resources cannot be transformed through generic CRUD."
            )
        props = kwargs.get("properties") or {}
        for key, val in props.items():
            if canonical_iri(policy.context, key) == definition["statusPropertyIri"]:
                vals = val if isinstance(val, (list, tuple, set)) else [val]
                if any(
                    canonical_iri(policy.context, v) == definition["publishedStatusIri"]
                    for v in vals
                    if v is not None
                ):
                    raise PublicationConflict(
                        "Use the publication command to publish resources."
                    )
        grants = kwargs.get("attached_to_role") or {}
        if any(
            canonical_iri(policy.context, role) == definition["publicRoleIri"]
            for role in grants
        ):
            raise PublicationConflict(
                "Use the publication command to grant public access."
            )
        return
    if operation not in ("create", "update"):
        return
    new_status = single(instance, str(status_key))
    old_status = single(previous, str(status_key)) if previous is not None else None
    published = definition["publishedStatusIri"]
    normalize = lambda value: (
        canonical_iri(policy.context, value) if value is not None else None
    )
    if normalize(new_status) != normalize(old_status) and published in (
        normalize(new_status),
        normalize(old_status),
    ):
        raise PublicationConflict(
            "Use the publication command to change published state."
        )
    new_permission = _public_permission(instance, policy, definition)
    old_permission = (
        _public_permission(previous, policy, definition)
        if previous is not None
        else None
    )
    if operation == "update" and normalize(old_status) == published:
        relation_key = str(
            policy.context.iri2qname(definition["mediaToRootPropertyIri"])
        )
        if set(values(instance, relation_key)) != set(values(previous, relation_key)):
            raise PublicationConflict(
                "Relations of published resources cannot be changed through generic CRUD."
            )
    if new_permission != old_permission:
        raise PublicationConflict(
            "Use the publication command to change public access."
        )


class ArchivePublication(ArchiveRepository):
    """Authorize, review and atomically publish an explicitly requested resource."""

    def _configured(self):
        policy = self._policy()
        if not policy.publication:
            raise OldapErrorNoPermission("Publication is not configured.")
        validate_definition(policy.publication)
        return policy, policy.publication

    def _authorize(self, policy, definition):
        # Fresh membership query: neither token defaults nor creator/admin status
        # substitutes for an explicitly configured publication role.
        roles = " ".join(_iri(role).toRdf for role in definition["publisherRoleIris"])
        query = policy.context.sparql_context + f"""ASK {{ GRAPH oldap:admin {{
            {self._con.userIri.toRdf} oldap:isActive true ; oldap:hasRole ?role .
            VALUES ?role {{ {roles} }}
            ?role a oldap:Role ; oldap:definedByProject {self.project.projectIri.toRdf} .
        }} }}"""
        if not resource_query(self._con, query)["boolean"]:
            raise OldapErrorNoPermission("Publication permission is required.")

    def capabilities(self, resource_iri=None):
        """Return only public feature availability and current role capability."""
        from oldaplib.src.resource_transaction import archive_policy_for

        policy = archive_policy_for(self._con, self.project)
        if policy is None or not policy.enabled or not policy.publication:
            return {"enabled": False, "canPublish": False}
        try:
            self._authorize(policy, policy.publication)
            allowed = True
        except OldapErrorNoPermission:
            allowed = False
        supported = (
            resource_iri is None
            or _kind(self._read(_absolute(resource_iri), policy), policy.publication)
            is not None
        )
        return {
            "enabled": True,
            "canPublish": allowed and supported,
            "statusPropertyName": str(
                policy.context.iri2qname(policy.publication["statusPropertyIri"])
            ),
            "rootClassIris": policy.publication["rootClassIris"],
            "mediaClassIris": policy.publication["mediaClassIris"],
            "statusPropertyIri": policy.publication["statusPropertyIri"],
            "publishedStatusIri": policy.publication["publishedStatusIri"],
        }

    def _read(self, iri, policy):
        instance = self.factory.read(_iri(iri))
        policy.require_data(instance, DP.DATA_VIEW)
        return instance

    def _review(self, iri, permission, policy, definition):
        if permission not in ("DATA_VIEW", "DATA_RESTRICTED"):
            raise OldapErrorValue("Publication accepts only public read permissions.")
        root = self._read(iri, policy)
        kind = _kind(root, definition)
        if kind is None:
            raise OldapErrorValue("Resource class is not configured for publication.")
        resources = {iri: root}
        relation = _iri(definition["mediaToRootPropertyIri"]).toRdf
        graph = f"{self.project.projectShortName}:data"
        if kind == "root":
            query = policy.context.sparql_context + f"""SELECT DISTINCT ?media WHERE {{
                GRAPH {graph} {{ ?media {relation} {_iri(iri).toRdf} }}
            }} LIMIT {definition['maxResources'] + 1}"""
            rows = resource_query(self._con, query)["results"]["bindings"]
            if len(rows) + 1 > definition["maxResources"]:
                raise PublicationConflict(
                    "Publication exceeds the configured resource limit."
                )
            for row in rows:
                media_iri = row["media"]["value"]
                media = self._read(media_iri, policy)
                if _kind(media, definition) != "media":
                    raise PublicationConflict(
                        "A linked resource is not a configured media class."
                    )
                resources[media_iri] = media
        dependencies = {}
        effective = {}
        for resource_iri, instance in resources.items():
            policy.require_data(instance, DP.DATA_UPDATE)
            selected = DP.from_string(permission)
            if _kind(instance, definition) == "media":
                for linked in values(
                    instance,
                    str(policy.context.iri2qname(definition["mediaToRootPropertyIri"])),
                ):
                    linked_iri = canonical_iri(policy.context, linked)
                    if linked_iri in resources:
                        continue
                    if (
                        linked_iri not in dependencies
                        and len(resources) + len(dependencies)
                        >= definition["maxResources"]
                    ):
                        raise PublicationConflict(
                            "Publication dependencies exceed the configured resource limit."
                        )
                    parent = dependencies.get(linked_iri) or self._read(
                        linked_iri, policy
                    )
                    parent_status = single(
                        parent,
                        str(policy.context.iri2qname(definition["statusPropertyIri"])),
                    )
                    if (
                        _kind(parent, definition) != "root"
                        or parent_status is None
                        or canonical_iri(policy.context, parent_status)
                        != definition["publishedStatusIri"]
                    ):
                        raise PublicationConflict("A related entry is not published.")
                    grant = _public_permission(parent, policy, definition)
                    if grant not in (DP.DATA_VIEW, DP.DATA_RESTRICTED):
                        raise PublicationConflict(
                            "A related entry has no supported public read grant."
                        )
                    selected = min(selected, grant)
                    dependencies[linked_iri] = parent
            # Re-publishing must never widen existing access as a side effect.
            old = _public_permission(instance, policy, definition)
            status = single(
                instance, str(policy.context.iri2qname(definition["statusPropertyIri"]))
            )
            if (
                status is not None
                and canonical_iri(policy.context, status)
                == definition["publishedStatusIri"]
            ):
                if old not in (DP.DATA_VIEW, DP.DATA_RESTRICTED):
                    raise PublicationConflict(
                        "Published resource has unsupported public permissions."
                    )
                selected = min(selected, old)
            effective[resource_iri] = selected
        ids = " ".join(
            _iri(item).toRdf for item in sorted(resources.keys() | dependencies.keys())
        )
        # Include ACL annotations, all metadata and dates in the review digest.
        query = (
            policy.context.sparql_context + f"""SELECT ?s ?p ?o ?role ?grant WHERE {{
          GRAPH {graph} {{ VALUES ?s {{ {ids} }} ?s ?p ?o .
          OPTIONAL {{ ?s oldap:attachedToRole ?role . <<?s oldap:attachedToRole ?role>> oldap:hasDataPermission ?grant }} }}
        }}"""
        )
        rows = resource_query(self._con, query)["results"]["bindings"]
        rows.sort(key=lambda row: json.dumps(row, sort_keys=True))
        revision = _digest(
            [
                definition,
                rows,
                sorted((iri, grant.name) for iri, grant in effective.items()),
                permission,
            ]
        )
        status_key = policy.context.iri2qname(definition["statusPropertyIri"])
        if status_key is None:
            raise OldapErrorConfiguration(
                "Publication status namespace is not configured."
            )
        for instance in resources.values():
            if Q(status_key) not in instance.resolved_properties():
                raise OldapErrorConfiguration(
                    "Publication status property is not defined on a target class."
                )
            instance[Q(status_key)] = _iri(definition["publishedStatusIri"])
        return resources, effective, revision

    def preview(self, request):
        """Return a bounded review after checking every affected resource."""
        if not isinstance(request, dict) or set(request) != {
            "resourceIri",
            "permission",
        }:
            raise OldapErrorValue("Expected resourceIri and permission.")
        _iri(request["resourceIri"])
        with resource_transaction(self._con):
            policy, definition = self._configured()
            self._authorize(policy, definition)
            resources, grants, revision = self._review(
                request["resourceIri"], request["permission"], policy, definition
            )
            return {
                "resourceIri": request["resourceIri"],
                "revision": revision,
                "resources": [
                    {"iri": iri, "permission": grant.name}
                    for iri, grant in sorted(grants.items())
                ],
            }

    def apply(self, request, operation_id):
        """Commit exactly the reviewed set and an owner-scoped receipt atomically."""
        operation_id = self._operation_id(operation_id)
        if not isinstance(request, dict) or set(request) != {
            "resourceIri",
            "permission",
            "revision",
        }:
            raise OldapErrorValue("Expected resourceIri, permission and revision.")
        import re

        _iri(request["resourceIri"])
        if not isinstance(request["revision"], str) or not re.fullmatch(
            r"[a-f0-9]{64}", request["revision"]
        ):
            raise OldapErrorValue("Invalid publication revision.")
        fingerprint = _digest(request)
        with resource_transaction(self._con):
            policy, definition = self._configured()
            self._authorize(policy, definition)
            replay = self._receipt(policy, operation_id, command="publication")
            if replay is not None:
                if replay["requestDigest"] != fingerprint:
                    raise PublicationConflict(
                        "Publication operation ID was reused with another request."
                    )
                for iri in replay["result"]["resourceIris"]:
                    self._read(iri, policy)
                return replay["result"]
            resources, grants, revision = self._review(
                request["resourceIri"], request["permission"], policy, definition
            )
            if request["revision"] != revision:
                raise PublicationConflict("Publication review is stale. Review again.")
            context = policy.context.sparql_context
            graph = f"{self.project.projectShortName}:data"
            status = _iri(definition["statusPropertyIri"]).toRdf
            published = _iri(definition["publishedStatusIri"]).toRdf
            public_role = _iri(definition["publicRoleIri"]).toRdf
            from oldaplib.src.xsd.xsd_datetimestamp import Xsd_dateTimeStamp

            timestamp = Xsd_dateTimeStamp().toRdf
            for iri, instance in resources.items():
                subject = _iri(iri).toRdf
                grant = (
                    grants[iri].toRdf
                    if hasattr(grants[iri], "toRdf")
                    else grants[iri].value.toRdf
                )
                query = (
                    context
                    + f"""WITH {graph}
                DELETE {{ {subject} {status} ?oldStatus ; oldap:lastModificationDate ?date ; oldap:lastModifiedBy ?actor .
                  <<{subject} oldap:attachedToRole {public_role}>> oldap:hasDataPermission ?oldGrant . }}
                INSERT {{ {subject} {status} {published} ; oldap:attachedToRole {public_role} ; oldap:lastModificationDate {timestamp} ; oldap:lastModifiedBy {self._con.userIri.toRdf} .
                  <<{subject} oldap:attachedToRole {public_role}>> oldap:hasDataPermission {grant} . }}
                WHERE {{ OPTIONAL {{ {subject} {status} ?oldStatus }} OPTIONAL {{ {subject} oldap:lastModificationDate ?date }} OPTIONAL {{ {subject} oldap:lastModifiedBy ?actor }} OPTIONAL {{ <<{subject} oldap:attachedToRole {public_role}>> oldap:hasDataPermission ?oldGrant }} }}"""
                )
                self._con.transaction_update(query)
            result = {
                "operationId": operation_id,
                "state": "committed",
                "resourceIris": sorted(resources),
            }
            record = {
                "requestDigest": fingerprint,
                "result": result,
                "actor": canonical_iri(policy.context, self._con.userIri),
                "time": datetime.now(timezone.utc).isoformat(),
                "command": "publication",
                "reviewRevision": revision,
            }
            encoded = json.dumps(json.dumps(record, sort_keys=True))
            receipt = self._receipt_iri(policy, operation_id, command="publication")
            self._con.transaction_update(
                f"INSERT DATA {{ GRAPH <{RECEIPT_GRAPH}> {{ <{receipt}> <urn:oldap:archive:record> {encoded} }} }}"
            )
            return result

    def operation(self, operation_id):
        """Return an actor-scoped committed result with fresh authorization."""
        operation_id = self._operation_id(operation_id)
        with resource_transaction(self._con):
            policy, definition = self._configured()
            self._authorize(policy, definition)
            receipt = self._receipt(policy, operation_id, command="publication")
            if receipt is None:
                raise OldapErrorNotFound("Publication operation not found.")
            for iri in receipt["result"]["resourceIris"]:
                self._read(iri, policy)
            return receipt["result"]
