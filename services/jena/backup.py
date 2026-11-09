"""Private offline backup/restore bundles for the OLDAP Jena deployment.

Stop/fence all writers, API workers, media writers and coordination Redis first.
The TDB POSIX lock additionally excludes a live Jena service throughout copying.
Other components require the operator's explicit quiescence assertion; file hashes
are integrity checks, not proof of a consistent live multi-service snapshot.
Restore only creates a new isolated directory and never starts services.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from uuid import uuid4

COMPONENTS = ('dataset', 'media', 'operations', 'coordination', 'release')


def digest(path):
    """Hash bounded chunks, including large RDF/media/Redis files."""
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def inventory(root):
    """Return file checksums and directory names; reject links and special files."""
    files, directories = {}, []
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symlinks are not supported in backup components')
        name = path.relative_to(root).as_posix()
        if path.is_dir():
            directories.append(name)
        elif path.is_file():
            files[name] = {'bytes': path.stat().st_size, 'sha256': digest(path),
                           'executable': bool(path.stat().st_mode & 0o111)}
        else:
            raise ValueError('Socket/device/special file found; provide stopped component data directories')
    return {'files': files, 'directories': directories}


@contextmanager
def stopped_dataset(dataset):
    """Hold the same POSIX lock range used by TDB, refusing a running service.

    Never copy/open this lock file again while holding it: POSIX process locks
    can be released by closing a second descriptor to the same inode.
    """
    if (dataset / 'oldap-service-format').read_text() != 'oldap-jena-service-1\n':
        raise ValueError('Expected an initialized OLDAP service dataset')
    lock = dataset / 'tdb.lock'
    if lock.is_symlink() or not lock.is_file():
        raise ValueError('Expected the existing TDB lock file')
    with lock.open('r+b') as stream:
        try:
            fcntl.lockf(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('Jena is running; stop it before backup') from error
        try:
            yield
        finally:
            fcntl.lockf(stream, fcntl.LOCK_UN)


def copy_component(source, target, dataset=False):
    """Copy regular state privately; omit dataset locks and rebuildable indexes."""
    target.mkdir(mode=0o700)
    for entry in sorted(source.iterdir()):
        if entry.is_symlink():
            raise ValueError('Symlinks are not supported in backup components')
        if dataset and entry.name == 'tdb.lock':
            continue
        # Native indexes rebuild from RDF and durable configuration at startup.
        if dataset and source.name == 'managed-text' and entry.name.startswith('index-'):
            continue
        destination = target / entry.name
        if entry.is_dir():
            copy_component(entry, destination, dataset)
        elif entry.is_file():
            shutil.copyfile(entry, destination)
            if digest(entry) != digest(destination):
                raise ValueError('Source changed or copy integrity failed')
            destination.chmod(0o700 if entry.stat().st_mode & 0o111 else 0o600)
        else:
            raise ValueError('Only stopped regular-file state can be copied')


def verify(bundle):
    """Verify a complete bundle without trusting paths from its manifest."""
    if bundle.is_symlink() or not bundle.is_dir():
        raise ValueError('Bundle must be a regular directory')
    if (bundle / 'manifest.json').is_symlink():
        raise ValueError('Manifest must not be a symlink')
    manifest = json.loads((bundle / 'manifest.json').read_text())
    if manifest.get('format') != 1 or set(manifest.get('components', {})) != set(COMPONENTS):
        raise ValueError('Unsupported or incomplete backup manifest')
    if set(p.name for p in bundle.iterdir()) != {'manifest.json', *COMPONENTS}:
        raise ValueError('Unexpected bundle entries')
    for component in COMPONENTS:
        saved = manifest['components'][component]
        for name in [*saved['files'], *saved['directories']]:
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or str(path) != name or not path.parts:
                raise ValueError('Unsafe manifest path')
        root = bundle / component
        if root.is_symlink() or not root.is_dir() or inventory(root) != saved:
            raise ValueError('Backup integrity verification failed: ' + component)
    release = json.loads((bundle / 'release/build.json').read_text())
    if 'backup_tool_sha256' in release and digest(bundle / 'release/backup.py') != release['backup_tool_sha256']:
        raise ValueError('Bundled backup operator mismatch')
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', release['version']):
        raise ValueError('Invalid service version in build manifest')
    if digest(bundle / 'release/lib/fuseki-server.jar') != release['fuseki_sha256']:
        raise ValueError('Bundled Fuseki artifact mismatch')
    if digest(bundle / 'release/lib' / ('oldap-jena-service-' + release['version'] + '.jar')) != release['service_sha256']:
        raise ValueError('Bundled service artifact mismatch')
    return manifest


def durable_publish(stage, output):
    """Flush copied bytes and directory entries before publishing the snapshot.

    Fsync errors abort publication instead of claiming durable backup completion.
    The parent is flushed after rename; an error there leaves a complete but
    durability-uncertain destination which must be inspected, never overwritten.
    """
    for path in stage.rglob('*'):
        if path.is_file():
            with path.open('rb') as stream:
                os.fsync(stream.fileno())
    directories = [p for p in stage.rglob('*') if p.is_dir()]
    for path in [*sorted(directories, key=lambda p: len(p.parts), reverse=True), stage]:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    stage.rename(output)
    descriptor = os.open(output.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def backup(roots, output, generation, *, quiesced=False):
    """Publish a new verified bundle after all deployment writers are stopped.

    Args:
        roots: Explicit directories for all five required components.
        output: New destination outside every source directory.
        generation: Operator-selected identity of the source dataset generation.
        quiesced: Explicit confirmation that all non-Jena writers are stopped.
    """
    if not quiesced or not generation or set(roots) != set(COMPONENTS):
        raise ValueError('All components, source generation and stopped-writers assertion are required')
    output = output.absolute()
    if output.exists():
        raise FileExistsError(output)
    for root in roots.values():
        if root.is_symlink() or not root.is_dir():
            raise ValueError('Components must be explicit regular directories')
        if output.resolve().is_relative_to(root.resolve()) or root.resolve().is_relative_to(output.resolve()):
            raise ValueError('Backup destination overlaps source')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.oldap-backup-', dir=output.parent))
    try:
        with stopped_dataset(roots['dataset']):
            for component in COMPONENTS:
                copy_component(roots[component], stage / component, component == 'dataset')
            manifest = {'format': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
                        'source_generation': generation, 'quiesced_by_operator': True,
                        'components': {c: inventory(stage / c) for c in COMPONENTS}}
            (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
            (stage / 'manifest.json').chmod(0o600)
            verify(stage)
            # Publication is atomic; existing destinations are never overwritten.
            durable_publish(stage, output)
        return manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def restore(bundle, output):
    """Verify before copying into a fresh, quarantined restore directory.

    Saved operations and Redis state are retained for review, not activated.
    The new generation is an operator handoff, NOT an automatic runtime switch:
    rebind endpoint/path/secrets and writer-journal generation before enabling
    any worker. Reconcile old in-flight operations explicitly; never clear gates.
    """
    manifest = verify(bundle)
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    if output.resolve().is_relative_to(bundle.resolve()) or bundle.resolve().is_relative_to(output.resolve()):
        raise ValueError('Restore destination overlaps backup')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.oldap-restore-', dir=output.parent))
    try:
        for component in COMPONENTS:
            copy_component(bundle / component, stage / component)
            if inventory(stage / component) != manifest['components'][component]:
                raise ValueError('Restored component verification failed')
        handoff = {'state': 'quarantined-not-activated', 'source_generation': manifest['source_generation'],
                   'target_generation': str(uuid4()), 'backup_manifest_sha256': digest(bundle / 'manifest.json'),
                   'required': ['Rebind paths/endpoints and review saved credentials/policy.',
                                'Fence original writers; use isolated empty object cache.',
                                'Keep restored coordinator state offline until operator reconciliation.',
                                'Bind new dataset generation before considering retained commands.',
                                'Validate identities, rights, text, media and receipts before activation.']}
        (stage / 'RESTORE_REVIEW.json').write_text(json.dumps(handoff, indent=2) + '\n')
        (stage / 'RESTORE_REVIEW.json').chmod(0o600)
        durable_publish(stage, output)
        return handoff
    finally:
        if stage.exists():
            shutil.rmtree(stage)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    save = commands.add_parser('backup')
    for component in COMPONENTS:
        save.add_argument('--' + component, type=Path, required=True)
    save.add_argument('--source-generation', required=True)
    save.add_argument('--writers-stopped', action='store_true', required=True)
    save.add_argument('--output', type=Path, required=True)
    check = commands.add_parser('verify')
    check.add_argument('bundle', type=Path)
    load = commands.add_parser('restore')
    load.add_argument('bundle', type=Path)
    load.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'backup':
        backup({c: getattr(args, c) for c in COMPONENTS}, args.output, args.source_generation, quiesced=args.writers_stopped)
    elif args.command == 'verify':
        verify(args.bundle)
    else:
        restore(args.bundle, args.output)
    print(args.command + ' completed; no services started')
