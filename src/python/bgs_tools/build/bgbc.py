import argparse
import json
import os, sys
import subprocess
import re
import shutil
import threading
import logging

from pathlib import Path

from bgs_tools.build.preprocessor import preprocessor
# from bgs_tools.build.git_handler import git_handler

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = ".\\.dev\\project.json"
DEFAULT_SRCDIR = "src\\papyrus"
DEFAULT_IMPORT  = ['F:\\SteamLibrary\\steamapps\\common\\Starfield\\Data\\Scripts\\Source\\Base']
DEFAULT_OUTPUT = 'F:\\Mod Files\\Starfield\\MO2\\overwrite\\scripts'
DEFAULT_CAPRICA = 'F:\\SteamLibrary\\steamapps\\common\\Starfield\\Data\\scripts\\Source\\User'

RED = '\033[1;31m'
GREEN = '\033[1;32m'
RESET = '\033[0;0m'

CONFIG_DEFAULTS = {
    "compiler_path": os.path.join(SCRIPT_DIR, 'caprica.exe')
}

_VERBOSE = False

class BGBCompileError(Exception): pass

def verbose_print(message):
    if _VERBOSE: 
        print(message)

def verify_or_create_directory(name, directory):
    
    if not os.path.exists(directory):
        dir_exists = False
        while not dir_exists:
            answer = input(f"Directory {directory} does not exist. (c)reate/(m)odify/(e)xit? ")
            if answer == 'e':
                exit()
            elif answer == 'c':
                print(f"Creating directory {directory}")
                os.makedirs(directory)
                dir_exists = True
            elif answer == 'm':
                directory = input(f"Enter {name} directory: ")
                continue
            else:
                raise ValueError(f"Invalid answer {answer}")
    
    return directory

def stream_output(pipe, collector, print_output=False):
    """Handles streaming output from a subprocess."""
    for line in iter(pipe.readline, ''):
        collector.append(line)
        if print_output:
            print(line, end='')  # Stream the output        

def create_and_start_threads(function, args_list):
    """Creates and starts threads for the given function and argument list."""
    threads = []
    for args in args_list:
        thread = threading.Thread(target=function, args=args, kwargs={"print_output": _VERBOSE})
        threads.append(thread)
        thread.start()
    return threads

def join_threads(threads):
    """Waits for all the given threads to complete."""
    for thread in threads:
        thread.join()

def process_errors(output):
    """Processes the output to find and print error lines."""
    error_lines = [line for line in output if "error" in line.lower()]
    for line in error_lines:
        print(f"{RED}{line}{RESET}")

