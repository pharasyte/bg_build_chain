# bgbc Preprocess Build Tree Plan

Plan Date: 2026-05-10

## Goal

Change the active `bgbc` build flow so compilation operates on a copied source tree inside `build_dir`, creating a safe place for future preprocessing transforms to mutate `.psc` files before they are handed to the compiler.

## Current State Review

The current code path in `src/python/bgs_tools/build/bgbc.py` already recreates `build_dir`, but it never uses that directory as compiler input. Both `--file` and `--folder` compile original source paths directly, and `copy_source_to` mirrors the same original files after compilation. The preprocessor module currently parses a file and returns parser results, but it does not emit transformed text back to disk. That means the first implementation slice is not “finish the whole preprocessor”; it is “stage the sources into `build_dir` and compile from that staged tree without breaking current build behavior.”

Key review findings that drive the plan:

- `build_dir` is wiped and recreated on every run, but it is not part of file discovery or compiler invocation.
- The folder build loop discovers `.psc` files under the original `args.folder` path and passes those original paths directly to `compile_script(...)`.
- The single-file path also compiles the original file directly.
- `compile_script(...)` currently assumes the source path used for compilation is also the source path that should be copied to `copy_source_to`.
- `preprocessor.preprocess_file(...)` is read-only from the build system’s perspective; it parses and returns data, but it does not rewrite or materialize a transformed output file.
- Dormant `copy_includes(...)`, `delete_includes(...)`, and `change_scriptname(...)` functions show an older “compile from generated files” direction, but that path is not active and should not be revived wholesale without a smaller, explicit contract.
- There are no existing automated tests in this repo, so validation must be designed as part of the implementation.

## Stage 1: Define the Staged Build Contract

### Step 1.1: Lock down the behavioral invariants before changing file flow

**Action Directive:**

Write down the exact behaviors that must remain stable when `bgbc` starts compiling from `build_dir` instead of the original source tree.

**Rationale:**

The current source flow is tightly coupled in a few places: file discovery, compiler invocation, relative path preservation for `copy_source_to`, and error handling inside the folder loop. If those relationships are not made explicit first, the first implementation attempt will almost certainly drift into accidental behavior changes. This is especially important because the attached project instructions explicitly call out file copying, import resolution, and build orchestration as high-risk areas.

**Technical Implementation:**

Capture the invariants in code comments or implementation notes before editing behavior. The important ones for this feature are:

- `--filter` must keep its current exclusion semantics unless a separate task changes it.
- `--continue-on-error` must keep controlling folder-build failure behavior.
- `copy_source_to` must continue preserving the relative layout of the built source tree.
- `import_dir` and recursive `import_projects` resolution must remain untouched for the first slice.
- `extras` and asset copying must still run after the compile step.
- `build_dir` must stay disposable and fully recreated on each run.

Add an explicit note for one design decision that must be resolved during implementation: whether `copy_source_to` should receive the original source text or the staged/transformed source text. The safer default, given the instruction to preserve current behavior unless intentionally changed, is to keep mirroring original source text unless the preprocessing feature explicitly redefines that contract.

### Step 1.2: Define a stable path-mapping model between original and staged files

**Action Directive:**

Introduce a single, explicit mapping model that can convert between original source paths and their staged counterparts under `build_dir`.

**Rationale:**

Once the compiler starts operating on staged files, every follow-on behavior depends on deterministic path mapping:

- compile targets must point at staged files,
- filter checks may still need to reason about original absolute paths,
- `copy_source_to` may need original-relative layout,
- future preprocess diagnostics should be able to point back to original files,
- single-file builds need a predictable staged location even when the input is not the root of a folder build.

Without a dedicated path-mapping abstraction, this logic will get duplicated inside the `--file` and `--folder` branches and become hard to reason about once preprocessing writes transformed content.

**Technical Implementation:**

Plan to add small helper functions in `bgbc.py` first, rather than a broad refactor into a new package. A minimal shape would look like this:

```python
def get_stage_root(build_dir: str) -> str:
    return os.path.join(build_dir, "src")

def get_staged_path(original_path: str, source_root: str, stage_root: str) -> str:
    relative_path = os.path.relpath(original_path, source_root)
    return os.path.join(stage_root, relative_path)

def get_relative_source_path(path: str, source_root: str) -> str:
    return os.path.relpath(path, source_root)
```

