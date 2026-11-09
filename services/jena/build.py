"""Build an offline, versioned private backend from a pinned Fuseki distribution.

Uses the shared migration engine/servlet sources without copying implementations.
The diagnostic probe and fault-injection subclass are excluded from the artifact.
Requires JDK 25. Output must not exist; dependency/source hashes accompany the jar.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

FUSEKI_SHA256 = '2c92c598e65ab69d99820052e05f4277ed1d77980a8845f87545ad35b71a76ee'
VERSION = '1.0.1'
SHARED = ('JenaSessionEngine', 'JenaSessionServlet', 'ProtectedApplicationDataset',
          'JenaManagedText', 'JenaProjectTransfer', 'OldapTextAnalyzer', 'JenaTextFixture')


def build(java_home, fuseki_home, output):
    """Compile the explicit source set and retain a self-contained distribution.

    JenaTextFixture is a compile dependency of the legacy engine constructor;
    the service always explicitly selects managed mode, never fixture mode.
    """
    root = Path(__file__).resolve().parents[2]
    dependency = fuseki_home / 'fuseki-server.jar'
    digest = hashlib.sha256(dependency.read_bytes()).hexdigest()
    if digest != FUSEKI_SHA256:
        raise ValueError('Expected the reviewed Apache Jena Fuseki 6.2.0 jar')
    sources = [root / 'tools/migration' / (name + '.java') for name in SHARED]
    sources.append(Path(__file__).parent / 'src/JenaService.java')
    sources.append(Path(__file__).parent / 'src/JenaAdministration.java')
    sources.append(Path(__file__).parent / 'src/JenaCompaction.java')
    sources.append(Path(__file__).parent / 'src/JenaInitialImport.java')
    # The offline importer reuses the converter's cross-graph RDF verifier.
    # Neither command is exposed by the HTTP service.
    sources.append(root / 'tools/migration/ConvertLegacyRdfStar.java')
    output.mkdir(parents=True, exist_ok=False)
    try:
        (output / 'lib').mkdir()
        with tempfile.TemporaryDirectory(prefix='oldap-jena-build-') as directory:
            classes = Path(directory)
            subprocess.run([str(java_home / 'bin/javac'), '--release', '25', '-encoding', 'UTF-8',
                            '-cp', str(dependency), '-d', str(classes), *map(str, sources)], check=True)
            artifact = output / 'lib' / f'oldap-jena-service-{VERSION}.jar'
            # Fixed ZIP metadata makes identical sources/JDK/dependency reproducible.
            with zipfile.ZipFile(artifact, 'w', compression=zipfile.ZIP_DEFLATED) as jar:
                for compiled in sorted(classes.rglob('*.class')):
                    info = zipfile.ZipInfo(compiled.relative_to(classes).as_posix(), (2026, 1, 1, 0, 0, 0))
                    jar.writestr(info, compiled.read_bytes())
        shutil.copy2(dependency, output / 'lib/fuseki-server.jar')
        for name in ('LICENSE', 'NOTICE'):
            shutil.copy2(fuseki_home / name, output / ('FUSEKI_' + name))
        operator = Path(__file__).parent / 'backup.py'
        shutil.copyfile(operator, output / 'backup.py')
        launcher = output / 'start'
        launcher.write_text('''#!/bin/sh
set -eu
: "${JAVA_HOME:?Set JAVA_HOME to JDK 25}"
heap=${JAVA_HEAP_MB:-8192}
case "$heap" in ''|*[!0-9]*) echo 'JAVA_HEAP_MB must be a positive integer' >&2; exit 2;; esac
[ "$heap" -gt 0 ] || exit 2
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$JAVA_HOME/bin/java" "-Xmx${heap}m" -cp "$base/lib/*" JenaService "$@"
''')
        launcher.chmod(0o755)
        manifest = {'version': VERSION, 'backup_tool_sha256': hashlib.sha256(operator.read_bytes()).hexdigest(), 'fuseki_version': '6.2.0', 'fuseki_sha256': digest,
                    'javac': subprocess.check_output([str(java_home / 'bin/javac'), '-version'], text=True).strip(),
                    'sources': {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
                    'service_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest()}
        (output / 'build.json').write_text(json.dumps(manifest, indent=2) + '\n')
    except BaseException:
        shutil.rmtree(output)
        raise
    print('Built OLDAP Jena service ' + VERSION)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--fuseki-home', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.java_home.resolve(), args.fuseki_home.resolve(), args.output.resolve())