def change_scriptname(input_script, script_path):
    """
    Modifies the ScriptName directive in the given script, prepending the namespace, with
    the namespace being the path to the script file relative to the last "src" directory in
    script_path.

    Example:
        Given a file path "project_root/src/dev/project/libpharasyte/random.psc",
        change the directive:

            "ScriptName "libpharasyte:random" -> "ScriptName dev:project:libpharasyte:random"
    """
    
    # Find the last "src" directory in the path
    script_path_parts = script_path.split(os.sep)

    print(script_path_parts)

    src_index = script_path_parts.index("src")

    if src_index == -1:
        raise ValueError(f"Path {script_path} does not contain a 'src' directory.")
    
    namespace = ":".join(script_path_parts[src_index + 2:-1])

    with open(input_script, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    changed_lines = []

    for line in lines:
        # print(line)
        if "ScriptName" in line:
            print("Found ScriptName")
            scriptname = line.split(" ")[1]
            print(f"Scriptname: {scriptname}")
            scirpt_relname = scriptname.split(":")[-1]
            new_scriptname = f"{namespace}:{scirpt_relname}"
            print(f"Changing {scriptname} to {new_scriptname}")
            line = line.replace(scriptname, new_scriptname)
            print(f"Changed line: {line}")
        
        changed_lines.append(line)

    new_file_text = "".join(changed_lines)

    verbose_print(f"Writing new file text to {script_path}")
    verbose_print(new_file_text)

    with open(script_path, "w", encoding="utf-8") as f:
       f.write(new_file_text)

def copy_includes(includes, output_dir):
    if not includes:
        return
    
    for include in includes:
        # Get children in include directory
        children = [f for f in Path(include).rglob("*")]

        for child in children:
            if child.is_file():
                output_path = os.path.join(output_dir, os.path.relpath(child, include))

                verbose_print(f"Copying {child} to {output_path}")
                verbose_print(f"Creating directory {os.path.dirname(output_path)}")

                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                change_scriptname(child, output_path)
            else:
                # Copy the child's directory structure to the output directory
                output_path = os.path.join(output_dir, os.path.relpath(child, include))
                verbose_print(f"Copying directory {child} to {output_dir}")

                for root, dirs, files in os.walk(child):
                    for file in files:
                        file_path = os.path.join(root, file)
                        output_path = os.path.join(output_dir, os.path.relpath(file_path, include))

                        verbose_print(f"Copying {file_path} to {output_path}")
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        change_scriptname(file_path, output_path)
        
def delete_includes(includes, output_dir):
    if not includes:
        return
    
    # Delete the output directory
    print(f"Deleting {output_dir}")
    shutil.rmtree(output_dir)

def get_project_imports(project_dir, loaded_projects=[os.getcwd()]):
    """
    Recursively builds a list of import directories starting with the given project.

    Projects are expected to have their source files in the "src/papyrus" directory and
    a ".dev/project.json" file containing the project configuration.
    """
    print(f"Getting imports for {project_dir}")
    imports = [os.path.join(project_dir, "src", "papyrus")]
    print(f"Imports: {imports}")

    with open(os.path.join(project_dir, ".dev", "project.json"), "r", encoding="utf-8") as f:
        project_config = json.load(f)

    imports = list(set(imports + project_config.get("import_dir", [])))
    import_projects = project_config.get("import_projects", [])
    if import_projects:
        for project in import_projects:
            if project in loaded_projects:
                print(f"Project {project} already loaded. Skipping.")
                continue

            loaded_projects.append(project)
            imports = list(set(imports + get_project_imports(project, loaded_projects)))

    return imports

def compile_script(script_path, import_dir, output_dir, excecutable, copy_source_to=None, base_path=None):

    global _VERBOSE

    if type(import_dir) is list:
        import_dir = ";".join(import_dir)

    cmd = [excecutable, script_path, "-f=Starfield_Papyrus_Flags.flg", f"-i={import_dir}", f"-o={output_dir}"]

    if excecutable == DEFAULT_CAPRICA:
        cmd.insert(1, "--game")
        cmd.insert(2, "starfield")

    if _VERBOSE:
        print("Compiling {} with command: {}".format(script_path, " ".join(cmd)))
    else:
        print(f"Compiling {script_path}")

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    stdout_collector, stderr_collector = [], []

    output_collectors = [
        (process.stdout, stdout_collector), 
        (process.stderr, stderr_collector)
    ]

    # Create and start threads for streaming output
    threads = create_and_start_threads(stream_output, output_collectors)

    join_threads(threads)

    exit_code = process.wait()

    if exit_code != 0:
        process_errors(stdout_collector + stderr_collector)
        raise BGBCompileError(f"{RED}Error compiling {script_path}{RESET}")

    if copy_source_to:

        if base_path:
            # If base path is specified we need to mirror the directory structure
            # at the destination.
            relative_path = os.path.relpath(script_path, base_path)
            verbose_print(f"Using directory structure at {copy_source_to} (Base Path: {base_path}, Relative Path: {relative_path})")

            copy_source_to = os.path.join(copy_source_to, relative_path)
            os.makedirs(os.path.dirname(copy_source_to), exist_ok=True)

        verbose_print(f"Copying {script_path} to {copy_source_to}")
        shutil.copy(script_path, copy_source_to)

def load_config(config_name):
    if not os.path.exists(f"{config_name}"):
        return None

    with open(f"{config_name}", "r", encoding="utf-8") as f:
        config = json.load(f)

    return config

def save_config(config_path, config):
    with open(f"{config_path}", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def merge_config(args, config={}):

    arg_options = [v for v in args.__dir__() if not v.startswith("_")]

    for arg_name in arg_options:
        if getattr(args, arg_name):
            config[arg_name] = getattr(args, arg_name)

    return config

def recursive_copy(src, dest):
    if os.path.isdir(src):
        shutil.copytree(src, dest, dirs_exist_ok=True)
    else:
        shutil.copy(src, dest)

def main():

    global _VERBOSE

    # TODO: Move this to pharasyte.config.arguments
    parser = argparse.ArgumentParser(description='Wrapper for Caprica compiler.')
    parser.add_argument('--verbose', help='Verbose output', action='store_true')
    parser.add_argument('--file', help='Single file to compile')
    parser.add_argument('--folder', default=DEFAULT_SRCDIR, help='Folder to search for scripts')
    parser.add_argument('--filter', help='Filter for file selection (regex or substring)')
    parser.add_argument('--no-recurse', help='Don\'t recursively search for scripts in folder', action='store_true')
    parser.add_argument('--compiler-mode', help='Compiler to use (default is caprica)', default='caprica', choices=['caprica', 'ck'])
    parser.add_argument('--compiler-path', help='Path to the compiler')
    parser.add_argument('--compiler-args', help='Additional arguments for the compiler')
    parser.add_argument('--import-dir', help='Import directory')
    parser.add_argument('--output-dir', help='Output directory')
    parser.add_argument('--caprica-dir', help='Caprica directory')
    parser.add_argument('--force-defaults', help='Use default directories', action='store_true')
    parser.add_argument('--save-config', help='Save current directories as defaults', action='store_true')
    parser.add_argument('--copy-source-to', help='Copy source files to specified directory')
    parser.add_argument('--assets-dir', help='Assets directory')
    parser.add_argument('--fetch-assets', help='Fetch the listed assets from the game directory', nargs='+')
    parser.add_argument('--continue-on-error', help='Continue compiling after an error', action='store_true')
    parser.add_argument('--disable-preprocessor', help='Disable the preprocessor', action='store_true', default=False)

    DRY_RUN_LEVELS = ['collectFiles', 'preprocess']
    parser.add_argument('--dry-run-level', help='Dry run level', choices=DRY_RUN_LEVELS)

    parser.add_argument('--debug-preprocessor', help='Debug the preprocessor', action='store_true')
    parser.add_argument('--build-dir', help='Build directory', default=os.path.join(os.getcwd(), "build"))

    parser.add_argument(
        '--config',
        default=DEFAULT_CONFIG,
        help="Load the specified config if it exists. If --save-config is specified, the current directories will be saved as this config."
    )
    # End of pharasyte.config.arguments

    #TODO: Move this to pharasyte.config.resolver
    args = parser.parse_args()

    import_dir = DEFAULT_IMPORT
    output_dir = DEFAULT_OUTPUT
    copy_source_to = None

    if args.config:
        config = load_config(args.config)
        if not config and not args.save_config:
            print(f"Config {args.config} does not exist. Use --save-config to create it.")
            exit()
    else:
        config = {}

    config = merge_config(args, config)
        
    if args.save_config:
        save_config(args.config, config)

    _VERBOSE = args.verbose

    if _VERBOSE:
        pretty_config = json.dumps(config, indent=4)
        print(f"Using config:\n{pretty_config}")

    project_namespace = config.get("project_namespace", None)
    preprocessor_imports = config.get("preprocessor_imports", [])
    
    if type(preprocessor_imports) is str:
        preprocessor_imports = [preprocessor_imports]
    elif type(preprocessor_imports) is not list:
        print("Preprocessor imports must be a list of directories.")
        exit(1)
        
    import_dir = config.get("import_dir", import_dir)

    if not isinstance(import_dir, list):
        import_dir = [import_dir]

    import_projects = config.get("import_projects", [])

    print(f"Import projects: {import_projects}")

    for project in import_projects:
        if isinstance(project, dict):
            project = project["path"]
        import_dir = list(set(import_dir + get_project_imports(project)))

    print(f"Importing from {import_dir}")

    build_dir = os.path.abspath(args.build_dir if args.build_dir else config.get("build_dir", "build"))
    shutil.rmtree(build_dir, ignore_errors=True)
    
    os.makedirs(build_dir, exist_ok=True)
    print(f"{GREEN}Build directory: {build_dir}{RESET}")

    output_dir = verify_or_create_directory("output", config.get("output_dir", output_dir))
    copy_source_to = config.get("copy_source_to", copy_source_to)
    assets_dir = config.get("assets_dir", None)
    assets = config.get("assets", [])
    extras = config.get("extras", [])

    excecutable = config.get("compiler_path", CONFIG_DEFAULTS["compiler_path"])

    print(f"Using compiler at {excecutable}")

    if not os.path.isfile(excecutable):
        print(f"Compiler not found at {excecutable}.")
        exit(1)
    # End of pharasyte.config.resolver

    # git_handler.build_commit()

    print(f"args: {args}")
    if args.debug_preprocessor:
        print("Debugging preprocessor.")
        if not args.file:
            print("Please specify a file to debug the preprocessor.")
            exit(1)
        else:
            preprocessor.preprocess_file(args.file, output_dir)
            exit(0)
    elif args.file:
        file_path = os.path.abspath(args.file)
        file_dir  = os.path.dirname(file_path)
        os.chdir(file_dir)

        # copy_includes(includes, includes_output_dir)
        compile_script(file_path, import_dir, output_dir, excecutable, copy_source_to)
        # delete_includes(includes, includes_output_dir)
    elif args.folder:

        abs_folder = os.path.abspath(args.folder)
        os.chdir(abs_folder)

        print(f"Abs folder: {abs_folder}")

        

        # includes_output_dir = os.path.join(abs_folder, project_namespace.replace(":", "\\"), "inc")
        # copy_includes(includes, includes_output_dir)

        print(f"Filter: {args.filter}")

        pattern = re.compile(args.filter) if args.filter else None
        print(f"pattern: {pattern}")

        verbose_print(f"Searching for scripts in {abs_folder}")
        
        if args.no_recurse:
            files = [f for f in Path(abs_folder).glob("*.psc")]
        else:
            files = [f for f in Path(abs_folder).rglob("*.psc")]

        verbose_print(f"Found {len(files)} scripts:\n{files}")

        for file in files:
            file_abspath = os.path.abspath(str(file))

            if pattern:
                print(f"{RED}Checking {file}: pattern.search({file.name}) = {pattern.search(file_abspath)}{RESET}")
                
            if (not pattern) or (not pattern.search(file_abspath)):
                try:
                    compile_script(file_abspath, import_dir, output_dir, excecutable, copy_source_to, base_path=abs_folder)
                except BGBCompileError as e:
                    if not args.continue_on_error:
                        sys.stderr.write(f"Error compiling {file}: {e}\n")
                        exit(1)

        for extra in extras:
            extra_src = extra.get("src")
            extra_dest = extra.get("dest")
            remove_dest = extra.get("remove_dest", False)
            if extra_src and extra_dest:
                print(f"Copying extra from {extra_src} to {extra_dest}")
                if remove_dest and os.path.exists(extra_dest):
                    print(f"Removing existing destination {extra_dest}")
                    if os.path.isdir(extra_dest):
                        shutil.rmtree(extra_dest)
                    else:
                        os.remove(extra_dest)

                recursive_copy(extra_src, extra_dest)

        for asset_path in assets:
            if os.path.exists(asset_path):
                if not os.path.exists(assets_dir):
                    os.makedirs(assets_dir, exist_ok=True)
                print(f"Copying {asset_path} to {assets_dir}")
                shutil.copy(asset_path, assets_dir)
            else:
                print(f"Asset {asset_path} does not exist. Skipping.")
        
        # delete_includes(includes, includes_output_dir)
    else:
        print("Please specify either --file or --folder.")

if __name__ == "__main__":
    main()
