"""Exercise shape CRUD and instance barriers using real isolated Jena TDB2.

The JSON-line subprocess is a diagnostic connection, not a service transport.
Use a complete project virtualenv. No HTTP service or live Redis is contacted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from rdflib import Graph

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from oldaplib.test.test_datamodel_externalontology_sparql import _RecordingConnection
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorNotFound
from oldaplib.src.helpers.reification import guard_instance_write
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.reifier_shape import ReifierShape
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_qname import Xsd_QName


class NativeConnection(_RecordingConnection):
    """Minimal test connection forwarding real query/update text to Jena."""
    def __init__(self, process):
        super().__init__()
        self.process = process

    def send(self, operation, **payload):
        self.process.stdin.write(json.dumps({'operation': operation, **payload}) + '\n')
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('Native probe exited; inspect stderr.')
        return json.loads(line)

    def query(self, query, format=None):
        result = self.send('query', query=query)
        return Graph().parse(data=result['result'], format='turtle') if result.get('format') else json.loads(result['result'])

    def transaction_query(self, query, result_format=None):
        return self.query(query, result_format)

    def transaction_update(self, query):
        self.send('update', query=query)

    def transaction_start(self):
        self.send('begin')
        super().transaction_start()

    def transaction_commit(self):
        self.send('commit')
        super().transaction_commit()

    def transaction_abort(self):
        self.send('abort')
        super().transaction_abort()


def run(java_home, fuseki_jar, output):
    """Run on newly owned storage, preserving a compact successful-check report."""
    digest = hashlib.sha256(fuseki_jar.read_bytes()).hexdigest()
    if digest != '2c92c598e65ab69d99820052e05f4277ed1d77980a8845f87545ad35b71a76ee':
        raise ValueError('Expected pinned Fuseki 6.2.0 dependency')
    output.mkdir(parents=True, exist_ok=False)
    subprocess.run([str(java_home / 'bin/javac'), '-cp', str(fuseki_jar), '-d', str(output),
                    str(ROOT / 'tools/reification/JenaModelProbe.java')], check=True)
    process = subprocess.Popen([str(java_home / 'bin/java'), '-cp', str(output) + ':' + str(fuseki_jar),
        'JenaModelProbe', str(output / 'tdb')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    checks = []
    try:
        con = NativeConnection(process)
        project = Project(con=con, projectIri='https://example.org/project', projectShortName='example',
            namespaceIri=NamespaceIRI('https://example.org/ns/'), projectStart=Xsd_date('2026-01-01'))
        field = PropertyClass(con=con, project=project, property_class_iri='example:dateTime',
            datatype=XsdDatatypes.dateTime, minCount=1, maxCount=1)
        shape = ReifierShape(con=con, project=project, shape_iri='example:VisitShape', properties=[field])
        with patch('oldaplib.src.resource_transaction.archive_coordination_enabled', return_value=False), patch('oldaplib.src.cachesingleton.CacheSingletonRedis'):
            shape.create()
            loaded = ReifierShape.read(con, project, shape.shape_iri)
            assert loaded['example:dateTime'].maxCount == 1
            checks.append('Native library create/read')
            loaded['example:dateTime'].maxCount = 2
            loaded.update()
            assert ReifierShape.read(con, project, shape.shape_iri)['example:dateTime'].maxCount == 2
            checks.append('Native library update/read')
            loaded.delete()
            try:
                ReifierShape.read(con, project, shape.shape_iri)
            except OldapErrorNotFound:
                checks.append('Native library delete/read')
            else:
                raise AssertionError('Deleted shape still present')
        context = Context(name=con.context_name)
        context['ex'] = NamespaceIRI('https://example.org/reification/')
        con.transaction_start()
        con.send('load', path=str(ROOT / 'oldaplib/testdata/reification/travel.trig'))
        def instance(name, iri):
            return SimpleNamespace(_con=con, name=Xsd_QName(name), iri=Iri(iri), _graph='ex')
        trip = instance('ex:Travel', 'ex:T')
        house = instance('ex:Building', 'ex:House')
        try:
            guard_instance_write(trip, 'update', (), {})
        except OldapErrorValue:
            checks.append('Native model policy blocks instance mutation')
        else:
            raise AssertionError('Annotated model bypassed barrier')
        guard_instance_write(house, 'update', (), {})
        checks.append('Different use of isAt remains writable')
        con.transaction_update(context.sparql_context + '''DELETE WHERE { GRAPH ex:shacl {
            ?use sh:reifierShape ?shape }}; DELETE WHERE { GRAPH ex:shacl {
            ?use sh:reificationRequired ?required }}''')
        try:
            guard_instance_write(trip, 'delete', (), {})
        except OldapErrorValue:
            checks.append('Existing business reifiers block deletion without model links')
        else:
            raise AssertionError('Existing annotations bypassed barrier')
        con.transaction_update(context.sparql_context + '''INSERT DATA { GRAPH ex:data {
            ex:House oldap:attachedToRole ex:Reader .
            ex:grant rdf:reifies <<( ex:House oldap:attachedToRole ex:Reader )>> ;
                oldap:hasDataPermission oldap:DATA_VIEW . }}''')
        guard_instance_write(house, 'update', (), {})
        checks.append('Protected permission reifiers do not trigger business barrier')
        con.transaction_abort()
        sources = ['oldaplib/src/reifier_shape.py', 'oldaplib/src/helpers/reification.py',
                   'tools/reification/JenaModelProbe.java', 'tools/reification/probe_model.py']
        report = {'checks': checks, 'fusekiSha256': digest,
            'sourceSha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources},
            'scope': 'Isolated TDB2; real library CRUD and generated barrier queries; no HTTP or Redis'}
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        process.stdout.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--fuseki-jar', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.java_home.resolve(), args.fuseki_jar.resolve(), args.output.resolve())
