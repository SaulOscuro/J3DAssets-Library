"""Plan/build immutable Blender libraries and verify/stage distribution files.

Python 3.11+; build additionally needs Blender 5.2. No automatic Git publication.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit

REPO = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def safe_child(root, relative):
    relative = str(relative).replace('\\', '/')
    if not relative or PureWindowsPath(relative).drive or Path(relative).is_absolute():
        raise ValueError(f'Expected a relative path: {relative}')
    if any(part in ('', '.', '..') or ':' in part for part in relative.split('/')):
        raise ValueError(f'Unsafe relative path: {relative}')
    root = Path(root).resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f'Path escapes root: {relative}')
    return target


def disjoint(*paths):
    roots = [Path(path).resolve() for path in paths]
    for index, first in enumerate(roots):
        for second in roots[index + 1:]:
            if first.is_relative_to(second) or second.is_relative_to(first):
                raise ValueError(f'Roots must not overlap: {first} / {second}')


def get_plan(paths_file, policy_file, assets_file, version):
    if not re.fullmatch(r'v\d{3,}', version):
        raise ValueError('Use a release version such as v002.')
    paths, policy = read_json(paths_file), read_json(policy_file)
    if policy['schema_version'] != 1 or policy['profile'] != 'ao-bake-no-textures-v1':
        raise ValueError('Unsupported build policy; update the worker and its tests first.')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', policy['folder_prefix']):
        raise ValueError('folder_prefix must be a simple directory name.')
    if policy['blender_series'] != '5.2':
        raise ValueError('This worker supports Blender 5.2.x.')
    for field in ('source_root', 'cache_root', 'prepared_root', 'work_root'):
        if not Path(paths[field]).is_absolute():
            raise ValueError(f'{field} must be absolute in the local paths configuration.')
    source, cache = Path(paths['source_root']).resolve(), Path(paths['cache_root']).resolve()
    destination = Path(paths['prepared_root']).resolve() / (policy['folder_prefix'] + '_' + version)
    work = Path(paths['work_root']).resolve() / version
    protected = [source, cache, destination, work, REPO / 'library']
    mirror = None
    if paths.get('mirror_root'):
        if not Path(paths['mirror_root']).is_absolute():
            raise ValueError('mirror_root must be absolute.')
        mirror = Path(paths['mirror_root']).resolve() / destination.name
        protected.append(mirror)
    disjoint(*protected)
    entries, seen = read_json(assets_file), set()
    if not entries:
        raise ValueError('The asset manifest is empty.')
    for entry in entries:
        relative = entry['blend_path'].replace('\\', '/')
        if relative.casefold() in seen or Path(relative).suffix.lower() != '.blend':
            raise ValueError(f'Duplicate or invalid blend path: {relative}')
        seen.add(relative.casefold())
        if entry['category'] not in policy['catalogs'] or not entry['name'].strip():
            raise ValueError(f'Invalid asset name or catalog: {relative}')
        if not safe_child(source, relative).is_file():
            raise FileNotFoundError(relative)
        if not safe_child(cache, entry['preview']).is_file():
            raise FileNotFoundError(entry['preview'])
    material_source = safe_child(source, policy['material_template'])
    if not material_source.is_file():
        raise FileNotFoundError(material_source)
    return {'version': version, 'source': str(source), 'cache': str(cache),
            'destination': str(destination), 'mirror': str(mirror) if mirror else None,
            'work': str(work), 'blender': paths['blender'], 'policy': policy,
            'policy_sha256': sha(policy_file), 'asset_manifest_sha256': sha(assets_file),
            'material_source': str(material_source), 'count': len(entries), 'entries': entries}


def listing_files(root):
    root = Path(root).resolve()
    included = {'_asset-library-meta.json', 'blender_assets.cats.txt'}
    seen_files, seen_assets = set(), set()
    metadata = read_json(root / '_asset-library-meta.json')

    def check_ref(url, expected):
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError(f'Expected a local listing reference: {url}')
        relative = unquote(parsed.path)
        path = safe_child(root, relative)
        if expected != 'SHA256:' + sha(path):
            raise ValueError(f'Listing hash mismatch: {relative}')
        included.add(relative)
        return path

    version = metadata['api_versions']['v1']
    index = read_json(check_ref(version['url'], version['hash']))
    assets = []
    for reference in index['pages']:
        page = read_json(check_ref(reference['url'], reference['hash']))
        for file in page['files']:
            path = check_ref(file['path'], file['hash'])
            if file['path'] in seen_files or path.stat().st_size != file['size_in_bytes']:
                raise ValueError(f'Duplicate file or incorrect size: {path}')
            if path.stat().st_size >= 100 * 1024 * 1024:
                raise ValueError(f'File too large for this Git distribution: {path}')
            seen_files.add(file['path'])
        assets.extend(page['assets'])
    catalogs = {identifier for catalog in index['catalogs'] for identifier in catalog['uuids']}
    for asset in assets:
        if asset['id_type'] != 'COLLECTION' or not asset['files']:
            raise ValueError('Expected a collection asset with a blend file.')
        key = (tuple(asset['files']), asset['name'])
        if key in seen_assets or not set(asset['files']).issubset(seen_files):
            raise ValueError(f'Duplicate or unresolved asset: {asset["name"]}')
        seen_assets.add(key)
        if asset['meta']['catalog_id'] not in catalogs:
            raise ValueError(f'Unknown catalog: {asset["name"]}')
        thumbnail = asset.get('thumbnail')
        if not thumbnail:
            raise ValueError(f'Missing generated thumbnail: {asset["name"]}. Check the Blender listing log and Windows path length.')
        check_ref(thumbnail['url'], thumbnail['hash'])
    if len(assets) != index['asset_count'] or len(seen_files) != index['file_count']:
        raise ValueError('Listing counts differ.')
    files = [{'path': name, 'sha256': sha(safe_child(root, name)),
              'bytes': safe_child(root, name).stat().st_size} for name in sorted(included)]
    return files, index


def verify(root, manifest_path):
    root, manifest = Path(root).resolve(), read_json(manifest_path)
    actual, index = listing_files(root)
    expected = manifest['files']
    if len({f['path'] for f in expected}) != len(expected):
        raise ValueError('Duplicate manifest paths.')
    if sorted(actual, key=lambda f: f['path']) != sorted(expected, key=lambda f: f['path']):
        raise ValueError('Release manifest and listing files differ.')
    if manifest['asset_count'] != index['asset_count'] or manifest['catalog_count'] != len(index['catalogs']):
        raise ValueError('Manifest counts differ from listing.')
    # Extra release files must not accidentally enter a later Git publication.
    actual_paths = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    allowed = {f['path'] for f in actual} | {'release-manifest.json', 'RELEASE_INFO.txt'}
    # Native Blender writes empty timestamp sentinels during thumbnail export.
    # They are local build metadata and are never part of the copied release.
    allowed.update(p.relative_to(root).as_posix() for p in root.rglob('.last_modified')
                   if p.parent.name.endswith('_thumbnails') and p.is_file() and p.stat().st_size == 0)
    if actual_paths - allowed:
        raise ValueError(f'Unlisted files in release: {sorted(actual_paths - allowed)}')
    return {'status': 'PASS', 'version': manifest['version'], 'assets': index['asset_count'],
            'catalogs': len(index['catalogs']), 'files': len(actual)}


def build(plan):
    destination, work = Path(plan['destination']), Path(plan['work'])
    if destination.exists() or work.exists():
        raise FileExistsError('Release/work directory exists; choose a new version or review the partial build.')
    # Freeze source and primary preview hashes before opening Blender.
    assets = []
    for entry in plan['entries']:
        source = safe_child(plan['source'], entry['blend_path'])
        preview = safe_child(plan['cache'], entry['preview'])
        assets.append({'entry': {**entry, 'thumb_paths': [entry['preview']]},
                       'source': str(source), 'source_sha256': sha(source),
                       'preview_sha256': sha(preview)})
    work.mkdir(parents=True, exist_ok=False)
    job = {key: value for key, value in plan.items() if key != 'entries'}
    job['assets'] = assets
    job['worker_sha256'] = sha(REPO / 'tools' / 'build_blender.py')
    job['material_source_sha256'] = sha(plan['material_source'])
    write_json(work / 'inventory.json', job)
    env = dict(os.environ)
    for name in ('BLENDER_USER_CONFIG', 'BLENDER_USER_EXTENSIONS'):
        path = work / name.lower()
        path.mkdir()
        env[name] = str(path)
    def blender(label, arguments):
        with (work / (label + '.log')).open('w', encoding='utf-8') as log:
            subprocess.run([plan['blender'], '--factory-startup', '--background',
                            '--disable-autoexec', *arguments], check=True, env=env,
                           stdout=log, stderr=subprocess.STDOUT, timeout=3600)
    blender('build', ['--python-exit-code', '1', '--python', str(REPO / 'tools/build_blender.py'),
                      '--', str(work / 'inventory.json')])
    summary = read_json(work / 'build_summary.json')
    if summary['passed'] != plan['count'] or summary['failed']:
        raise ValueError(f'Build failed; inspect {work}. Nothing was published.')
    blender('listing', ['--command', 'asset_listing', 'generate', str(destination)])
    metadata_path = destination / '_asset-library-meta.json'
    metadata = read_json(metadata_path)
    metadata['name'], metadata['contact'] = plan['policy']['name'], plan['policy']['contact']
    write_json(metadata_path, metadata)
    files, index = listing_files(destination)
    manifest = {'version': plan['version'], 'blender': summary['blender'],
                'asset_count': plan['count'], 'catalog_count': len(index['catalogs']),
                'material': plan['policy']['material'], 'image_textures': 0,
                'policy_sha256': plan['policy_sha256'],
                'asset_manifest_sha256': plan['asset_manifest_sha256'],
                'worker_sha256': job['worker_sha256'], 'files': files}
    for asset in assets:
        if sha(asset['source']) != asset['source_sha256']:
            raise ValueError('Source changed during build.')
    write_json(destination / 'release-manifest.json', manifest)
    return verify(destination, destination / 'release-manifest.json')


def copy_release(root, manifest_path, destination, stage=False):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    disjoint(root, destination, REPO / 'library')
    result = verify(root, manifest_path)
    if destination.exists():
        raise FileExistsError(f'Refusing existing destination: {destination}')
    manifest = read_json(manifest_path)
    destination.mkdir(parents=True, exist_ok=False)
    output = destination / 'library' if stage else destination
    for item in manifest['files']:
        source, target = safe_child(root, item['path']), safe_child(output, item['path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if sha(target) != item['sha256']:
            raise ValueError(f'Copy hash mismatch: {target}')
    write_json(destination / 'release-manifest.json', manifest)
    verify(output, destination / 'release-manifest.json')
    return {**result, 'destination': str(destination), 'published': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('plan', 'build'):
        sub = commands.add_parser(name)
        sub.add_argument('--paths', type=Path, default=REPO / 'config/paths.local.json')
        sub.add_argument('--policy', type=Path, default=REPO / 'config/library.json')
        sub.add_argument('--assets', type=Path, default=REPO / 'config/assets.json')
        sub.add_argument('--version', required=True)
    for name in ('verify', 'mirror', 'stage'):
        sub = commands.add_parser(name)
        sub.add_argument('--root', type=Path, required=True)
        sub.add_argument('--manifest', type=Path, required=True)
        if name != 'verify':
            sub.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command in ('plan', 'build'):
            plan = get_plan(args.paths, args.policy, args.assets, args.version)
            result = build(plan) if args.command == 'build' else {k: v for k, v in plan.items() if k not in ('entries', 'policy')}
        elif args.command == 'verify':
            result = verify(args.root, args.manifest)
        else:
            result = copy_release(args.root, args.manifest, args.destination, args.command == 'stage')
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
