"""Offline connector safety and lossless-configuration regressions."""
import copy
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from rdflib.plugins.sparql.parser import parseUpdate
from oldaplib.src.lucene_connector import ProjectLuceneConnector, configuration_revision
from oldaplib.src.helpers.oldaperror import OldapErrorAlreadyExists, OldapErrorNoPermission, OldapErrorUpdateFailed, OldapErrorValue
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.xsd.iri import Iri

CONFIG = {"types": ["https://example.org/Book"], "fields": [{"fieldName": "title", "propertyChain": ["https://example.org/title"], "valueFilter": "?value != \"x\""}], "customOption": {"nested": "retained"}}


def service(current=None):
    connector = object.__new__(ProjectLuceneConnector)
    connector.name = "demo"
    connector.con = Mock()
    connector.read = Mock(return_value=copy.deepcopy(current))
    return connector


@pytest.fixture(autouse=True)
def no_gate():
    with patch("oldaplib.src.lucene_connector.archive_coordination_enabled", return_value=False):
        yield


def test_create_preserves_options_and_escapes_literal():
    connector = service()
    payload = copy.deepcopy(CONFIG)
    payload["customOption"] = 'quotes: \'"\\\n and """'
    assert connector.apply(payload) == "created"
    query = connector.con.update_query.call_args.args[0]
    parseUpdate(query)
    assert "customOption" in query and "valueFilter" in query


@pytest.mark.parametrize("mode,revision", [("create", None), ("replace", "stale")])
def test_conflict_never_drops(mode, revision):
    connector = service(CONFIG)
    with pytest.raises(OldapErrorAlreadyExists):
        connector.apply(CONFIG, mode=mode, expected_revision=revision)
    connector.con.update_query.assert_not_called()


def test_matching_replace_does_not_rebuild():
    connector = service(CONFIG)
    assert connector.apply(CONFIG, mode="replace", expected_revision=configuration_revision(CONFIG)) == "unchanged"
    connector.con.update_query.assert_not_called()


def test_invalid_configuration_never_drops():
    connector = service(CONFIG)
    with pytest.raises(OldapErrorValue):
        connector.apply({"types": []}, mode="replace", expected_revision=configuration_revision(CONFIG))
    connector.con.update_query.assert_not_called()


def test_failed_replace_restores_previous_configuration():
    connector = service()
    connector.read.side_effect = [CONFIG, None, CONFIG]
    connector.con.update_query.side_effect = [None, RuntimeError("creation failed"), None]
    desired = dict(CONFIG, languages=["de"])
    with pytest.raises(OldapErrorUpdateFailed, match="Previous configuration restored"):
        connector.apply(desired, mode="replace", expected_revision=configuration_revision(CONFIG))
    assert connector.con.update_query.call_count == 3
    assert "languages" not in connector.con.update_query.call_args.args[0]


def test_ambiguous_replace_never_overwrites_observed_connector():
    connector = service()
    connector.read.side_effect = [CONFIG, dict(CONFIG, languages=["fr"])]
    connector.con.update_query.side_effect = [None, RuntimeError("timeout")]
    with pytest.raises(OldapErrorUpdateFailed, match="could not be confirmed"):
        connector.apply(dict(CONFIG, languages=["de"]), mode="replace", expected_revision=configuration_revision(CONFIG))
    assert connector.con.update_query.call_count == 2


def test_project_permission_boundary():
    project = SimpleNamespace(projectIri=Iri("https://example.org/demo"), projectShortName="demo")
    con = Mock(userdata=SimpleNamespace(inProject={}))
    with patch("oldaplib.src.lucene_connector.Project.read", return_value=project):
        with pytest.raises(OldapErrorNoPermission):
            ProjectLuceneConnector(con, "demo")
        con.query.assert_not_called()
        con.userdata.inProject[project.projectIri] = {AdminPermission.ADMIN_MODEL}
        assert ProjectLuceneConnector(con, "demo").name == "demo"


def test_read_matches_instance_iri_and_retains_unknown_options():
    connector = service()
    del connector.read
    connector.con.query.side_effect = [{"boolean": True}, {"results": {"bindings": [{"options": {"value": json.dumps(CONFIG)}}]}}]
    assert connector.read() == CONFIG
    assert "inst:demo luc:listConnectors ?name" in connector.con.query.call_args_list[0].args[0]


def test_unavailable_writer_gate_prevents_reads_and_commands():
    from oldaplib.src.mutation_gate import MutationGateUnavailable
    connector = service(CONFIG)
    with patch("oldaplib.src.lucene_connector.archive_coordination_enabled", return_value=True), patch(
        "oldaplib.src.lucene_connector.mutation_gate", side_effect=MutationGateUnavailable("busy")
    ):
        with pytest.raises(MutationGateUnavailable):
            connector.apply(CONFIG, mode="replace", expected_revision=configuration_revision(CONFIG))
    connector.read.assert_not_called()
    connector.con.update_query.assert_not_called()
