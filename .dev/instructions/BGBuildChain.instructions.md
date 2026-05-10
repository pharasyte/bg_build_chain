# bgBuildChain Copilot Instructions

## Top-Level Instructions

- Every time you make changes in this project, re-read this file and decide whether it also needs to be updated. If the architecture, workflow, module boundaries, config format, or known limitations change, update this file in the same piece of work.
- Treat `bgBuildChain/` as the repository root when working here. Paths in these instructions are relative to that root.
- Prefer source-grounded changes over assumptions. The README currently does not describe this project accurately, so use the Python source as the primary reference.
- Keep changes small and local. This codebase has partially duplicated logic and unfinished subsystems, so broad refactors are high risk unless explicitly requested.
- Preserve current behavior unless the task is specifically to change behavior. In particular, be careful around build orchestration, import resolution, file copying, and git side effects.

## Project Purpose

`bgBuildChain` is a Python-based Papyrus build orchestrator intended to replace older per-project wrapper scripts with a single configurable build entry point.

Its active responsibilities are:

- Load build settings from `.dev/project.json`.
- Resolve direct and transitive Papyrus import directories from `import_projects`.
- Compile either one file or a whole folder tree of `.psc` files.
- Mirror source files into a deployment source tree via `copy_source_to`.
- Copy plugin assets into an assets directory after compilation.

It also contains an aspirational macro/preprocessor system, but that subsystem is not fully integrated or feature-complete.

The current development direction is:

- keep `bgs_tools.build.bgbc` as the legacy reference and compatibility path,
- move new architectural work into `bgs_tools.constellation`,
- preserve `.dev/project.json` compatibility across both entry points,
- use the staged build tree in constellation as the basis for future preprocessing work.

## How The Tool Is Invoked

The active CLI entry point is:

- `src/python/bgs_tools/build/bgbc.py`

There is also a new componentized replacement entry point:

- `src/python/bgs_tools/constellation/main.py`

The constellation entry point is invoked as:

```powershell
python -m bgs_tools.constellation --verbose
```

Typical invocation is:

```powershell
python -m bgs_tools.build.bgbc --verbose
```

Important:

- `bgs_tools` is not installed as a regular package in this workspace by default.
- When running locally from source, the caller usually needs `bgBuildChain/src/python` on `PYTHONPATH`, or an equivalent editable/install path setup.
- The default config path is `.\.dev\project.json` relative to the current working directory.
- The tool assumes it is launched from the target project root, not from `bgBuildChain` itself, when building another mod project.

Practical guidance:

- prefer `python -m bgs_tools.constellation` for new implementation and validation work,
- use `python -m bgs_tools.build.bgbc` when comparing behavior against the legacy flow,
- expect both paths to consume the same `.dev/project.json` file format.

## Current Runtime Flow

The real build flow in `src/python/bgs_tools/build/bgbc.py` is:

1. Parse CLI arguments.
2. Load `.dev/project.json` if present.
3. Merge CLI arguments over config values.
4. Expand `import_projects` recursively into additional import directories.
5. Recreate the build directory.
6. Validate the configured compiler path.
7. Run git side effects through `git_handler.build_commit()`.
8. Compile either a single file or every `.psc` under the target folder.
9. Copy source files to `copy_source_to` while preserving relative structure.
10. Copy configured plugin assets to `assets_dir`.

Notes about current behavior:

- Folder builds recurse by default and stop at the first compile failure unless `--continue-on-error` is used.
- `--filter` currently behaves as an exclusion filter, not an inclusion filter. Files are compiled when there is no pattern, or when the pattern does **not** match the absolute path.
- `build_dir` is wiped on every run.
- `output_dir` is validated interactively if it does not exist.
- `copy_source_to` mirrors source layout relative to the folder being built.

The constellation flow in `src/python/bgs_tools/constellation/main.py` is the active replacement path with a componentized implementation:

