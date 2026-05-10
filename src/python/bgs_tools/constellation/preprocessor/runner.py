import copy
import shutil
from pathlib import Path

EMPTY_RESULTS = {
    "imports": [],
    "vars": [],
    "macros": [],
    "macro_calls": [],
}


def empty_results():
    return copy.deepcopy(EMPTY_RESULTS)


def load_legacy_preprocessor():
    try:
        from bgs_tools.build.preprocessor import preprocessor as legacy_preprocessor
    except ImportError:
        return None

    return legacy_preprocessor


def preprocess_file(input_path, output_path=None, imports=None):
    preprocessor_imports = tuple(imports or [])
    input_path = str(input_path)
    target_path = str(output_path) if output_path else input_path

    if target_path != input_path:
        Path(target_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(input_path, target_path)

    legacy_preprocessor = load_legacy_preprocessor()
    if legacy_preprocessor is None:
        return empty_results()

    if preprocessor_imports:
        pass

    return legacy_preprocessor.preprocess_file(target_path, output_path)


def preprocess_build_items(build_items, enabled=True, imports=None, collect_metadata=False):
    results = {}
    if not enabled:
        return results

    for item in build_items:
        if collect_metadata:
            results[item.staged_path] = preprocess_file(item.staged_path, imports=imports)
        else:
            results[item.staged_path] = empty_results()

    return results