For folder builds, `source_root` should be the absolute folder being built. For single-file builds, the initial version should pick a narrow rule and document it clearly. The least disruptive choice is to treat the file’s parent directory as the source root for staging, because that matches the current single-file flow where the code changes into the file’s directory before compiling.

## Stage 2: Stage the Source Tree Before Compilation

### Step 2.1: Extract file discovery into a reusable collection step

**Action Directive:**

Pull the current `.psc` file discovery logic out of the `--folder` branch into a helper that returns original source files in a deterministic order.

**Rationale:**

The build tree feature needs a clear sequence:

1. collect original files,
2. copy them into the staging tree,
3. optionally preprocess staged files,
4. compile staged files.

Right now, file collection is embedded directly in the folder branch and immediately feeds the compile loop. Extracting it first gives one place to preserve the current `--no-recurse` and `--filter` behavior while making later stages simpler to reason about.

**Technical Implementation:**

The helper should return original absolute paths, not staged paths. That keeps existing filter behavior anchored to the current implementation.

```python
def collect_script_files(folder: str, no_recurse: bool) -> list[str]:
    abs_folder = os.path.abspath(folder)
    if no_recurse:
        files = [str(path.resolve()) for path in Path(abs_folder).glob("*.psc")]
    else:
        files = [str(path.resolve()) for path in Path(abs_folder).rglob("*.psc")]
    return sorted(files)
```

Keep `pattern.search(file_abspath)` behavior unchanged in the first pass, even though it currently acts as an exclusion filter.

### Step 2.2: Add a dedicated source-staging pass that mirrors originals into `build_dir`

**Action Directive:**

Add a step that copies the source inputs into a dedicated subtree under `build_dir` before any compilation happens.

**Rationale:**

This is the core enabling change. Preprocessing cannot safely mutate files in place inside the real source tree, and the current `build_dir` lifecycle already gives the tool a natural disposable workspace. The staging pass needs to happen before compilation, but it should remain intentionally simple at first: mirror the source tree exactly, without transformation, then switch the compiler to consume the staged copy.

**Technical Implementation:**

Prefer explicit file-by-file copy over a blind `copytree(...)` of the entire source directory in the first implementation. That gives tighter control over which files are staged and keeps the future preprocessing pipeline aligned with the set of files actually being built.

```python
def stage_source_files(files: list[str], source_root: str, build_dir: str) -> dict[str, str]:
    stage_root = get_stage_root(build_dir)
    staged_files = {}

    for original_path in files:
        staged_path = get_staged_path(original_path, source_root, stage_root)
        os.makedirs(os.path.dirname(staged_path), exist_ok=True)
        shutil.copy2(original_path, staged_path)
        staged_files[original_path] = staged_path

    return staged_files
```

For the first version, stage only the files selected for the build. If later preprocessing turns out to require non-compiled neighboring files, that can be widened in a follow-up change with a concrete reason.

### Step 2.3: Preserve single-file and folder-build parity when staging

**Action Directive:**

Design the staging logic so both `--file` and `--folder` go through the same “original path -> staged path -> compile” flow.

**Rationale:**

The current implementation has separate control flow for file and folder builds. If staging is only added to the folder path first, the feature will immediately become inconsistent and future preprocess behavior will be harder to maintain. The right boundary is to normalize both modes into the same internal representation as early as possible.

**Technical Implementation:**

Use a shared internal structure such as:

```python
build_items = [
    {
        "original_path": original_path,
        "staged_path": staged_path,
        "relative_path": os.path.relpath(original_path, source_root),
    }
]
```

For `--file`, treat `source_root` as `os.path.dirname(file_path)` in the first iteration. That preserves the current assumption that the process changes into the file’s containing directory before compilation.

## Stage 3: Compile from the Staged Tree Without Breaking Existing Outputs

### Step 3.1: Split “compiler input path” from “source mirroring path” inside `compile_script(...)`

**Action Directive:**

Refactor the compiler call boundary so it can compile one path while copying a different source file to `copy_source_to` if needed.

**Rationale:**

Right now `compile_script(...)` assumes one path serves both purposes:

- the file passed to the Papyrus compiler,
- the file mirrored to `copy_source_to`.

