import re
from pathlib import Path

from bgs_tools.constellation.preprocessor.nodes import LinkQuestDirective, SourceFile


SCRIPT_NAME_PATTERN = re.compile(r"^\s*ScriptName\s+([A-Za-z_][A-Za-z0-9_:]*)\b", re.IGNORECASE | re.MULTILINE)
LINK_QUEST_PATTERN = re.compile(r"^\s*\$LinkQuest\s*\(\s*([^,]+?)\s*,\s*([^\)]+?)\s*\)\s*$")


def parse_script_name(source_text):
    match = SCRIPT_NAME_PATTERN.search(source_text)
    return match.group(1) if match else None


def normalize_plugin_file(plugin_arg):
    plugin_arg = plugin_arg.strip()
    if len(plugin_arg) >= 2 and plugin_arg[0] == plugin_arg[-1] and plugin_arg[0] in {'"', "'"}:
        plugin_arg = plugin_arg[1:-1]

    return Path(plugin_arg).name


def lift_source_file(source_text, file_path, parser_info=None):
    directives = []
    body_lines = []

    for line_number, line in enumerate(source_text.splitlines(keepends=True), start=1):
        match = LINK_QUEST_PATTERN.match(line)
        if match:
            directives.append(
                LinkQuestDirective(
                    plugin_file=normalize_plugin_file(match.group(1)),
                    quest_id=match.group(2).strip(),
                    line_number=line_number,
                    raw_text=line,
                )
            )
            continue

        body_lines.append(line)

    return SourceFile(
        file_path=file_path,
        source_text=source_text,
        body_lines=body_lines,
        script_name=parse_script_name(source_text),
        directives=directives,
        parser=parser_info,
    )