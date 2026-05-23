import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BuildItem:
    original_path: str
    staged_path: str
    source_root: str
    relative_path: str
    stage_root: str | None = None
    generated: bool = False
    parent_original_path: str | None = None
    emitted_paths: list[str] = field(default_factory=list)
    transpile_metadata: dict = field(default_factory=dict)
    source_map_path: str | None = None


def prepare_build_dir(build_dir):
    shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(build_dir, exist_ok=True)


def get_stage_root(build_dir):
    return os.path.join(build_dir, "src")


def get_staged_path(original_path, source_root, stage_root):
    relative_path = os.path.relpath(original_path, source_root)
    return os.path.join(stage_root, relative_path)


def stage_source_files(files, source_root, build_dir):
    source_root = os.path.abspath(source_root)
    stage_root = get_stage_root(build_dir)
    build_items = []

    for original_path in files:
        original_path = os.path.abspath(str(original_path))
        relative_path = os.path.relpath(original_path, source_root)
        staged_path = get_staged_path(original_path, source_root, stage_root)
        Path(staged_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original_path, staged_path)
        build_items.append(
            BuildItem(
                original_path=original_path,
                staged_path=staged_path,
                source_root=source_root,
                relative_path=relative_path,
                stage_root=stage_root,
            )
        )

    return build_items
