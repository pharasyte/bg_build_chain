import os
import sys

from bgs_tools.constellation.compile import (
    BGBCompileError,
    collect_script_files,
    compile_build_items,
    filter_script_files,
    prepare_build_dir,
    stage_source_files,
)
from bgs_tools.constellation.config import resolve_config
from bgs_tools.constellation.config.constants import GREEN, RESET
from bgs_tools.constellation.packaging import copy_assets, copy_extras, mirror_source
from bgs_tools.constellation.preprocessor import PreprocessorError, preprocess_build_items, preprocess_file


def verbose_print(verbose, message):
    if verbose:
        print(message)


def option(build_config, name, default=None):
    return build_config.values.get(name, getattr(build_config.args, name, default))


def validate_compiler(compiler_path):
    print(f"Using compiler at {compiler_path}")
    if not os.path.isfile(compiler_path):
        print(f"Compiler not found at {compiler_path}.")
        raise SystemExit(1)


def stage_single_file(file_path, build_dir):
    file_path = os.path.abspath(file_path)
    source_root = os.path.dirname(file_path)
    os.chdir(source_root)
    return stage_source_files([file_path], source_root, build_dir)


def stage_folder(folder, build_config):
    abs_folder = os.path.abspath(folder)
    os.chdir(abs_folder)
    print(f"Abs folder: {abs_folder}")
    print(f"Filter: {option(build_config, 'filter')}")

    files = collect_script_files(abs_folder, no_recurse=bool(option(build_config, "no_recurse", False)))
    verbose_print(build_config.verbose, f"Found {len(files)} scripts:\n{files}")

    selected_files = filter_script_files(files, option(build_config, "filter"), verbose=build_config.verbose)
    return stage_source_files(selected_files, abs_folder, build_config.build_dir)


def print_collection_dry_run(build_items):
    for item in build_items:
        print(f"{item.original_path} -> {item.staged_path}")


def run_debug_preprocessor(build_config):
    print("Debugging preprocessor.")
    file_path = option(build_config, "file")
    if not file_path:
        print("Please specify a file to debug the preprocessor.")
        raise SystemExit(1)

    build_items = stage_single_file(file_path, build_config.build_dir)
    results = preprocess_file(
        build_items[0].staged_path,
        build_config.output_dir,
        imports=build_config.preprocessor_imports,
        context=build_config.values,
        collect_metadata=True,
    )
    print(results)
    raise SystemExit(0)


def compile_items(build_items, build_config):
    staged_import_dir = os.path.join(build_config.build_dir, "src")
    import_dir = [staged_import_dir] + list(build_config.import_dir)

    def mirror_successful_source(item):
        stage_root = item.stage_root or staged_import_dir
        mirror_source(
            item.staged_path,
            copy_source_to=build_config.copy_source_to,
            base_path=stage_root,
            verbose=build_config.verbose,
        )

    return compile_build_items(
        build_items,
        import_dir,
        build_config.output_dir,
        build_config.compiler_path,
        verbose=build_config.verbose,
        continue_on_error=bool(option(build_config, "continue_on_error", False)),
        on_success=mirror_successful_source,
    )


def main(argv=None):
    build_config = resolve_config(argv)
    prepare_build_dir(build_config.build_dir)
    print(f"{GREEN}Build directory: {build_config.build_dir}{RESET}")
    validate_compiler(build_config.compiler_path)

    print(f"args: {build_config.args}")

    if option(build_config, "debug_preprocessor", False):
        run_debug_preprocessor(build_config)

    if option(build_config, "file"):
        build_items = stage_single_file(option(build_config, "file"), build_config.build_dir)
    elif option(build_config, "folder"):
        build_items = stage_folder(option(build_config, "folder"), build_config)
    else:
        print("Please specify either --file or --folder.")
        return

    dry_run_level = option(build_config, "dry_run_level")

    if dry_run_level == "collectFiles":
        print_collection_dry_run(build_items)
        return

    try:
        if not option(build_config, "disable_preprocessor", False):
            results = preprocess_build_items(
                build_items,
                enabled=True,
                imports=build_config.preprocessor_imports,
                context=build_config.values,
                collect_metadata=(dry_run_level == "preprocess"),
            )
            if dry_run_level == "preprocess":
                print(results)
                return

        compile_items(build_items, build_config)
    except PreprocessorError as exc:
        print(exc)
        raise SystemExit(1) from exc
    except BGBCompileError as exc:
        raise SystemExit(1) from exc

    copy_extras(build_config.extras)
    copy_assets(build_config.assets, build_config.assets_dir)


if __name__ == "__main__":
    main(sys.argv[1:])
