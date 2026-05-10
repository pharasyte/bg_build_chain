import os
import re
from pathlib import Path

from bgs_tools.constellation.config.constants import RED, RESET


def collect_script_files(folder, no_recurse=False):
    abs_folder = os.path.abspath(folder)
    if no_recurse:
        files = [str(path.resolve()) for path in Path(abs_folder).glob("*.psc")]
    else:
        files = [str(path.resolve()) for path in Path(abs_folder).rglob("*.psc")]

    return sorted(files)


def compile_filter(pattern_text):
    return re.compile(pattern_text) if pattern_text else None


def should_compile(file_path, pattern=None):
    return (not pattern) or (not pattern.search(file_path))


def filter_script_files(files, pattern_text=None, verbose=False):
    pattern = compile_filter(pattern_text)
    selected_files = []

    for file_path in files:
        if pattern:
            print(f"{RED}Checking {file_path}: pattern.search({Path(file_path).name}) = {pattern.search(file_path)}{RESET}")
        if should_compile(file_path, pattern):
            selected_files.append(file_path)

    if verbose:
        print(f"Selected {len(selected_files)} scripts:\n{selected_files}")

    return selected_files

