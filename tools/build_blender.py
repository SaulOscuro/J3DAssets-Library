"""Derived from the validated v001 builder; run through tools/library.py."""
import bpy
import hashlib
import json
import sys
import time
import traceback
import uuid
from pathlib import Path

if not bpy.app.background:
    raise RuntimeError('Run this worker in a separate background Blender, never in a production session.')
if bpy.app.version[:2] != (5, 2):
    raise RuntimeError('This build profile requires Blender 5.2.x.')
inventory = json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text(encoding='utf-8'))
HERE = Path(inventory['work'])
ROOT = Path(inventory['destination'])
CACHE = Path(inventory['cache'])
POLICY = inventory['policy']
PROFILE = POLICY['profile']
MATERIAL = POLICY['material']
MATERIAL_SOURCE = inventory['material_source']
RESULTS = HERE / 'results'
RESULTS.mkdir(exist_ok=False)
ROOT.mkdir(parents=True, exist_ok=False)

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()

def signature():
    bpy.context.view_layer.update()
    return {obj.name:{'type':obj.type, 'parent':obj.parent.name if obj.parent else None,
        'matrix':[float(v) for row in obj.matrix_world for v in row],
        'vertices':len(obj.data.vertices) if obj.type=='MESH' else None,
        'polygons':len(obj.data.polygons) if obj.type=='MESH' else None,
        'materials':[s.material.name if s.material else None for s in obj.material_slots],
        'modifiers':[(m.name,m.type) for m in obj.modifiers]} for obj in bpy.data.objects}

def compare(before, after):
    assert before.keys() == after.keys(), 'Object names differ'
    for name, previous in before.items():
        current = after[name]
        for key in ('type','parent','vertices','polygons','modifiers'):
            assert previous[key] == current[key], (name,key,previous[key],current[key])
        assert all(abs(a-b)<1e-5 for a,b in zip(previous['matrix'], current['matrix'])), (name,'world transform')

def all_ids():
    return list(bpy.data.user_map())

def validate_dependencies():
    assert not bpy.data.libraries, 'Live linked libraries remain'
    for image in bpy.data.images:
        if image.source != 'GENERATED':
            assert image.packed_file or image.packed_files, ('unpacked image',image.name,image.filepath)
    for font in bpy.data.fonts:
        assert font.filepath == '<builtin>' or font.packed_file, ('unpacked font',font.filepath)
    assert not bpy.data.cache_files and not bpy.data.volumes, 'External simulation/volume requires separate review'
    assert not bpy.data.images, 'Image textures remain'
    assert len(bpy.data.materials)==1 and bpy.data.materials[0].name==MATERIAL, 'Unexpected material'
    for obj in bpy.data.objects:
        if hasattr(obj.data,'materials'):
            assert len(obj.material_slots)==1 and obj.material_slots[0].material==bpy.data.materials[MATERIAL], obj.name

def apply_ao_material():
    with bpy.data.libraries.load(MATERIAL_SOURCE,link=False,recursive=True) as (available,requested):
        assert MATERIAL in available.materials
        requested.materials=[MATERIAL]
    canonical=requested.materials[0]
    for previous in list(bpy.data.materials):
        if previous != canonical:
            previous.user_remap(canonical)
            bpy.data.materials.remove(previous)
    canonical.name=MATERIAL
    for obj in bpy.data.objects:
        if hasattr(obj.data,'materials'):
            obj.data.materials.clear()
            obj.data.materials.append(canonical)
            for slot in obj.material_slots:
                slot.link='DATA'
                slot.material=canonical
            if obj.type=='MESH':
                for polygon in obj.data.polygons:
                    polygon.material_index=0
    for group in [canonical.node_tree]+list(bpy.data.node_groups):
        if group and group.bl_idname=='ShaderNodeTree':
            assert not any(node.type in {'TEX_IMAGE','TEX_ENVIRONMENT'} for node in group.nodes), 'Unexpected texture in AO template'

