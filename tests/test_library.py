import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('library', REPO / 'tools/library.py')
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)


class LibraryTests(unittest.TestCase):
    def setUp(self):
        work = REPO / '.work/tests'
        work.mkdir(parents=True, exist_ok=True)
        self.scratch = tempfile.TemporaryDirectory(dir=work)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)

    def fixture(self):
        root = self.root / 'release'
        root.mkdir()
        files = {'asset.blend': b'fixture', 'preview.webp': b'preview', 'blender_assets.cats.txt': b'VERSION 1\n'}
        for name, content in files.items():
            (root / name).write_bytes(content)
        def ref(name):
            return {'url': name, 'hash': 'SHA256:' + library.sha(root / name)}
        page = {'files': [{'path': 'asset.blend', 'hash': ref('asset.blend')['hash'], 'size_in_bytes': 7}],
                'assets': [{'name': 'Asset', 'id_type': 'COLLECTION', 'files': ['asset.blend'],
                            'meta': {'catalog_id': 'catalog'}, 'thumbnail': ref('preview.webp')}]}
        library.write_json(root / 'page.json', page)
        library.write_json(root / 'index.json', {'asset_count': 1, 'file_count': 1,
            'catalogs': [{'path': 'Category', 'uuids': ['catalog']}], 'pages': [ref('page.json')]})
        library.write_json(root / '_asset-library-meta.json', {'api_versions': {'v1': ref('index.json')}})
        listing, _ = library.listing_files(root)
        manifest = root / 'release-manifest.json'
        library.write_json(manifest, {'version': 'v001', 'asset_count': 1, 'catalog_count': 1, 'files': listing})
        return root, manifest

    def test_paths_and_overlap(self):
        for relative in ('../secret', 'x/../secret', 'C:\\secret', '/secret', '//server/share', 'name:stream', 'x//y'):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                library.safe_child(self.root, relative)
        self.assertEqual(library.safe_child(self.root, 'x/y.blend'), self.root / 'x/y.blend')
        with self.assertRaises(ValueError):
            library.disjoint(self.root, self.root / 'child')

    def test_public_release(self):
        report = library.verify(REPO / 'library', REPO / 'release-manifest.json')
        self.assertGreater(report['assets'], 0)
        self.assertGreater(report['catalogs'], 0)

    def test_copy_stage_and_refuse_overwrite(self):
        root, manifest = self.fixture()
        target = self.root / 'stage'
        report = library.copy_release(root, manifest, target, stage=True)
        self.assertFalse(report['published'])
        self.assertEqual((target / 'library/asset.blend').read_bytes(), b'fixture')
        with self.assertRaises(FileExistsError):
            library.copy_release(root, manifest, target, stage=True)
        self.assertEqual((target / 'library/asset.blend').read_bytes(), b'fixture')

    def test_corrupt_hash_is_rejected_before_copy(self):
        root, manifest = self.fixture()
        (root / 'asset.blend').write_bytes(b'changed')
        target = self.root / 'mirror'
        with self.assertRaises(ValueError):
            library.copy_release(root, manifest, target)
        self.assertFalse(target.exists())

    def test_unlisted_files_block_staging(self):
        root, manifest = self.fixture()
        (root / 'private.txt').write_text('do not publish')
        with self.assertRaises(ValueError):
            library.verify(root, manifest)

    def test_encoded_escape_in_listing(self):
        root, manifest = self.fixture()
        metadata = library.read_json(root / '_asset-library-meta.json')
        metadata['api_versions']['v1']['url'] = '%2e%2e/outside.json'
        library.write_json(root / '_asset-library-meta.json', metadata)
        with self.assertRaises(ValueError):
            library.verify(root, manifest)

    def test_bad_release_version(self):
        with self.assertRaises(ValueError):
            library.get_plan(None, None, None, '../../old')

    def test_plan_safety_and_readonly(self):
        paths = {key: str(self.root / key) for key in
                 ('source_root', 'cache_root', 'prepared_root', 'work_root')}
        paths['blender'] = 'blender'
        for key in ('source_root', 'cache_root'):
            Path(paths[key]).mkdir()
        (Path(paths['source_root']) / 'one.blend').write_bytes(b'not opened by plan')
        (Path(paths['cache_root']) / 'one.png').write_bytes(b'not opened by plan')
        policy = library.read_json(REPO / 'config/library.json')
        policy['material_template'] = 'one.blend'
        entry = {'name': 'One', 'category': policy['catalogs'][0], 'blend_path': 'one.blend', 'preview': 'one.png'}
        for name, value in (('paths', paths), ('policy', policy), ('assets', [entry])):
            library.write_json(self.root / (name + '.json'), value)
        def plan():
            return library.get_plan(self.root / 'paths.json', self.root / 'policy.json',
                                    self.root / 'assets.json', 'v002')
        self.assertEqual(plan()['count'], 1)
        self.assertFalse(Path(paths['prepared_root']).exists())
        self.assertFalse(Path(paths['work_root']).exists())
        library.write_json(self.root / 'assets.json', [entry, {**entry, 'blend_path': 'ONE.blend'}])
        with self.assertRaises(ValueError):
            plan()
        library.write_json(self.root / 'assets.json', [entry])
        for target in (paths['source_root'], str(REPO / 'library')):
            paths['prepared_root'] = target
            library.write_json(self.root / 'paths.json', paths)
            with self.subTest(target=target), self.assertRaises(ValueError):
                plan()
        paths['prepared_root'] = str(self.root / 'prepared_root')
        library.write_json(self.root / 'paths.json', paths)
        policy['folder_prefix'] = '../../elsewhere'
        library.write_json(self.root / 'policy.json', policy)
        with self.assertRaises(ValueError):
            plan()


if __name__ == '__main__':
    unittest.main()
