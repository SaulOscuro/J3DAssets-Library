# Library history

## 2026-10-04 - Version the preparation logic and organization

The existing public J3DAssets-Library repository now owns the reusable build
pipeline, explicit relative asset manifest, policy configuration, workstation
path template, architecture guide, maintenance workflow and agent instructions.
There is no second library repository and the existing remote URL is retained.

The v001 scripts previously lived in the J3DSyncManager task's ignored scratch
folder. Their proven Blender worker was adapted into a configurable pipeline.
The old cache index is no longer needed for enumeration: config/assets.json
explicitly lists all 246 inputs and their primary previews.

Confirmed rules: AO-bake only, no image textures, preserve names/transforms/
geometry/modifiers and existing parenting, add no parents. Scene operators
remain owned by J3DSyncManager-2.0. The studio storage policy remains owned by
3d-production-workspace; the path template records the owner's approved K:/D:/H:
library arrangement without moving data.

Validation:

- Eight Python tests passed, covering relative-path escape/root overlap checks,
  read-only planning, duplicate paths, corrupt hashes, unlisted files, copy
  verification and refusal to overwrite a destination.
- The complete existing published release passed: 246 assets, nine catalogs,
  496 distribution files checked against native listing hashes and the manifest.
- A new isolated background Blender 5.2.2 smoke build passed with 15 assets
  spanning all nine catalogs, both Windows_window5 paths, the ampersand filename
  and the three assets with formerly missing textures. Prepared files were
  reopened/appended and checked for the approved material/structure rules.
- Native listing/thumbnail generation, release verification, mirror/stage copies
  and refusal to rebuild the same version passed. Final local evidence is under
  `.work/s-87anlh5j/`; evidence paths are not public downloads.
- An initial deeply nested test exposed the Windows thumbnail writer's path
  limit. The invalid release was rejected; a shorter isolated path passed.
- No production v002 was built. All published v001 files and the release
  manifest remain unchanged; no source originals, galleries or addon files
  were changed. No new full visual or rig review is claimed.

## 2026-10-03 - Publish v001

- Distribution commit: `2cb6d30` on `codex/library-release`.
- 246 collection assets in nine catalogs, AO-bake only and zero image textures.
- Prepared master on D:, verified copy at the matching H: library path.
- All prepared files were reopened and appended in Blender 5.2.2. The live
  native remote downloader/import test passed for 15 representative assets.
- Source hashes and published file hashes were verified. Original editing
  files and full preview galleries remain on K:.
- The remote library is public. Appended scene copies are not automatically
  replaced when a new library version is published.
