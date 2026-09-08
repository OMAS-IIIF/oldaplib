"""Retain private membership and organisation read access during cataloguing.

These hooks execute only inside ResourceInstance's owned transaction and writer
 gate. Automatic retention is not a folder relocation: source folder VIEW and
 the existing medium transformation permission suffice, including Mobile inboxes.
"""

from dataclasses import dataclass
import json
from uuid import uuid4

from oldaplib.src.archive_domain import (
    AREA,
    FOLDER_PARENT,
    REFERENCE,
    is_a,
    single,
    values,
    audit_resource_operation,
)
from oldaplib.src.archive_policy import ArchiveConflict, canonical_iri
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.oldaperror import OldapErrorConfiguration
from oldaplib.src.staging_folder_tree import StagingFolderTree
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_datetimestamp import Xsd_dateTimeStamp


@dataclass
class ArchiveTransfer:
    """Validated source placement, retained until the transformation commits."""

    folder: object
    source: object

    @classmethod
    def prepare(cls, instance, args, kwargs, policy):
        """Validate current placement and derive archive-safe target grants.

        Explicit caller grants remain subject to policy validation; omitted
        grants retain existing readers while capping non-editorial writes at VIEW.
        The area's authoritative default role retains VIEW without gaining writes.
        Returns None for transformations outside the opt-in staging lifecycle.
        """
        if not is_a(instance, "shared:StagingMediaObject"):
            return None
        target = instance.factory.createObjectInstance(
            args[0] if args else kwargs["target_class"]
        )
        if not policy.is_catalogued(target):
            return None  # The ordinary guard rejects invalid lifecycle targets.
        if canonical_iri(policy.context, kwargs.get("preserve_class")) != canonical_iri(
            policy.context, "shared:MediaObject"
        ):
            raise ArchiveConflict(
                "Cataloguing must preserve shared:MediaObject and its binary identity."
            )
        source = instance.factory.read(instance.iri)
        if not is_a(source, "shared:StagingMediaObject"):
            raise ArchiveConflict("The medium was already catalogued; reload it.")
        folder_iri, area_iri = single(source, FOLDER_PARENT), single(source, AREA)
        if folder_iri is None or area_iri is None:
            raise ArchiveConflict(
                "Cataloguing requires a current private folder and area."
            )
        folder = instance.factory.read(folder_iri)
        area = instance.factory.read(area_iri)
        if not is_a(folder, "shared:StagingFolder") or not is_a(
            area, "shared:StagingArea"
        ):
            raise ArchiveConflict("The source placement is invalid.")
        if canonical_iri(policy.context, single(folder, AREA)) != canonical_iri(
            policy.context, area_iri
        ):
            raise ArchiveConflict("The source folder belongs to another area.")
        policy.require_data(folder, DataPermission.DATA_VIEW)
        policy.require_data(area, DataPermission.DATA_VIEW)
        policy.require_data(source, DataPermission.DATA_DELETE)
        tree = StagingFolderTree(policy.connection, policy.project)
        if any(
            tree._portable_name_key(tree._name(node)) == "trash"
            for node in tree.path_to_root(folder.iri)
        ):
            raise ArchiveConflict("Restore media from Trash before cataloguing.")
        default_role = single(area, "shared:stagingDefaultRole")
        if default_role is None:
            raise OldapErrorConfiguration("The private area requires one default role.")
        default_role = canonical_iri(policy.context, default_role)
        # A private organisation must be represented by a project-owned role,
        # never by the global public/Unknown role.
        query = policy.context.sparql_context + f"""ASK {{ GRAPH oldap:admin {{
          <{default_role}> a oldap:Role ; oldap:definedByProject {policy.project.projectIri.toRdf} .
        }} }}"""
        if not policy.connection.transaction_query(query)["boolean"]:
            raise OldapErrorConfiguration(
                "The private area's default role must belong to this project."
            )
        original = {
            canonical_iri(policy.context, r): p
            for r, p in source.attachedToRoleAnnotation.items()
        }
        supplied = kwargs.get("attached_to_role")
        if supplied is not None:
            grants = {
                canonical_iri(policy.context, r): (
                    p
                    if isinstance(p, DataPermission)
                    else DataPermission.from_string(p)
                )
                for r, p in supplied.items()
            }
            policy.validate_archive_grants(grants)
        else:
            grants = {
                r: (
                    p
                    if r in policy.editorial_roles
                    else min(p, DataPermission.DATA_VIEW)
                )
                for r, p in original.items()
            }
        for role, permission in original.items():
            retained = min(permission, DataPermission.DATA_VIEW)
            if role not in grants or grants[role] < retained:
                grants[role] = retained
        if (
            default_role not in grants
            or grants[default_role] < DataPermission.DATA_VIEW
        ):
            grants[default_role] = DataPermission.DATA_VIEW
        kwargs["attached_to_role"] = {
            policy.context.iri2qname(r) or Iri(Xsd_anyURI(r)): p
            for r, p in grants.items()
        }
        return cls(folder, source)

    def finish(self, result, policy):
        """Append the retained reference and transfer audit in the same transaction.

        A narrow internal RDF append preserves unrelated folder edges and does not
        require weakening protected Mobile ACLs. Any failure rolls back the medium,
        archive attachment, reference, grants and audits together.
        """
        if values(result, FOLDER_PARENT) or values(result, AREA):
            raise ArchiveConflict(
                "Catalogued media must not retain staging placement properties."
            )
        timestamp = Xsd_dateTimeStamp()
        folder = Iri(Xsd_anyURI(canonical_iri(policy.context, self.folder.iri))).toRdf
        medium = Iri(Xsd_anyURI(canonical_iri(policy.context, result.iri))).toRdf
        policy.connection.transaction_update(
            policy.context.sparql_context
            + f"""WITH {policy.project.projectShortName}:data
        DELETE {{ {folder} oldap:lastModificationDate ?date ; oldap:lastModifiedBy ?actor }}
        INSERT {{ {folder} shared:referencedMediaObject {medium} ;
            oldap:lastModificationDate {timestamp.toRdf} ; oldap:lastModifiedBy {policy.connection.userIri.toRdf} }}
        WHERE {{ OPTIONAL {{ {folder} oldap:lastModificationDate ?date }}
                OPTIONAL {{ {folder} oldap:lastModifiedBy ?actor }} }}"""
        )
        current = result.factory.read(self.folder.iri)
        audit_resource_operation(
            current, self.folder, "retain-catalogue-reference", policy
        )
        record = {
            "operation": "catalogue-transfer",
            "actor": canonical_iri(policy.context, policy.connection.userIri),
            "project": str(policy.project.projectShortName),
            "time": str(timestamp),
            "mediaIri": canonical_iri(policy.context, result.iri),
            "sourceFolderIri": canonical_iri(policy.context, self.folder.iri),
            "sourceClass": str(self.source.name),
            "targetClass": str(result.name),
        }
        payload = json.dumps(json.dumps(record, sort_keys=True, separators=(",", ":")))
        policy.connection.transaction_update(
            f"""INSERT DATA {{ GRAPH <urn:oldap:archive-operations> {{
            <urn:oldap:archive:audit:{uuid4()}> <urn:oldap:archive:record> {payload} . }} }}"""
        )
