"""Regression tests for external ontologies embedded in datamodel creation."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from rdflib.plugins.sparql.parser import parseUpdate

from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.externalontology import ExternalOntology
from oldaplib.src.helpers.context import Context
from oldaplib.src.iconnection import IConnection
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime


class _RecordingConnection(IConnection):
    """Minimal connection that validates generated updates without GraphDB."""

    def __init__(self) -> None:
        super().__init__("DATAMODEL_EXTERNAL_ONTOLOGY_TEST")
        self._userdata = SimpleNamespace(
            userIri=Iri("urn:uuid:00000000-0000-0000-0000-000000000001"),
            userId="tester",
            inProject={Iri("oldap:SystemProject"): {AdminPermission.ADMIN_OLDAP}},
        )
        self.updates: list[str] = []

    def issue_media_token(self, claims):
        raise NotImplementedError

    def clear_graph(self, graph_iri):
        raise NotImplementedError

    def clear_repo(self):
        raise NotImplementedError

    def upload_turtle(self, filename, graphname=None):
        raise NotImplementedError

    def query(self, query, format=None):
        return {"boolean": False}

    def update_query(self, query):
        raise NotImplementedError

    def transaction_start(self):
        self._transaction_url = "recording://transaction"

    def transaction_query(self, query, result_format=None):
        raise NotImplementedError

    def transaction_update(self, query):
        parseUpdate(query)
        self.updates.append(query)

    def transaction_commit(self):
        self._transaction_url = None

    def transaction_abort(self):
        self._transaction_url = None

    def in_transaction(self):
        return self._transaction_url is not None


class TestDataModelExternalOntologySparql(unittest.TestCase):
    """Verify that a combined datamodel update contains no nested update."""

    def test_create_embeds_external_ontology_as_triples(self) -> None:
        connection = _RecordingConnection()
        project = Project(
            con=connection,
            projectIri="https://example.org/project",
            projectShortName="example",
            namespaceIri=NamespaceIRI("https://example.org/ns/"),
            projectStart=Xsd_date("2026-01-01"),
        )
        external_ontology = ExternalOntology(
            con=connection,
            projectShortName="example",
            prefix="external",
            namespaceIri=NamespaceIRI("https://external.example/ns/"),
        )
        datamodel = DataModel(
            con=connection,
            project=project,
            extontos=[external_ontology],
        )

        standalone_update = (
            Context(name=connection.context_name).sparql_context
            + external_ontology.create_shacl(timestamp=Xsd_dateTime.now())
        )
        parseUpdate(standalone_update)
        self.assertEqual(standalone_update.count("INSERT DATA"), 1)

        with patch("oldaplib.src.datamodel.CacheSingletonRedis"):
            datamodel.create()

        self.assertEqual(len(connection.updates), 1)
        update = connection.updates[0]
        self.assertEqual(update.count("INSERT DATA"), 1)
        self.assertIn("example:external a oldap:ExternalOntology", update)


if __name__ == "__main__":
    unittest.main()
