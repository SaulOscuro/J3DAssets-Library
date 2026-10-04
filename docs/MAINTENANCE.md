# Changing and releasing the library

## Choose the right change

- Model changes: edit the original source blend; keep its manifest path stable.
- Add/remove an asset or replace its primary preview: edit config/assets.json.
  Only explicitly listed assets are built; the old addon cache index is no
  longer required to enumerate the library.
- Change the AO template or catalogs: review config/library.json and related
  tests. Renaming a catalog changes its UUID under the current policy.
- Change conversion behavior: edit tools/build_blender.py and test it. A policy
  field does not implement new behavior by itself; unsupported profiles fail.
- Change drive paths: update the ignored config/paths.local.json. Update the
  example and architecture document when the agreed workstation layout changes.
- Change scene tools/shortcuts: work in J3DSyncManager-2.0 instead.

## Set up

Use Python 3.11+ and Blender 5.2.x. Run commands at this repository root.
Copy config/paths.example.json to config/paths.local.json, then set `blender`
to an installed executable (or leave `blender` if it is on PATH). All filesystem
roots in that local file must be absolute. Keep originals/previews available.

```powershell
Copy-Item config/paths.example.json config/paths.local.json
python tools/library.py plan --version v002
python -m unittest discover -s tests -p "test_*.py"
python tests/smoke_build.py
```

Plan is read-only: it resolves paths, checks every listed source/primary preview,
and checks root overlap. It does not build, mirror or publish. On the owner's
machine a local configuration is already populated; do not overwrite it casually.

The smoke test requires the configured original files and previews. It builds
15 representative assets spanning all nine catalogs, tests mirror/stage and
overwrite protection, and keeps its evidence only under `.work/`. It does not
change the served library or the prepared D:/H: releases. Keep build output
paths short on Windows: Blender's thumbnail image writer can fail near the
traditional 260-character path limit even if Python can access longer paths.

## Build a new release

```powershell
python tools/library.py build --version v002
```

This creates a fresh prepared release and .work/v002. It freezes input hashes,
runs the worker in isolated background Blender, reopens and appends each output,
generates native listings/thumbnails with Blender's asset_listing command, and
verifies the release manifest. Existing version/work directories are refused.
Failed partial outputs remain for diagnosis and are not a publishable release.
Inspect logs in the work directory; choose another unused version for a retry,
or explicitly review and archive a failed build before rebuilding that version.

The worker preserves original source files. It never saves the active user's
scene. Blender 5.2 is deliberately required because the listing API is versioned.

## Verify, mirror and stage

For a newly built v002, use its manifest inside the prepared folder:

```powershell
$release = 'D:\01_3D\03_LIBRARY\01_BLENDER_ASSET_LIBRARIES\J3DAssets_v002'
$manifest = Join-Path $release 'release-manifest.json'
python tools/library.py verify --root $release --manifest $manifest
python tools/library.py mirror --root $release --manifest $manifest --destination 'H:\Mi unidad\01_3D\03_LIBRARY\01_BLENDER_ASSET_LIBRARIES\J3DAssets_v002'
python tools/library.py stage --root $release --manifest $manifest --destination '.work\v002-staged'
```

Copy destinations must be new. Each copied file is hash-verified. Stage produces
`library/` and `release-manifest.json` in the staging directory; it does not touch
the currently served repository tree, run Git or publish. `mirror_root` in the
path config records the intended route; copying still needs an explicit target.
Use the printed plan to choose it. Check Google Drive syncing separately.

For the existing v001, the authoritative manifest is at this repository's root:

```powershell
python tools/library.py verify --root library --manifest release-manifest.json
```

## Review and publish

1. Review source changes, config changes, build results and a visual sample.
   Structural checks do not replace a full visual/rig review where needed.
2. Test the staged library in Blender. For a remote test, serve only the staged
   library over localhost and use an isolated cache/Blender session.
3. Keep the previous prepared version. Compare the staged manifest with the
   repository manifest, including removals. Check Git for unrelated changes.
4. Replace the repository's served `library/` contents with the reviewed staged
   `library/`, and its root manifest with the staged manifest. This is an explicit
   publication preparation step, not something the build command does. Review
   every removal and confirm it is within the repository's library directory.
5. Run the verify command above, stage only intended files, and review the diff.
   Confirm `.gitattributes` still applies `-text` to `library/**`; changing JSON
   line endings breaks embedded hashes. Preserve filename casing and URL encoding.
6. Commit and push `codex/library-release` without force. That push publishes
   the change at the existing URL. Verify the live metadata and asset downloads;
   raw GitHub caching can delay visibility of a newly pushed release.
7. Record the version, commit, Blender version, validation scope and file hash in
   docs/HISTORY.md. A rollback restores a whole matching library+manifest pair,
   using a new Git commit rather than rewriting remote history.

## Boundaries

Do not commit source authoring files, full preview galleries, ignored inventories,
credentials or machine-specific executable settings. Do not overwrite v001 or
regenerate the live listing merely to modify build code/documentation. The raw
library URL remains stable while the software around it evolves.