That assumption becomes incorrect as soon as staged compilation is introduced. If left unchanged, the first build-tree implementation will implicitly change `copy_source_to` to mirror transformed build outputs instead of the original source files. That might be desirable later, but it should not happen accidentally.

**Technical Implementation:**

Plan to change the call shape to make the distinction explicit.

```python
def compile_script(
    compile_path,
    import_dir,
    output_dir,
    executable,
    copy_source_to=None,
    copy_source_path=None,
    base_path=None,
):
    source_to_copy = copy_source_path or compile_path
```

Then update the mirroring logic so relative paths are derived from the original source root, not implicitly from the staged tree unless that becomes an intentional behavior change.

### Step 3.2: Switch the build loop to compile staged files while keeping filter and error behavior unchanged

**Action Directive:**

Update the build loop so the decision points still operate on original file metadata, but the compiler is invoked with staged file paths.

**Rationale:**

This keeps the external behavior stable while changing only the internal source of truth for compilation. It also makes future preprocess work cleaner because transformations can be applied to staged files without affecting filter behavior or user-facing file selection rules.

**Technical Implementation:**

The intended flow for folder builds should become:

```python
files = collect_script_files(abs_folder, args.no_recurse)
selected_files = [path for path in files if should_build(path, pattern)]
staged_files = stage_source_files(selected_files, abs_folder, build_dir)

for original_path in selected_files:
    staged_path = staged_files[original_path]
    compile_script(
        staged_path,
        import_dir,
        output_dir,
        executable,
        copy_source_to=copy_source_to,
        copy_source_path=original_path,
        base_path=abs_folder,
    )
```

Preserve the current `continue_on_error` handling in this loop exactly.

### Step 3.3: Decide how staged compilation should interact with current working directory changes

**Action Directive:**

Review the current `os.chdir(...)` calls and make a deliberate choice about whether compilation should continue changing into the original source location, change into the staged location, or stop depending on the working directory entirely.

**Rationale:**

The current code changes into the file directory for `--file` builds and into the folder path for `--folder` builds before collecting and compiling. Once compilation happens against staged files, the meaning of those `chdir(...)` calls becomes ambiguous. Leaving them untouched might still work, but only by accident. This is a fragile place to rely on implicit behavior.

**Technical Implementation:**

Treat this as a targeted compatibility review during implementation:

- If the compiler only needs explicit file and import paths, remove unnecessary `chdir(...)` usage.
- If relative compiler behavior still depends on the working directory, switch `chdir(...)` to the staged source root instead of the original source root.

Do not widen this into a general refactor. The implementation should pick one rule, validate it with a real compile, and keep the rest of the flow local.

## Stage 4: Insert the Preprocessor Boundary on Top of the Staged Tree

### Step 4.1: Define a write-capable preprocessor contract that operates on staged files

**Action Directive:**

Redefine the preprocessor boundary so it accepts a staged file path and can either leave it unchanged or rewrite it in place inside `build_dir`.

**Rationale:**

The current preprocessor API is analysis-oriented. It parses a file and returns parser results, but that is not enough to support a compile-time transform pipeline. The staging change should therefore establish the right integration point without forcing the whole macro system to be finished in the same change.

**Technical Implementation:**

Plan for a contract shaped more like this:

```python
def preprocess_file(input_path: str, output_path: str | None = None, *, imports=None):
    # Read staged file
    # Parse directives
    # Materialize transformed text to output_path or overwrite input_path
    # Return structured metadata for debugging
```

For the first implementation slice, it is acceptable for the preprocessor step to be a no-op passthrough when `--disable-preprocessor` is set or when no supported directives are found. The important change is that the build pipeline now has a place to call it safely.

### Step 4.2: Keep imported dependency directories out of the first preprocessing scope unless explicitly required

**Action Directive:**

Scope the first feature so only the current build target’s source files are staged and preprocessed unless implementation evidence shows imported projects also need staged transforms immediately.

**Rationale:**

`import_projects` currently resolve to source directories that are fed to the compiler as import paths. Expanding the first build-tree change to recursively stage and preprocess imported projects would significantly widen the blast radius and create more path-management complexity. The smallest safe change is to keep imported sources as compiler imports for now and restrict staged preprocessing to the primary build target.

**Technical Implementation:**

Document this boundary in the implementation notes and in the instructions file once the feature lands. If imported-project preprocessing becomes necessary later, add it as a separate plan item with explicit rules for:

