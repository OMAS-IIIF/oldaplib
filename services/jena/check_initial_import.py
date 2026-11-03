"""Exercise the packaged offline importer on owned temporary TDB2 directories.

Checks persisted grants/cross-graph blank nodes, timestamp spelling, and refusal
without activation for wrong checksums, legacy syntax and protected receipts.
No live database, service configuration or account is accessed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def run(java: Path, release: Path) -> None:
    """Run the actual built command and fail if any import contract is violated."""
    with tempfile.TemporaryDirectory(prefix='oldap-initial-import-') as temp:
        root = Path(temp)
        fixture = '''PREFIX oldap: <http://oldap.org/base#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
oldap:admin {
 <urn:test:user> oldap:userId "tester" ; oldap:credentials "synthetic-hash" ;
   oldap:inProject <urn:test:project> .
 <urn:test:grant> rdf:reifies <<( <urn:test:user> oldap:inProject <urn:test:project> )>> ;
   oldap:hasAdminPermission oldap:ADMIN_USERS .
 _:shared oldap:creationDate "2026-10-26T20:45:47.342000+00:00"^^xsd:dateTimeStamp .
}
<urn:test:data> { <urn:test:thing> <urn:test:link> _:shared }
'''

        def invoke(name, text, *, digest=None, target=None, success=False):
            source = root / (name + '.trig')
            source.write_text(text)
            target = target or root / name
            result = subprocess.run([str(java), '-cp', str(release / 'lib/*'),
                'JenaInitialImport', str(source), digest or hashlib.sha256(source.read_bytes()).hexdigest(),
                str(target)], capture_output=True, timeout=60)
            if (result.returncode == 0) != success:
                raise AssertionError(f'{name}: unexpected import outcome\n{result.stderr.decode()}')
            return target

        target = invoke('valid', fixture, success=True)
        report_bytes = (target / 'initial-import.json').read_bytes()
        report = json.loads(report_bytes)
        assert report['persistedDatasetVerified'] and len(report['graphs']) == 2
        assert (target / 'oldap-service-format').read_text() == 'oldap-jena-service-1\n'
        invoke('existing', fixture, target=target)
        assert (target / 'initial-import.json').read_bytes() == report_bytes
        refused = [
            invoke('checksum', fixture, digest='0' * 64),
            invoke('legacy', '<urn:g> { << <urn:s> <urn:p> <urn:o> >> <urn:q> <urn:r> }'),
            invoke('sidechannel', '#>> account\n' + fixture),
            invoke('receipts', '<urn:probe:http-commits> { <urn:s> <urn:p> <urn:o> }'),
            invoke('malformed', '<urn:g> {'),
        ]
        assert all(not path.exists() for path in refused)
        # A different lexical normalization must not accidentally pass our narrow
        # timestamp allowance. TDB2 normalizes boolean 1 to true.
        failed = invoke('boolean-spelling', '<urn:g> { <urn:s> <urn:p> '
                        '"1"^^<http://www.w3.org/2001/XMLSchema#boolean> }')
        assert failed.exists() and not (failed / 'oldap-service-format').exists()
        print('PASS: persisted RDF, real grant structure, shared blank nodes, timestamp spelling; '
              'existing target, checksum, legacy syntax, side-channel, receipts, malformed RDF, '
              'unapproved normalization refusal')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', type=Path, required=True)
    parser.add_argument('--release', type=Path, required=True)
    args = parser.parse_args()
    run(args.java.resolve(), args.release.resolve())
