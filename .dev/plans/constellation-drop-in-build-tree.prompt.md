# Constellation Drop-In Build Tree Plan

Plan Date: 2026-05-10

## Goal

Create a new `bgs_tools.constellation` package as a drop-in replacement target for the active `bgbc` utility, preserving current behavior while moving the implementation into clear components and executing the staged build-tree design from `preprocess-build-tree.prompt.md`.

## Boundary Map

- `bgs_tools.constellation.main`: CLI entry point and high-level orchestration only.
- `bgs_tools.constellation.config`: argument parser, JSON config loading/saving, CLI-over-config merge behavior, import project expansion, and output directory validation.
- `bgs_tools.constellation.preprocessor`: dummy/no-op staged-file preprocessor with debug metadata parity where possible.
- `bgs_tools.constellation.compile`: script discovery, filter semantics, build-tree staging, compiler subprocess execution, and compile error policy.
- `bgs_tools.constellation.packaging`: source mirroring, extras copying, and asset copying.

## Stage 1: Package Scaffold and Config Handling

### Step 1.1: Create the `bgs_tools.constellation` package tree

**Action Directive:**

Create a new package under `src/python/bgs_tools/constellation` with subpackages for `config`, `preprocessor`, `compile`, and `packaging`, plus `main.py` and `__main__.py`.

**Rationale:**

The existing `bgbc.py` is a monolithic entry point. A separate package lets the new implementation preserve runtime behavior while avoiding a risky in-place refactor of the current utility.

**Technical Implementation:**

Create this tree:

```text
src/python/bgs_tools/constellation/
  __init__.py
  __main__.py
  main.py
  config/
  preprocessor/
  compile/
  packaging/
```

Checkpoint after this stage if the scaffold plus config work stays under 300 lines. If it grows beyond that, commit the scaffold first and config second.

### Step 1.2: Implement drop-in argument and config resolution

**Action Directive:**

Move the active parser and config behavior from `bgbc.py` into the config package while preserving the current default values and truthy CLI merge semantics.

**Rationale:**

The new tool must be usable against the same `.dev/project.json` files. Behavior such as string-to-list conversion for `preprocessor_imports`, dict support in `import_projects`, and semicolon compiler imports must remain stable.

**Technical Implementation:**

The config package owns:

- parser construction,
- config file loading and saving,
- merge behavior,
- `import_projects` recursion,
- build/output/copy/assets/extras config normalization,
- interactive directory validation parity for `output_dir`.

## Stage 2: Dummy Preprocessor Package

### Step 2.1: Implement a no-op staged preprocessor boundary

**Action Directive:**

Create a preprocessor package that can run against staged files, return metadata, and leave file contents unchanged.

**Rationale:**

The first target is staged-tree alignment, not completing the macro system. The dummy preprocessor gives the compile pipeline a safe extension point without mutating original sources.

**Technical Implementation:**

Expose `preprocess_file(path, output_path=None, imports=None)` and `preprocess_build_items(items, enabled=True, imports=None)`. When enabled, parse metadata through the legacy preprocessor if available; otherwise return empty parity-shaped metadata. Do not transform text yet.

## Stage 3: Compile Pass and Build Tree

### Step 3.1: Implement script discovery and current filter semantics

**Action Directive:**

Move `.psc` discovery and exclusion-style filtering into the compile package.

**Rationale:**

The current `--filter` behavior is inverted: matching files are skipped. The drop-in replacement must keep this behavior for the first cut.

**Technical Implementation:**

Create helpers for recursive/non-recursive discovery and `should_compile(path, pattern)`.

### Step 3.2: Execute the staged build-tree plan

**Action Directive:**

Stage selected source files into `build_dir/src`, optionally run the dummy preprocessor over the staged files, and compile from the staged paths.

**Rationale:**

This gives the preprocessor a disposable workspace and keeps original source files untouched.

**Technical Implementation:**

Represent each build item with original path, staged path, source root, and relative path. Compile staged paths, while packaging can still mirror original source text unless the transform contract changes later.

## Stage 4: Packaging Pass

### Step 4.1: Extract source mirroring and post-compile copy behavior

**Action Directive:**

Move `copy_source_to`, extras, and assets behavior into the packaging package.

**Rationale:**

Packaging is currently intertwined with compilation, but it has different failure semantics: source mirroring is tied to successful compile, missing assets are skipped, and extras can destructively replace destinations.

**Technical Implementation:**

Expose `mirror_source(...)`, `copy_extras(...)`, and `copy_assets(...)` with current behavior preserved.

## Stage 5: Main Entrypoint and Fixture Validation

### Step 5.1: Wire the orchestrator in `main.py`

**Action Directive:**

Build the new CLI flow from the component packages.

**Rationale:**

`main.py` should show the lifecycle plainly without owning the implementation details.

**Technical Implementation:**

Flow: parse/resolve config, prepare build directory, validate compiler, handle debug preprocessor, collect/stage/preprocess/compile, then run extras/assets packaging.

### Step 5.2: Validate against the scratch-redirected fixture

**Action Directive:**

Use `.dev/if_it_aint_broke` only after its `.dev/project.json` outputs point to `.dev/scratch/if_it_aint_broke`.

**Rationale:**

The fixture contains real deployment paths. Scratch redirection prevents the new tool from writing into live Mod Organizer or project asset locations during testing.

**Technical Implementation:**

Pre-create scratch directories, run `python -m bgs_tools.constellation --help`, run a dry-run collection against the fixture where possible, and avoid full compiler execution if dependencies or compiler paths are unavailable.

## Stage 6: Documentation and Checkpoints

### Step 6.1: Update project instructions

**Action Directive:**

Update `.dev/instructions/BGBuildChain.instructions.md` after implementation to describe `bgs_tools.constellation`, the staged build tree, and current dummy preprocessor scope.

**Rationale:**

The repository instructions require updates when the entry point, compiler invocation path, preprocessor status, and source mirroring behavior change.

### Step 6.2: Commit checkpoints by major component

**Action Directive:**

Create git checkpoints as each major component is completed. Split any component over roughly 300 changed lines into multiple commits.

**Rationale:**

The requested implementation is broad. Checkpoints make review and rollback easier without mixing unrelated component boundaries.

## Compressed Checklist

- [ ] Stage 1: Package Scaffold and Config Handling
- [ ] Step 1.1: Create the `bgs_tools.constellation` package tree
- [ ] Step 1.2: Implement drop-in argument and config resolution
- [ ] Stage 2: Dummy Preprocessor Package
- [ ] Step 2.1: Implement a no-op staged preprocessor boundary
- [ ] Stage 3: Compile Pass and Build Tree
- [ ] Step 3.1: Implement script discovery and current filter semantics
- [ ] Step 3.2: Execute the staged build-tree plan
- [ ] Stage 4: Packaging Pass
- [ ] Step 4.1: Extract source mirroring and post-compile copy behavior
- [ ] Stage 5: Main Entrypoint and Fixture Validation
- [ ] Step 5.1: Wire the orchestrator in `main.py`
- [ ] Step 5.2: Validate against the scratch-redirected fixture
- [ ] Stage 6: Documentation and Checkpoints
- [ ] Step 6.1: Update project instructions
- [ ] Step 6.2: Commit checkpoints by major component