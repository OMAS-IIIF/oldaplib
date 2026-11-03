"""Offline bundle integrity, path and non-overwrite regression tests."""
import json
from pathlib import Path
import tempfile
import unittest

from backup import backup, restore, verify, digest, COMPONENTS


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.roots = {name: self.root / name for name in COMPONENTS}
        for root in self.roots.values():
            root.mkdir()
        dataset = self.roots['dataset']
        (dataset / 'oldap-service-format').write_text('oldap-jena-service-1\n')
        (dataset / 'tdb.lock').touch()
        (dataset / 'Data-0001').mkdir()
        (dataset / 'Data-0001/data').write_bytes(b'owned unit fixture')
        (self.roots['media'] / 'file').write_bytes(b'media')
        release = self.roots['release']
        (release / 'lib').mkdir()
        dependency = release / 'lib/fuseki-server.jar'
        dependency.write_bytes(b'dependency')
        artifact = release / 'lib/oldap-jena-service-0.1.0.jar'
        artifact.write_bytes(b'service')
        (release / 'build.json').write_text(json.dumps({'version': '0.1.0',
            'fuseki_sha256': digest(dependency), 'service_sha256': digest(artifact)}))
        (release / 'start').write_text('launcher')
        (release / 'start').chmod(0o700)
        self.bundle = self.root / 'bundle'

    def save(self):
        return backup(self.roots, self.bundle, 'source', quiesced=True)

    def test_roundtrip_preserves_files_and_private_permissions(self):
        self.save()
        restored = self.root / 'restored'
        review = restore(self.bundle, restored)
        self.assertEqual((restored / 'media/file').read_bytes(), b'media')
        self.assertEqual((restored / 'media/file').stat().st_mode & 0o777, 0o600)
        self.assertTrue((restored / 'release/start').stat().st_mode & 0o100)
        self.assertNotEqual(review['source_generation'], review['target_generation'])
        self.assertFalse((restored / 'dataset/tdb.lock').exists())

    def test_existing_destinations_are_not_overwritten(self):
        self.save()
        with self.assertRaises(FileExistsError):
            self.save()
        target = self.root / 'target'
        target.mkdir()
        with self.assertRaises(FileExistsError):
            restore(self.bundle, target)

    def test_corrupt_file_and_extra_file_are_refused(self):
        self.save()
        (self.bundle / 'media/file').write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            restore(self.bundle, self.root / 'target')
        self.assertFalse((self.root / 'target').exists())
        (self.bundle / 'media/file').write_bytes(b'media')
        (self.bundle / 'media/extra').touch()
        with self.assertRaises(ValueError):
            verify(self.bundle)

    def test_unsafe_manifest_paths_are_refused(self):
        self.save()
        path = self.bundle / 'manifest.json'
        data = json.loads(path.read_text())
        data['components']['media']['files']['../../outside'] = {}
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            restore(self.bundle, self.root / 'target')

    def test_symlink_sources_and_manifests_are_refused(self):
        (self.roots['media'] / 'link').symlink_to(self.roots['media'] / 'file')
        with self.assertRaises(ValueError):
            self.save()
        (self.roots['media'] / 'link').unlink()
        self.save()
        manifest = self.bundle / 'manifest.json'
        manifest.rename(self.root / 'outside.json')
        manifest.symlink_to(self.root / 'outside.json')
        with self.assertRaises(ValueError):
            verify(self.bundle)

    def test_overlapping_backup_path_is_refused(self):
        with self.assertRaises(ValueError):
            backup(self.roots, self.roots['dataset'] / 'backup', 'source', quiesced=True)

    def test_stopped_writers_assertion_is_required(self):
        with self.assertRaises(ValueError):
            backup(self.roots, self.bundle, 'source')


if __name__ == '__main__':
    unittest.main()