1. Parse CLI arguments and load `.dev/project.json` through `bgs_tools.constellation.config`.
2. Merge CLI values over config values and resolve recursive `import_projects`.
3. Recreate `build_dir` and stage selected `.psc` files under `build_dir/src`.
4. Run the dummy no-op preprocessor boundary over staged files unless disabled.
5. Compile staged files rather than original source files.
6. Mirror original source files to `copy_source_to` after successful compilation.
7. Copy configured extras and plugin assets through `bgs_tools.constellation.packaging`.

Constellation notes:

- `build_dir` from config is honored unless `--build-dir` is explicitly provided.
- `--filter` keeps the current exclusion behavior: matching paths are skipped.
- Imported projects remain compiler import directories; they are not staged or preprocessed yet.
- The dummy preprocessor does not transform source text in normal builds.
- The staged source root is added to the compiler import path so namespaced scripts compile correctly from `build_dir/src`.
- Constellation was validated against `.dev/if_it_aint_broke` using the same `.dev/project.json` as legacy `bgbc.py`.
- Stable parity signals matched between the two entry points: same relative output file set, same layout, same byte lengths, and matching hashes for deterministic copied outputs.
- Raw `.pex` hashes are not a reliable byte-for-byte parity signal because repeated legacy builds also produce different `.pex` hashes.

## Config Model

The main config file is `.dev/project.json` in the project being built.

Fields known to be active in the current implementation include:

- `project_namespace`
- `verbose`
- `compiler_path`
- `import_projects`
- `import_dir`
- `output_dir`
- `copy_source_to`
- `assets_dir`
- `assets`
- `build_dir`

Fields that exist in argument parsing but are not part of a fully realized modern flow should be treated cautiously.

Important current detail:

- `caprica_dir` is still parsed, but it is not meaningfully used in the active build execution path.

Additional current detail:

- `build_dir` is an active part of the constellation build path rather than a recreated-but-unused directory.

## Module Layout

### Main Orchestrator

- `src/python/bgs_tools/build/bgbc.py`
- `src/python/bgs_tools/constellation/main.py`

`bgbc.py` remains the legacy monolithic implementation and the baseline for behavior comparisons. `constellation/main.py` is the new componentized orchestration path and should be treated as the primary place for forward-looking work.

### Constellation Components

- `src/python/bgs_tools/constellation/config/`
- `src/python/bgs_tools/constellation/preprocessor/`
- `src/python/bgs_tools/constellation/compile/`
- `src/python/bgs_tools/constellation/packaging/`

The boundary lines are:

- config owns argument parsing, config loading/saving, config merging, output directory validation, and recursive import project resolution.
- preprocessor owns staged-file preprocessing hooks and debug metadata.
- compile owns file discovery, filter semantics, source staging, and compiler subprocess execution.
- packaging owns source mirroring, extras copying, and flat asset copying.

Current state of those boundaries:

- config is implemented and used by the constellation entry point.
- compile is implemented, including staged source copying under `build_dir/src`.
- packaging is implemented for source mirroring, extras, and assets.
- preprocessor is currently a dummy/no-op boundary in normal builds, with legacy parser metadata still available for debug-style use.

### Compiler Layer

- `src/python/bgs_tools/build/compiler/compiler.py`
- `src/python/bgs_tools/build/compiler/constants.py`

The compiler package exists, but it currently contains duplicated or incomplete logic. The active CLI path in practice uses the `compile_script` implementation inside `bgbc.py`, not a cleanly separated compiler abstraction.

### Config Layer

- `src/python/bgs_tools/build/config/arguments.py`
- `src/python/bgs_tools/constellation/config/`

This module defines argument parsing separately, but the active CLI in `bgbc.py` currently builds its own parser inline. Treat this package as partially extracted rather than authoritative.

The constellation config package is the active structured implementation for the replacement CLI.

### Git Integration

- `src/python/bgs_tools/build/git_handler/git_handler.py`

This module is live and currently dangerous from a workflow standpoint:

- `build_commit()` performs `git add .` followed by `git commit -a -m build`.
- The module also has an unguarded example call to `commit_files(...)` at import time.
- If you are changing git behavior, treat it as user-visible and high impact.

### Preprocessor

