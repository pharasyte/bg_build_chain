from dataclasses import dataclass, field

from bgs_tools.constellation.preprocessor.diagnostics import Diagnostic


@dataclass
class TreeSitterParseInfo:
    available: bool
    root_kind: str | None = None
    has_error: bool = False
    language_module: str | None = None
    reason: str | None = None

    def to_dict(self):
        data = {
            "engine": "tree-sitter",
            "available": self.available,
            "root_kind": self.root_kind,
            "has_error": self.has_error,
        }
        if self.language_module:
            data["language_module"] = self.language_module
        if self.reason:
            data["reason"] = self.reason
        return data


@dataclass
class LinkQuestDirective:
    plugin_file: str
    quest_id: str
    line_number: int
    raw_text: str

    def to_dict(self):
        return {
            "name": "LinkQuest",
            "args": [self.plugin_file, self.quest_id],
            "line": self.line_number,
        }


@dataclass
class SourceFile:
    file_path: str
    source_text: str
    body_lines: list[str]
    script_name: str | None = None
    directives: list[LinkQuestDirective] = field(default_factory=list)
    generated_functions: list[str] = field(default_factory=list)
    parser: TreeSitterParseInfo | None = None

    def body_text(self):
        return "".join(self.body_lines)


@dataclass
class EmittedFile:
    path: str
    text: str
    kind: str = "primary"
    relative_path: str | None = None

    def to_dict(self):
        data = {"path": self.path, "kind": self.kind}
        if self.relative_path:
            data["relative_path"] = self.relative_path
        return data


@dataclass
class TranspileResult:
    source_path: str
    primary: EmittedFile
    diagnostics: list[Diagnostic] = field(default_factory=list)
    generated_files: list[EmittedFile] = field(default_factory=list)
    macro_calls: list[dict] = field(default_factory=list)
    parser: TreeSitterParseInfo | None = None
    source_maps: list[dict] = field(default_factory=list)

    @property
    def emitted_files(self):
        return [self.primary] + list(self.generated_files)

    @property
    def has_transforms(self):
        return bool(self.macro_calls or self.generated_files or self.source_maps)

    def to_metadata(self, include_empty=False):
        metadata = {
            "imports": [],
            "vars": [],
            "macros": [],
            "macro_calls": list(self.macro_calls),
        }

        if include_empty or self.parser:
            metadata["parser"] = self.parser.to_dict() if self.parser else None
        if include_empty or self.diagnostics:
            metadata["diagnostics"] = [diagnostic.to_dict() for diagnostic in self.diagnostics]
        if include_empty or self.emitted_files:
            metadata["emitted_files"] = [emitted_file.to_dict() for emitted_file in self.emitted_files]
        if include_empty or self.source_maps:
            metadata["source_maps"] = list(self.source_maps)

        return metadata