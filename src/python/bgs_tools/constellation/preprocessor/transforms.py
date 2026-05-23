import re

from bgs_tools.constellation.preprocessor.diagnostics import Diagnostic, DiagnosticSeverity, TranspilerError


GET_SELF_PATTERN = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_:]*\s+Function\s+GetSelf\(\)\s+Global\b", re.IGNORECASE | re.MULTILINE)


def render_link_quest_function(script_name, quest_id, plugin_file):
    return (
        f"{script_name} Function GetSelf() Global\n"
        f"    Int QID = {quest_id}\n"
        f"    String PF = \"{plugin_file}\"\n\n"
        f"    Return Game.GetFormFromFile(QID, PF) as {script_name}\n"
        "EndFunction\n"
    )


def apply_link_quest_transform(source_file):
    directives = source_file.directives
    macro_calls = []

    if not directives:
        return macro_calls

    if len(directives) != 1:
        raise TranspilerError(
            [
                Diagnostic(
                    DiagnosticSeverity.ERROR,
                    "Only one $LinkQuest(...) directive is supported per file in the current implementation.",
                    file_path=source_file.file_path,
                )
            ]
        )

    if not source_file.script_name:
        raise TranspilerError(
            [
                Diagnostic(
                    DiagnosticSeverity.ERROR,
                    "Could not find a ScriptName declaration for $LinkQuest preprocessing.",
                    file_path=source_file.file_path,
                )
            ]
        )

    directive = directives[0]
    if GET_SELF_PATTERN.search(source_file.body_text()):
        raise TranspilerError(
            [
                Diagnostic(
                    DiagnosticSeverity.ERROR,
                    "$LinkQuest would generate GetSelf(), but the file already defines a global GetSelf() function.",
                    file_path=source_file.file_path,
                )
            ]
        )

    source_file.generated_functions.append(render_link_quest_function(source_file.script_name, directive.quest_id, directive.plugin_file))
    macro_calls.append(
        {
            "name": "LinkQuest",
            "args": [directive.plugin_file, directive.quest_id],
            "plugin_file": directive.plugin_file,
            "script_name": source_file.script_name,
            "line": directive.line_number,
        }
    )
    return macro_calls


def apply_transforms(source_file, context=None):
    _ = context
    macro_calls = []
    macro_calls.extend(apply_link_quest_transform(source_file))
    return macro_calls