- `src/python/bgs_tools/build/preprocessor/preprocessor.py`
- `src/python/bgs_tools/build/preprocessor/lexer/`
- `src/python/bgs_tools/build/preprocessor/parser/`
- `src/python/bgs_tools/build/preprocessor/expander/`
- `src/python/bgs_tools/build/preprocessor/scanner/`

This subsystem is only partially realized.

- `preprocess_file()` parses a source file and returns parser results.
- The CLI exposes debug and dry-run style hooks for preprocessing.
- The richer macro/include workflow appears incomplete relative to the intended design.
- Be careful not to overstate support for macro features unless you have validated them.

Constellation currently provides a dummy preprocessor package at `src/python/bgs_tools/constellation/preprocessor/`.

- Normal constellation builds leave staged source files unchanged.
- `--debug-preprocessor` can still use the legacy parser metadata path when available.
- The staged-tree boundary is ready for future transforms, but macro expansion and source rewriting are not implemented yet.
- Future preprocessing work should land in the constellation staged-tree flow first unless a task explicitly targets the legacy path.

## Includes And Namespace Rewriting

There is dormant code in `bgbc.py` for include copying and `ScriptName` rewriting:

- `copy_includes()`
- `delete_includes()`
- `change_scriptname()`

That path is currently commented out in the main folder-build execution flow. The idea appears to have been:

- copy included scripts into a build tree,
- rewrite `ScriptName` values to match their generated namespace path,
- compile against the generated tree.

Treat this as unfinished behavior unless you are explicitly restoring or redesigning it.

## Working Assumptions For Future Changes

- The project is Windows-first and path handling reflects that.
- Target consumers are Papyrus projects with mod-manager deployment directories.
- The currently proven use case is building other Starfield Papyrus projects from their own project roots.
- Recursive `import_projects` resolution is part of the intended shared-library workflow.
- Constellation is the preferred vehicle for architectural changes, parity work, and future preprocessing support.

## Known Risks And Oddities

- The README at the project root is currently unrelated to the actual tool.
- There is duplicated logic between `bgbc.py` and the `compiler` or `config` packages.
- There is also intentional overlap between legacy `bgbc.py` behavior and the new constellation packages while parity is maintained.
- The git handler has side effects both at import time and during normal builds.
- Some defaults still reflect older Caprica-era assumptions even when the configured compiler is the Creation Kit Papyrus compiler.
- Interactive directory prompts in `verify_or_create_directory()` can make automation awkward.
- The preprocessor is present, but its implemented capabilities lag behind the apparent intended macro system.
- The Papyrus compiler does not appear to emit deterministic `.pex` binaries across repeated identical builds, so parity validation should compare stable output shape and copied-file results rather than raw `.pex` hashes alone.

## Guidance For Copilot When Editing This Project

- Start by checking `src/python/bgs_tools/build/bgbc.py` before touching helper modules.
- If you move logic out of `bgbc.py`, keep runtime behavior identical unless the task explicitly authorizes behavior changes.
- If you change argument handling, keep `.dev/project.json` compatibility in mind.
- If you change import resolution, validate transitive `import_projects` behavior.
- If you change file-copy behavior, preserve relative source layout unless the task says otherwise.
- If you touch git integration, warn clearly about behavioral impact and verify whether automatic commits are still intended.
- If you improve the preprocessor, document exactly which directives or flows are now supported.
- For new work on the replacement CLI, prefer `bgs_tools.constellation` over expanding the legacy `bgbc.py` monolith unless the task explicitly targets legacy behavior.
- When validating replacement behavior, use the same project root and same `.dev/project.json` for both entry points whenever practical.
- When comparing compiled outputs, do not assume `.pex` hashes are stable across runs.

## Update Triggers

Update this file whenever any of the following change:

- the active CLI entry point,
- which CLI path is preferred for new work,
- the config schema or meaning of config fields,
- the way `import_projects` are resolved,
- the compiler invocation path,
- the source mirroring or asset copy behavior,
- the status or scope of the preprocessor,
- the git behavior during builds,
- the recommended local invocation method.