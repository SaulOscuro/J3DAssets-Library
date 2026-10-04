"""Build a representative release only inside .work, using available originals."""
import argparse
import importlib.util
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('library', REPO / 'tools/library.py')
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paths', type=Path, default=REPO / 'config/paths.local.json')
    args = parser.parse_args()
    work = REPO / '.work'
    work.mkdir(exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix='s-', dir=work))
    selected, categories = [], set()
    special = {'Windows_window5', 'Kitchen_Pack_Fridge&Micro',
               'WallStuff_Enchufes_enchufe3', 'WallStuff_Stuffs_stuff6', 'WallStuff_Stuffs_stuff7'}
    for entry in library.read_json(REPO / 'config/assets.json'):
        if entry['category'] not in categories or entry['name'] in special:
            selected.append(entry)
            categories.add(entry['category'])
    paths = library.read_json(args.paths)
    paths.update(prepared_root=str(scratch / 'r'), work_root=str(scratch / 'jobs'), mirror_root='')
    library.write_json(scratch / 'paths.json', paths)
    library.write_json(scratch / 'assets.json', selected)
    plan = library.get_plan(scratch / 'paths.json', REPO / 'config/library.json', scratch / 'assets.json', 'v001')
    print('SMOKE_BUILD', len(selected), 'assets in', scratch, flush=True)
    result = library.build(plan)
    root = Path(plan['destination'])
    manifest = root / 'release-manifest.json'
    library.copy_release(root, manifest, scratch / 'mirror')
    library.copy_release(root, manifest, scratch / 'stage', stage=True)
    try:
        library.build(plan)
    except FileExistsError:
        pass
    else:
        raise AssertionError('Existing release was not protected.')
    library.write_json(scratch / 'result.json', {**result, 'mirror': 'PASS', 'stage': 'PASS',
                       'overwrite_refused': True, 'production_library_modified': False})
    print('SMOKE_PASS', result, 'evidence:', scratch, flush=True)


if __name__ == '__main__':
    main()
