import importlib
import os

from bgs_tools.constellation.preprocessor.nodes import TreeSitterParseInfo


DEFAULT_LANGUAGE_MODULE = "tree_sitter_papyrus"


def _coerce_language(tree_sitter_module, language_value):
    language_class = getattr(tree_sitter_module, "Language", None)
    if language_class is None or isinstance(language_value, language_class):
        return language_value

    try:
        return language_class(language_value)
    except TypeError:
        return language_value


def _assign_language(parser, language):
    if hasattr(parser, "set_language"):
        parser.set_language(language)
    else:
        parser.language = language


def parse_with_tree_sitter(source_text, language_module_name=None):
    language_module_name = language_module_name or os.environ.get("BGB_TREE_SITTER_PAPYRUS_MODULE", DEFAULT_LANGUAGE_MODULE)

    try:
        tree_sitter = importlib.import_module("tree_sitter")
    except ImportError:
        return TreeSitterParseInfo(available=False, language_module=language_module_name, reason="tree_sitter is not installed")

    try:
        language_module = importlib.import_module(language_module_name)
    except ImportError:
        return TreeSitterParseInfo(
            available=False,
            language_module=language_module_name,
            reason=f"{language_module_name} is not installed",
        )

    language_factory = getattr(language_module, "language", None)
    if not language_factory:
        return TreeSitterParseInfo(
            available=False,
            language_module=language_module_name,
            reason=f"{language_module_name} does not expose language()",
        )

    parser = tree_sitter.Parser()
    language = _coerce_language(tree_sitter, language_factory())
    _assign_language(parser, language)

    tree = parser.parse(source_text.encode("utf-8"))
    root_node = tree.root_node
    return TreeSitterParseInfo(
        available=True,
        root_kind=root_node.type,
        has_error=bool(root_node.has_error),
        language_module=language_module_name,
    )