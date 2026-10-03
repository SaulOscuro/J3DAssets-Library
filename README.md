# J3DAssets

Native Blender 5.2 asset library: 246 model collections in nine catalogs.
Every model uses the procedural AO-bake material, with no image textures.

## Add the remote library

1. In Blender 5.2, allow online access in Preferences.
2. Open Preferences > Asset Libraries > + > Add Remote Asset Library.
3. Paste this library URL:

   https://raw.githubusercontent.com/SaulOscuro/J3DAssets-Library/codex/library-release/library/

4. Select J3DAssets in the Asset Browser. Right-click an asset and choose Download Asset, then drag it into the scene.

For editable objects, select Append in Import Settings. Collection instancing is a separate placement option.

The URL and files are publicly accessible without signing in. This repository contains prepared distribution files; editing originals and local work reports are maintained separately.

## Release v001

BathRoom (49), CeilingStuff (23), Closets (21), Doors (31), Kitchen (17), Mirrors (4), Vents (34), WallStuff (37), Windows (30).

Original names and object hierarchies are retained. Two assets retain the existing display name Windows_window5 in different source folders (Windows_window5 and Windows_window6).
The existing primary preview is embedded in each collection. Original multi-view galleries are retained separately from this distribution.

Validation checked original-file hashes, object names, parent relationships, world transforms, mesh vertex/polygon counts, modifier names/types, collection import, AO-bake-only assignment, absence of image textures, previews, catalogs, and every published file hash.
This is structural validation; a complete visual review of all 246 models has not been performed.

See release-manifest.json for file hashes. Updates to the remote catalog do not automatically replace assets already appended into scenes.
