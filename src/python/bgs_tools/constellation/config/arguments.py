import argparse
import os

from bgs_tools.constellation.config.constants import DEFAULT_CONFIG, DEFAULT_SRCDIR


DRY_RUN_LEVELS = ["collectFiles", "preprocess"]


def build_parser():
    parser = argparse.ArgumentParser(description="Wrapper for Caprica compiler.")
    parser.add_argument("--verbose", help="Verbose output", action="store_true")
    parser.add_argument("--file", help="Single file to compile")
    parser.add_argument("--folder", default=DEFAULT_SRCDIR, help="Folder to search for scripts")
    parser.add_argument("--filter", help="Filter for file selection (regex or substring)")
    parser.add_argument("--no-recurse", help="Don't recursively search for scripts in folder", action="store_true")
    parser.add_argument("--compiler-mode", help="Compiler to use (default is caprica)", default="caprica", choices=["caprica", "ck"])
    parser.add_argument("--compiler-path", help="Path to the compiler")
    parser.add_argument("--compiler-args", help="Additional arguments for the compiler")
    parser.add_argument("--import-dir", help="Import directory")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("--caprica-dir", help="Caprica directory")
    parser.add_argument("--force-defaults", help="Use default directories", action="store_true")
    parser.add_argument("--save-config", help="Save current directories as defaults", action="store_true")
    parser.add_argument("--copy-source-to", help="Copy source files to specified directory")
    parser.add_argument("--assets-dir", help="Assets directory")
    parser.add_argument("--fetch-assets", help="Fetch the listed assets from the game directory", nargs="+")
    parser.add_argument("--continue-on-error", help="Continue compiling after an error", action="store_true")
    parser.add_argument("--disable-preprocessor", help="Disable the preprocessor", action="store_true", default=False)
    parser.add_argument("--dry-run-level", help="Dry run level", choices=DRY_RUN_LEVELS)
    parser.add_argument("--debug-preprocessor", help="Debug the preprocessor", action="store_true")
    parser.add_argument("--build-dir", help="Build directory", default=os.path.join(os.getcwd(), "build"))
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help="Load the specified config if it exists. If --save-config is specified, the current directories will be saved as this config.",
    )
    return parser