for position, asset in enumerate(inventory['assets'],1):
    started = time.time()
    entry = asset['entry']
    result_path = RESULTS / f'{position:03d}.json'
    target = ROOT / entry['blend_path']
    source = Path(asset['source'])
    result = {'position':position,'name':entry['name'],'category':entry['category'],
              'relative':entry['blend_path'],'source_sha256':asset['source_sha256'],'profile':PROFILE}
    try:
        assert sha(source) == asset['source_sha256'], 'Source changed since inventory'
        assert not target.exists(), 'Refusing existing output file'
        assert sha(MATERIAL_SOURCE) == inventory['material_source_sha256'], 'Material template changed'
        bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
        original = signature()
        assert original, 'No objects in source'
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        with bpy.data.libraries.load(str(source),link=False,recursive=True) as (available,requested):
            requested.objects = list(available.objects)
        objects = list(requested.objects)
        collection = bpy.data.collections.new(entry['name'])
        bpy.context.scene.collection.children.link(collection)
        for obj in objects:
            assert obj is not None
            collection.objects.link(obj)
        compare(original,signature())
        apply_ao_material()
        for item in all_ids():
            if item.asset_data:
                item.asset_clear()
            if item.library_weak_reference:
                item.library_weak_reference.filepath = '//'
                item.library_weak_reference.id_name = ''
        bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
        for image in list(bpy.data.images):
            assert image.users-int(image.use_fake_user)==0, ('Image used outside material',image.name)
            bpy.data.images.remove(image)
        for library in list(bpy.data.libraries):
            user_map = bpy.data.user_map()
            assert not user_map.get(library) and not any(item.library==library for item in user_map)
            bpy.data.libraries.remove(library)
        bpy.ops.file.pack_all()
        validate_dependencies()
        # Packed images are self-contained; keep a portable unpack target instead of author machine paths.
        for image in bpy.data.images:
            if image.packed_file or image.packed_files:
                suffix = Path(image.filepath).suffix or '.png'
                image.filepath = '//textures/' + bpy.path.clean_name(image.name) + suffix
        collection.asset_mark()
        catalog = str(uuid.uuid5(uuid.NAMESPACE_URL,POLICY['catalog_namespace']+entry['category']))
        collection.asset_data.catalog_id = catalog
        collection.asset_data.description = 'J3DAssets - complete model collection'
        collection.asset_data.tags.new('J3D')
        collection.asset_data.tags.new(entry['category'])
        if 'preferred_import_method' in collection.asset_data.bl_rna.properties:
            collection.asset_data.preferred_import_method = 'APPEND'
        thumb = CACHE / entry['thumb_paths'][0]
        assert sha(thumb) == asset['preview_sha256'], 'Primary preview changed'
        with bpy.context.temp_override(id=collection):
            assert bpy.ops.ed.lib_id_load_custom_preview(filepath=str(thumb)) == {'FINISHED'}
        assert collection.preview.image_size[0] > 0
        target.parent.mkdir(parents=True,exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
        bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False,use_scripts=False)
        compare(original,signature())
        validate_dependencies()
        collection = bpy.data.collections[entry['name']]
        assert [item for item in all_ids() if item.asset_data] == [collection]
        assert len(collection.all_objects) == len(original)
        assert collection.asset_data.catalog_id == catalog and collection.preview.image_size[0] > 0
        assert all(not item.library_weak_reference or (item.library_weak_reference.filepath.startswith('//') and not item.library_weak_reference.id_name) for item in all_ids())
        for image in bpy.data.images:
            if image.packed_file or image.packed_files:
                assert len(image.pixels) > 0 and image.has_data, ('Packed image cannot decode',image.name)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        with bpy.data.libraries.load(str(target),link=False,recursive=True,assets_only=True) as (available,requested):
            assert available.collections == [entry['name']]
            requested.collections = [entry['name']]
        bpy.context.scene.collection.children.link(requested.collections[0])
        compare(original,signature())
        assert sha(source) == asset['source_sha256'], 'Original changed'
        result.update(status='PASS',output_sha256=sha(target),output_bytes=target.stat().st_size,
                      object_count=len(original),catalog_id=catalog,seconds=round(time.time()-started,2))
    except Exception as exc:
        result.update(status='FAIL',error=repr(exc),traceback=traceback.format_exc())
    result_path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('ASSET_RESULT',position,'/',inventory['count'],result['status'],entry['name'],result.get('error',''),flush=True)

results = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(RESULTS.glob('*.json'))]
categories = sorted({a['entry']['category'] for a in inventory['assets']})
catalogs = [str(uuid.uuid5(uuid.NAMESPACE_URL,POLICY['catalog_namespace']+category))+':'+category+':'+category for category in categories]
(ROOT/'blender_assets.cats.txt').write_text('VERSION 1\n\n'+'\n'.join(catalogs)+'\n',encoding='utf-8')
summary = {'blender':bpy.app.version_string,'count':len(results),'passed':sum(r['status']=='PASS' for r in results),
           'failed':[r for r in results if r['status']!='PASS'],'root':str(ROOT)}
(HERE/'build_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print('LIBRARY_BUILD_SUMMARY',json.dumps({k:v for k,v in summary.items() if k!='failed'}),'failed',len(summary['failed']),flush=True)

if summary['passed'] != inventory['count'] or summary['failed']:
    raise RuntimeError('Build validation failed; inspect build_summary.json')
