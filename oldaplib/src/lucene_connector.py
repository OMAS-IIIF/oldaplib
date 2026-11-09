"""Permission-checked management of the Lucene connector named for a project.

GraphDB connector commands affect index files and are not RDF transactions.
Replacement validates first, checks the reviewed revision, and attempts to
restore the previous configuration if creation fails. Concurrent connector
administrators must still serialize operations externally.
"""

from contextlib import nullcontext
import hashlib
import json
from typing import Any

from rdflib import Literal

from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.mutation_gate import archive_coordination_enabled, mutation_gate
from oldaplib.src.helpers.oldaperror import (
    OldapError, OldapErrorAlreadyExists, OldapErrorNoPermission,
    OldapErrorUpdateFailed, OldapErrorValue,
)
from oldaplib.src.iconnection import IConnection
from oldaplib.src.project import Project
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


_PREFIXES = """PREFIX luc: <http://www.ontotext.com/connectors/lucene#>
PREFIX inst: <http://www.ontotext.com/connectors/lucene/instance#>
"""


def configuration_revision(configuration: dict | None) -> str | None:
    """Return a stable revision of the complete JSON configuration, or absence."""
    if configuration is None:
        return None
    raw = json.dumps(configuration, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_configuration(configuration: Any) -> dict:
    """Validate transport structure while preserving all GraphDB creation options.

    GraphDB remains authoritative for analyzers, filters and advanced settings.
    This validation is completed before any destructive connector command.
    """
    if not isinstance(configuration, dict):
        raise OldapErrorValue("Lucene configuration must be a JSON object.")
    try:
        result = json.loads(json.dumps(configuration, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise OldapErrorValue("Lucene configuration must contain valid JSON values.") from error
    types = result.get("types")
    fields = result.get("fields")
    if not isinstance(types, list) or not types or not all(isinstance(item, str) and item for item in types):
        raise OldapErrorValue("Lucene configuration needs a nonempty types array.")
    if fields is None and result.get("detectFields") is True:
        fields = []
    if not isinstance(fields, list) or (not fields and result.get("detectFields") is not True):
        raise OldapErrorValue("Lucene configuration needs a nonempty fields array.")
    names = set()
    for field in fields:
        if not isinstance(field, dict) or not isinstance(field.get("fieldName"), str) or not field["fieldName"]:
            raise OldapErrorValue("Every Lucene field needs a fieldName.")
        if field["fieldName"] in names:
            raise OldapErrorValue("Lucene field names must be unique.")
        names.add(field["fieldName"])
        chain = field.get("propertyChain")
        if not isinstance(chain, list) or not chain or not all(isinstance(item, str) and item for item in chain):
            raise OldapErrorValue("Every Lucene field needs a nonempty propertyChain.")
    return result


class ProjectLuceneConnector:
    """Manage exactly one project's connector under ADMIN_MODEL/ADMIN_OLDAP.

    Args:
        con: Authenticated OLDAP connection, used for GraphDB queries/commands.
        project: Existing project object or short name/IRI.

    Neither callers nor configuration payloads can select another connector name.
    Read operations also require model administration because configurations can
    include internal filters and repository details.
    """

    def __init__(self, con: IConnection, project: Project | str):
        self.con = con
        self.project = project if isinstance(project, Project) else Project.read(con, project)
        permissions = con.userdata.inProject
        root = permissions.get(Iri("oldap:SystemProject")) or ()
        local = permissions.get(self.project.projectIri) or ()
        if AdminPermission.ADMIN_OLDAP not in root and AdminPermission.ADMIN_MODEL not in local:
            raise OldapErrorNoPermission("Lucene administration requires ADMIN_MODEL for this project.")
        self.name = str(Xsd_NCName(str(self.project.projectShortName), validate=True))

    def read(self) -> dict | None:
        """Read all stored creation options; distinguish absence from a broken export."""
        # Match the instance IRI, not the display string returned by listConnectors.
        exists = self.con.query(_PREFIXES + f"ASK {{ inst:{self.name} luc:listConnectors ?name . }}")
        if not isinstance(exists.get("boolean"), bool):
            raise OldapError("Invalid Lucene connector existence response.")
        if not exists["boolean"]:
            return None
        response = self.con.query(_PREFIXES + f"SELECT ?options WHERE {{ inst:{self.name} luc:listOptionValues ?options . }}")
        bindings = response.get("results", {}).get("bindings", [])
        if len(bindings) != 1:
            raise OldapError("Existing Lucene connector returned no unique configuration.")
        try:
            options = json.loads(bindings[0]["options"]["value"])
            if not isinstance(options, dict):
                raise ValueError("Expected object")
            configuration_revision(options)
        except (KeyError, TypeError, ValueError) as error:
            raise OldapError("Existing Lucene connector returned invalid JSON configuration.") from error
        return options

    def _create(self, configuration: dict) -> None:
        """Issue one creation command with JSON safely encoded as an RDF literal."""
        literal = Literal(json.dumps(configuration, ensure_ascii=False, allow_nan=False)).n3()
        self.con.update_query(_PREFIXES + f"INSERT DATA {{ inst:{self.name} luc:createConnector {literal} . }}")

    def _drop(self) -> None:
        self.con.update_query(_PREFIXES + f"INSERT DATA {{ inst:{self.name} luc:dropConnector [] . }}")

    def apply(self, configuration: dict, *, mode: str = "create", expected_revision: str | None = None) -> str:
        """Create or replace the project connector; return created/replaced/unchanged.

        Replacement requires the revision returned by read (None for absence).
        Existing matching configurations do not rebuild the index in replace mode.
        On creation failure after deletion, restore the previous configuration if
        no connector now exists. Ambiguous outcomes are never overwritten blindly.
        """
        with mutation_gate() if archive_coordination_enabled() else nullcontext():
            return self._apply(configuration, mode=mode, expected_revision=expected_revision)

    def _apply(self, configuration: dict, *, mode: str, expected_revision: str | None) -> str:
        """Run the complete read/check/replace under the deployment writer gate."""
        if mode not in {"create", "replace"}:
            raise OldapErrorValue("Connector mode must be create or replace.")
        desired = validate_configuration(configuration)
        current = self.read()
        if mode == "create" and current is not None:
            raise OldapErrorAlreadyExists(f'Lucene connector "{self.name}" already exists.')
        if mode == "replace" and configuration_revision(current) != expected_revision:
            raise OldapErrorAlreadyExists("Lucene connector changed since preview; read it again before replacement.")
        if current is not None and configuration_revision(current) == configuration_revision(desired):
            return "unchanged"
        if current is not None:
            self._drop()
        try:
            self._create(desired)
        except Exception as error:
            if current is None:
                raise OldapErrorUpdateFailed("Lucene creation failed; inspect connector state before retrying.") from error
            try:
                observed = self.read()
                if observed is None:
                    self._create(current)
                    observed = self.read()
                restored = configuration_revision(observed) == configuration_revision(current)
            except Exception:
                restored = False
            status = "Previous configuration restored; index may still be rebuilding." if restored else "Restoration could not be confirmed; inspect connector state before retrying."
            raise OldapErrorUpdateFailed(f"Lucene replacement failed. {status}") from error
        return "replaced" if current is not None else "created"