- stage location for dependency projects,
- collision handling between import trees,
- whether transformed imports are temporary or cacheable,
- how original-to-staged diagnostic mapping is preserved.

### Step 4.3: Align `--debug-preprocessor` and dry-run modes with the staged pipeline

**Action Directive:**

Update the debug and dry-run hooks so they inspect the same staged pipeline that normal builds will use.

**Rationale:**

Debugging a different path than the one that actually compiles is a maintenance trap. If the real build flow stages files before preprocessing, the debug path should expose that same behavior or it will stop being a reliable diagnostic tool.

**Technical Implementation:**

Use the existing flags as follows:

- `--debug-preprocessor`: stage the requested file, run preprocessing, and report both the structured parse result and the staged output path.
- `--dry-run-level collectFiles`: show original selected files and their planned staged destinations.
- `--dry-run-level preprocess`: show which staged files would be rewritten, without invoking the compiler.

This work should stay narrow. Do not attempt to build a full reporting subsystem in the same change.

## Stage 5: Validation, Documentation, and Rollout Safety

### Step 5.1: Add fixture-based coverage or a repeatable manual validation workflow

**Action Directive:**

Create a small validation surface that proves the new staged build flow works before additional preprocessing behavior is added.

**Rationale:**

There are no automated tests in the repository today, and this feature changes the path that every compile operation uses. Validation therefore has to be designed as part of the implementation, not left until the end.

**Technical Implementation:**

At minimum, validate these scenarios:

- folder build with preprocessing disabled still compiles the same set of files as before,
- single-file build stages the file and compiles from the staged path,
- `copy_source_to` preserves relative layout and intentionally chosen content source,
- `--continue-on-error` still controls folder-build failure behavior,
- assets and extras still run after compilation,
- `build_dir` contains the expected staged source layout and is recreated on rerun.

If the repo grows tests during implementation, add a small fixture tree with a nested `.psc` structure and one file that can be intentionally excluded by `--filter`.

### Step 5.2: Update the project instructions file when the feature is actually implemented

**Action Directive:**

Once code changes land, update `.dev/instructions/BGBuildChain.instructions.md` to describe the new staged build flow and the current scope of preprocessing support.

**Rationale:**

The attached instructions explicitly require updates when source mirroring behavior, compiler invocation path, preprocessor scope, or recommended usage changes. This feature touches all of those areas.

**Technical Implementation:**

When the implementation is complete, revise these sections in the instructions file:

- `Current Runtime Flow`
- `Config Model` if any preprocessing-related config becomes active
- `Preprocessor`
- `Includes And Namespace Rewriting` if any dormant code is removed, replaced, or intentionally left unused
- `Update Triggers` only if the meaning of those triggers changes

## Compressed Checklist

- [ ] Stage 1: Define the Staged Build Contract
- [ ] Step 1.1: Lock down the behavioral invariants before changing file flow
- [ ] Step 1.2: Define a stable path-mapping model between original and staged files
- [ ] Stage 2: Stage the Source Tree Before Compilation
- [ ] Step 2.1: Extract file discovery into a reusable collection step
- [ ] Step 2.2: Add a dedicated source-staging pass that mirrors originals into `build_dir`
- [ ] Step 2.3: Preserve single-file and folder-build parity when staging
- [ ] Stage 3: Compile from the Staged Tree Without Breaking Existing Outputs
- [ ] Step 3.1: Split “compiler input path” from “source mirroring path” inside `compile_script(...)`
- [ ] Step 3.2: Switch the build loop to compile staged files while keeping filter and error behavior unchanged
- [ ] Step 3.3: Decide how staged compilation should interact with current working directory changes
- [ ] Stage 4: Insert the Preprocessor Boundary on Top of the Staged Tree
- [ ] Step 4.1: Define a write-capable preprocessor contract that operates on staged files
- [ ] Step 4.2: Keep imported dependency directories out of the first preprocessing scope unless explicitly required
- [ ] Step 4.3: Align `--debug-preprocessor` and dry-run modes with the staged pipeline
- [ ] Stage 5: Validation, Documentation, and Rollout Safety
- [ ] Step 5.1: Add fixture-based coverage or a repeatable manual validation workflow
- [ ] Step 5.2: Update the project instructions file when the feature is actually implemented