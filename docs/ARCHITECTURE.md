# Library responsibilities and paths

## Where each kind of logic lives

| Responsibility | Source of truth |
| --- | --- |
| Which assets are included, their names, categories and primary previews | config/assets.json |
| Material template, build profile and stable catalog namespace | config/library.json |
| Preparation, validation, copying and staging | tools/library.py and tools/build_blender.py |
| Published collection assets, previews and native listings | library/ |
| Published file hashes and release version | release-manifest.json |
| Workstation path template | config/paths.example.json |
| This machine's executable and path overrides | config/paths.local.json (ignored) |
| Scene editing actions, including Make Asset Editable | [J3DSyncManager-2.0](https://github.com/SaulOscuro/J3DSyncManager-2.0) |
| Studio-wide storage organization | [3d-production-workspace](https://github.com/SaulOscuro/3d-production-workspace) |

## Current owner workstation mapping

| Role | Location |
| --- | --- |
| Original editing files | `K:\Mi unidad\J3DAssets` |
| Original previews and multi-image galleries | `K:\Mi unidad\J3DCache` |
| Prepared local library releases | `D:\01_3D\03_LIBRARY\01_BLENDER_ASSET_LIBRARIES\J3DAssets_vNNN` |
| Owner-authorized shared test/distribution copies | `H:\Mi unidad\01_3D\03_LIBRARY\01_BLENDER_ASSET_LIBRARIES\J3DAssets_vNNN` |
| This repository checkout | `D:\04_SOFTWARE_TOOLS\01_REPOS\WORKSPACE_SYSTEMS\J3DAssets-Library` |
| Private build inventories, results and logs | `.work/<version>/` inside this repository |

D: is the durable local working tier. The H: location is the specific shared
library destination requested by the owner; it does not change the general
studio routing rules. These are explicit copies, not an automatic D:/H: sync.
GitHub serves its own committed copy independently of either drive or the PC.
Google Drive cloud-sync completion is separate from local file verification.

The example configuration preserves this map in Git. Copy it to the ignored
local configuration and adjust drive letters and the Blender executable on
another computer. The executable version/path is not an asset identity.

## Asset contract

Each source blend becomes one collection asset containing every source object.
Original names, mesh vertex/polygon counts, modifiers, transforms and parenting
are checked before and after preparation. Material assignments are deliberately
normalized to one procedural AO-bake material. There are no image textures.
Only the collection is marked as an asset. Its primary preview is embedded;
the full original gallery remains in the cache and is not published.

The parenting audit of v001 found 210 assets without object parents and 36 with
existing internal parents, mostly doors/closets. The owner's final instruction
is to preserve those relationships exactly and add no parents. Collections
organize complete models without requiring a new object parent.

Catalog IDs are UUID5 values made from `j3d-assets/catalog/` plus the exact
category name. Keep the namespace and category spelling stable. Two assets
named Windows_window5 in different folders are intentional distinct entries;
the relative source path, not display name alone, identifies the input.

## Editing and runtime behavior

For this workflow use Append with Instance Collections > When Appending off.
Blender then imports editable objects inside their collection. Make Asset
Editable is a manual addon action for already instanced assets; it has no live
conversion handler. The remote library itself does not execute addon code.
Publishing a new library does not replace assets already appended into scenes.

## Reproducibility boundary

Git now versions the recipe, explicit asset list, path template and distribution.
Original authoring blends and full galleries are still maintained separately;
GitHub is not their backup. Local build inventories freeze source/preview hashes,
and new manifests record policy/asset-list/worker hashes. Native Blender output
is validated structurally and by published hashes; byte-identical rebuilt blend
files across runs or Blender patch versions are not promised.

Prepared D:/H: version folders are retained checkpoints. The remote `library/`
directory is the current served release; Git history retains older published
states. Never edit only the published copy and assume the authoring source or
other copies will receive that edit.
