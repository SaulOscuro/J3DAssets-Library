# J3DAssets library maintenance

This repository owns the asset manifest, preparation rules, builder, validation,
and published Blender remote library. Read README.md and docs/MAINTENANCE.md.

- Preserve source files, names, object transforms, geometry, modifiers and
  existing parenting. Never add parent handles, clear existing parenting, join
  meshes, or reorganize originals as part of library preparation.
- The current approved material rule is AO-bake only, with zero image textures.
  New material behavior requires an explicit change of policy and validation.
- Build only assets listed in config/assets.json. Preserve relative paths and
  stable catalog UUIDs. Duplicate display names in different paths are valid.
- Workstation defaults are in config/paths.example.json. Machine overrides and
  absolute-path inventories/logs belong in ignored paths.local.json and .work/.
  Keep source originals and cache/gallery contents out of this public repo.
- Build new immutable vNNN directories; do not overwrite an existing release,
  including a partial build. Keep prior releases until explicitly retired.
- Test in a separate background Blender with isolated preferences. Do not use
  the running production Blender session to execute the builder.
- Never alter library/** line endings: native listing references are hashed.
  Validate all listing, thumbnail and blend hashes before staging/publication.
- Build/mirror/stage commands do not publish. Review the staged files and Git
  diff before replacing the served library. A Git push on codex/library-release
  publishes changes at the existing public URL; do not change that URL casually.
- Keep Make Asset Editable and other scene tools in J3DSyncManager-2.0. This repo
  does not own the studio-wide routing policy in 3d-production-workspace.
- Generated files and tests belong in this repository's .work directory or an
  explicitly selected workspace destination. Never use Blender/install folders.
