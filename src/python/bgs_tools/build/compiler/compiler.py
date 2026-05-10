import os
import subprocess
import shutil

from bgs_tools.build.compiler.constants import DEFAULT_CAPRICA

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