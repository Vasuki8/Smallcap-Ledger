import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.package import PACKAGE_MANIFEST, PACKAGE_PREFIX, package_sources, write_package


class PackageManifestTests(unittest.TestCase):
    def test_generated_manifest_is_not_a_package_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'README.md').write_text('current source\n',encoding='utf-8')
            (root/PACKAGE_MANIFEST).write_text('stale manifest\n',encoding='utf-8')
            (root/'data').mkdir()
            (root/'data'/'ledger.sqlite3').write_bytes(b'data')
            (root/'.git').mkdir()
            (root/'.git'/'config').write_text('git metadata\n',encoding='utf-8')
            (root/'ignored.zip').write_bytes(b'zip')
            (root/'__pycache__').mkdir()
            (root/'__pycache__'/'ignored.pyc').write_bytes(b'pyc')

            selected=[p.relative_to(root).as_posix() for p in package_sources(root)]

            self.assertEqual(selected,['README.md'])

    def test_package_contains_exactly_one_fresh_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'docs').mkdir()
            source=root/'docs'/'note.txt'
            source.write_text('retained input\n',encoding='utf-8')
            (root/PACKAGE_MANIFEST).write_text('stale manifest\n',encoding='utf-8')
            output=root/'bundle.zip'

            manifest=write_package(
                output,
                package_sources(root),
                '2026-09-28T00:00:00+00:00',
                root=root,
            )

            manifest_path=PACKAGE_PREFIX+PACKAGE_MANIFEST
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.namelist().count(manifest_path),1)
                payload=json.loads(archive.read(manifest_path))
                self.assertEqual(payload['prepared_at'],'2026-09-28T00:00:00+00:00')
                self.assertEqual(payload['files'],manifest)
                self.assertEqual(
                    [row['path'] for row in payload['files']],
                    [PACKAGE_PREFIX+'docs/note.txt'],
                )
                self.assertNotIn(manifest_path,[row['path'] for row in payload['files']])

    def test_writer_rejects_manifest_as_explicit_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            stale=root/PACKAGE_MANIFEST
            stale.write_text('stale manifest\n',encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError,'manifest cannot be a package input'):
                write_package(
                    root/'bundle.zip',
                    [stale],
                    '2026-09-28T00:00:00+00:00',
                    root=root,
                )


if __name__=='__main__':
    unittest.main()
