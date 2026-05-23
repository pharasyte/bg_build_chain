from dataclasses import dataclass


class DiagnosticSeverity:
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class SourcePosition:
    line: int
    column: int

    def to_dict(self):
        return {"line": self.line, "column": self.column}


@dataclass(frozen=True)
class SourceSpan:
    start: SourcePosition
    end: SourcePosition

    def to_dict(self):
        return {"start": self.start.to_dict(), "end": self.end.to_dict()}


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    message: str
    file_path: str | None = None
    span: SourceSpan | None = None

    def to_dict(self):
        data = {
            "severity": self.severity,
            "message": self.message,
        }
        if self.file_path:
            data["file_path"] = self.file_path
        if self.span:
            data["span"] = self.span.to_dict()
        return data


class TranspilerError(Exception):
    def __init__(self, diagnostics):
        self.diagnostics = list(diagnostics)
        message = "; ".join(diagnostic.message for diagnostic in self.diagnostics)
        super().__init__(message)