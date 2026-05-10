import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1]
BGS_TOOLS_DIR = PACKAGE_DIR.parent
LEGACY_BUILD_DIR = BGS_TOOLS_DIR / "build"

DEFAULT_CONFIG = ".\\.dev\\project.json"
DEFAULT_SRCDIR = "src\\papyrus"
DEFAULT_IMPORT = ["F:\\SteamLibrary\\steamapps\\common\\Starfield\\Data\\Scripts\\Source\\Base"]
DEFAULT_OUTPUT = "F:\\Mod Files\\Starfield\\MO2\\overwrite\\scripts"
DEFAULT_CAPRICA = "F:\\SteamLibrary\\steamapps\\common\\Starfield\\Data\\scripts\\Source\\User"

CONFIG_DEFAULTS = {
    "compiler_path": os.path.join(str(LEGACY_BUILD_DIR), "caprica.exe"),
}
