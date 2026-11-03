"""Exercise offline conversion files, gzip, bounds and failure publication.

Usage: python probe_legacy_conversion_cli.py --java /path/java --jar /path/jar
No network calls, credentials or shared database/cache access are involved.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def run(java: str, jar: str) -> None:
    """Run the real converter with private temporary files and verify its artifacts."""
    root = Path(__file__).resolve().parents[2]
    source = b'''@prefix p: <https://example.org/p/> .
@prefix oldap: <http://oldap.org/base#> .
p:data { p:item oldap:attachedToRole p:Reader .
<< p:item oldap:attachedToRole p:Reader >> oldap:hasDataPermission oldap:DATA_VIEW . }
'''
    checks = 0
    with tempfile.TemporaryDirectory(prefix='oldap-conversion-') as directory:
        temp = Path(directory)
        def invoke(path, output, *, success):
            result = subprocess.run([java, '--class-path', jar, 'tools/migration/ConvertLegacyRdfStar.java',
                                     str(path), str(output)], cwd=root, capture_output=True, text=True, timeout=60)
            assert (result.returncode == 0) == success, result.stderr
        plain, zipped = temp / 'source.trig', temp / 'source.trig.gz'
        plain.write_bytes(source)
        zipped.write_bytes(gzip.compress(source))
        for path in (plain, zipped):
            out = temp / (path.name + '-result')
            invoke(path, out, success=True)
            report = json.loads((out / 'report.json').read_text())
            assert report['sourceTextSha256'] == hashlib.sha256(source).hexdigest()
            assert report['outputSha256'] == hashlib.sha256((out / 'converted.trig').read_bytes()).hexdigest()
            assert report['roundTripVerified'] and report['membershipReifiers'] == 1
            assert report['orphanedMembershipReifiers'] == report['assertedMembershipsAdded'] == 0
            assert out.stat().st_mode & 0o777 == 0o700
            checks += 1
            print('PASS real CLI validates ' + path.suffix + ' conversion, hashes and private output')
        original = (temp / 'source.trig-result/converted.trig').read_bytes()
        invoke(plain, temp / 'source.trig-result', success=False)
        assert (temp / 'source.trig-result/converted.trig').read_bytes() == original
        checks += 1
        print('PASS existing output is never overwritten')
        for name, payload in [('bad.trig', b'BROKEN'), ('encoding.trig', b'\xff'),
                              ('large.trig.gz', gzip.compress(b' ' * (16 * 1024 * 1024 + 1))),
                              ('users.trig', b'#>> {"userId":"fixture"}\n')]:
            path, out = temp / name, temp / (name + '-result')
            path.write_bytes(payload)
            invoke(path, out, success=False)
            assert not out.exists()
            checks += 1
            print('PASS invalid input leaves no partial output: ' + name)
        assert plain.read_bytes() == source and gzip.decompress(zipped.read_bytes()) == source
        checks += 1
        print('PASS original input files remain unchanged')
    print(f'PASS total={checks}; temporary CLI files removed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', required=True)
    parser.add_argument('--jar', required=True)
    args = parser.parse_args()
    run(args.java, args.jar)
