# J3DAssets

Native Blender 5.2 asset library: 246 model collections in nine catalogs.
Every model uses the procedural AO-bake material, with no image textures.

## Add the remote library

1. In Blender 5.2, allow online access in Preferences.
2. Open Preferences > Asset Libraries > + > Add Remote Asset Library.
3. Paste this library URL:

   https://raw.githubusercontent.com/SaulOscuro/J3DAssets-Library/codex/library-release/library/

4. Select J3DAssets in the Asset Browser. Right-click an asset and choose Download Asset, then drag it into the scene.

For immediately editable objects, select **Append** and disable **Instance Collections > When Appending**.
The collection still keeps the complete asset organized, and source parenting is preserved without adding parents.

The URL and files are publicly accessible without signing in. This repository versions the library rules,
relative asset manifest, build/validation tools, path template and prepared distribution files.
Editing originals and private build reports are maintained separately.

## Maintain or change the library

| Change | File or repository |
| --- | --- |
| Included assets, names, categories, previews | [config/assets.json](config/assets.json) |
| AO material template and catalog rules | [config/library.json](config/library.json) |
| Drive paths and output locations | [config/paths.example.json](config/paths.example.json), copied to ignored `paths.local.json` |
| Preparation and validation logic | [tools/](tools/) |
| Scene tools such as Make Asset Editable | [J3DSyncManager-2.0](https://github.com/SaulOscuro/J3DSyncManager-2.0) |

Read [architecture and current paths](docs/ARCHITECTURE.md), [the update workflow](docs/MAINTENANCE.md),
and [maintenance history](docs/HISTORY.md). Future sessions should start with [AGENTS.md](AGENTS.md).
No new parent handles, automatic scene conversion, or changes to original source files are part of the builder.

```powershell
python tools/library.py plan --version v002
python tools/library.py verify --root library --manifest release-manifest.json
```

The first command uses an ignored local paths configuration; see the setup guide.
Builds use new versioned directories. Build, mirror and stage do not publish or change the live URL.

## Release v001

BathRoom (49), CeilingStuff (23), Closets (21), Doors (31), Kitchen (17), Mirrors (4), Vents (34), WallStuff (37), Windows (30).

Original names and object hierarchies are retained. Two assets retain the existing display name Windows_window5 in different source folders (Windows_window5 and Windows_window6).
The existing primary preview is embedded in each collection. Original multi-view galleries are retained separately from this distribution.

Validation checked original-file hashes, object names, parent relationships, world transforms, mesh vertex/polygon counts, modifier names/types, collection import, AO-bake-only assignment, absence of image textures, previews, catalogs, and every published file hash.
This is structural validation; a complete visual review of all 246 models has not been performed.

See release-manifest.json for file hashes. Updates to the remote catalog do not automatically replace assets already appended into scenes.
