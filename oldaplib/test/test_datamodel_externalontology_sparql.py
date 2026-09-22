"""Regression tests for external ontologies embedded in datamodel creation."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from rdflib.plugins.sparql.parser import parseUpdate
from rdflib import Dataset, Graph, RDF, RDFS, OWL, URIRef

from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.externalontology import ExternalOntology
from oldaplib.src.helpers.context import Context
from oldaplib.src.iconnection import IConnection
from oldaplib.src.project import Project
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_qname import Xsd_QName


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

    def test_propertyless_class_fragments_are_complete_statements(self) -> None:
        """Adjacent class fragments must parse without depending on properties."""
        connection = _RecordingConnection()
        context = Context(name=connection.context_name)
        data = context.turtle_context
        for name in ("schema:NewsArticle", "schema:Place"):
            # Rendering needs only these fields; no live Project lookup is needed.
            resource = SimpleNamespace(_owlclass_iri=Xsd_QName(name), _attributes={}, _properties={})
            data += ResourceClass.create_owl(resource, timestamp=Xsd_dateTime.now())
        graph = Graph().parse(data=data, format="turtle")
        for name in ("NewsArticle", "Place"):
            iri = URIRef(str(context['schema']) + name)
            self.assertIn((iri, RDF.type, OWL.Class), graph)
            self.assertIn((iri, RDFS.subClassOf, URIRef("http://oldap.org/base#Thing")), graph)

    def test_trig_exports_embed_external_ontologies_without_update_wrappers(self) -> None:
        """String/API and file exports must both parse as named RDF graphs."""
        connection = _RecordingConnection()
        project = Project(con=connection, projectIri="https://example.org/project",
                          projectShortName="example", namespaceIri=NamespaceIRI("https://example.org/ns/"),
                          projectStart=Xsd_date("2026-01-01"))
        ontologies = [ExternalOntology(con=connection, projectShortName="example", prefix=prefix,
                                      namespaceIri=NamespaceIRI(f"https://{prefix}.example/ns/"),
                                      label=[f"{prefix}@en"])
                      for prefix in ("external", "other")]
        model = DataModel(con=connection, project=project, extontos=ontologies)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "model.trig"
            model.write_as_trig(str(path), indent=1, indent_inc=2)
            for data in (model.write_as_str(), path.read_text()):
                self.assertNotIn("INSERT DATA", data)
                dataset = Dataset().parse(data=data, format="trig")
                self.assertIn((URIRef("https://example.org/ns/ontology"), RDF.type, OWL.Ontology),
                              dataset.graph(URIRef("https://example.org/ns/onto")))
                graph = dataset.graph(URIRef("https://example.org/ns/shacl"))
                for prefix in ("external", "other"):
                    self.assertIn((URIRef(f"https://example.org/ns/{prefix}"), RDF.type,
                                   URIRef("http://oldap.org/base#ExternalOntology")), graph)
        self.assertEqual(connection.updates, [])

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
