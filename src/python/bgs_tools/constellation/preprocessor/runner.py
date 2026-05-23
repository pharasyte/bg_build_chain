import copy
import shutil
import os
from pathlib import Path

from bgs_tools.constellation.compile.staging import BuildItem
from bgs_tools.constellation.preprocessor.diagnostics import TranspilerError
from bgs_tools.constellation.preprocessor.pipeline import transpile_source

EMPTY_RESULTS = {
    "imports": [],
    "vars": [],
    "macros": [],
    "macro_calls": [],
}


class PreprocessorError(Exception):
    pass


def empty_results():
    return copy.deepcopy(EMPTY_RESULTS)


def resolve_output_path(input_path, output_path=None):
    if not output_path:
        return str(input_path)

    output_path = Path(output_path)
    if output_path.suffix:
        return str(output_path)

    return str(output_path / Path(input_path).name)


def write_emitted_files(transpile_result):
    for emitted_file in transpile_result.emitted_files:
        Path(emitted_file.path).parent.mkdir(parents=True, exist_ok=True)
        with open(emitted_file.path, "w", encoding="utf-8") as source_file:
            source_file.write(emitted_file.text)


def create_generated_build_item(parent_item, emitted_file):
    stage_root = parent_item.stage_root or os.path.dirname(parent_item.staged_path)
    relative_path = emitted_file.relative_path or os.path.relpath(emitted_file.path, stage_root)
    return BuildItem(
        original_path=parent_item.original_path,
        staged_path=emitted_file.path,
        source_root=parent_item.source_root,
        relative_path=relative_path,
        stage_root=stage_root,
        generated=True,
        parent_original_path=parent_item.original_path,
    )


def run_preprocessor(input_path, output_path=None, imports=None, context=None):
    preprocessor_imports = tuple(imports or [])
    input_path = str(input_path)
    target_path = resolve_output_path(input_path, output_path)

    if target_path != input_path:
        Path(target_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(input_path, target_path)

    with open(target_path, "r", encoding="utf-8") as source_file:
        source_text = source_file.read()

    if preprocessor_imports:
        pass

    try:
        transpile_result = transpile_source(source_text, target_path, context=context)
    except TranspilerError as error:
        raise PreprocessorError(str(error)) from error

    write_emitted_files(transpile_result)
    return transpile_result


def preprocess_file(input_path, output_path=None, imports=None, context=None, collect_metadata=False):
    transpile_result = run_preprocessor(input_path, output_path=output_path, imports=imports, context=context)
    metadata = transpile_result.to_metadata(include_empty=collect_metadata)

    if collect_metadata:
        return metadata

    return metadata if transpile_result.has_transforms else empty_results()


def preprocess_build_items(build_items, enabled=True, imports=None, context=None, collect_metadata=False):
    results = {}
    if not enabled:
        return results

    generated_items = []
    for item in list(build_items):
        transpile_result = run_preprocessor(
            item.staged_path,
            imports=imports,
            context=context,
        )
        metadata = transpile_result.to_metadata(include_empty=collect_metadata)
        item.transpile_metadata = metadata
        item.emitted_paths = [emitted_file.path for emitted_file in transpile_result.emitted_files]
        results[item.staged_path] = metadata if collect_metadata or transpile_result.has_transforms else empty_results()

        for emitted_file in transpile_result.generated_files:
            generated_items.append(create_generated_build_item(item, emitted_file))

    build_items.extend(generated_items)

    return results
