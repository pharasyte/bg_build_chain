import subprocess
import sys
import threading

from bgs_tools.constellation.compile.errors import BGBCompileError
from bgs_tools.constellation.config.constants import DEFAULT_CAPRICA, RED, RESET


def stream_output(pipe, collector, print_output=False):
    for line in iter(pipe.readline, ""):
        collector.append(line)
        if print_output:
            print(line, end="")


def start_output_threads(output_collectors, verbose=False):
    threads = []
    for pipe, collector in output_collectors:
        thread = threading.Thread(target=stream_output, args=(pipe, collector), kwargs={"print_output": verbose})
        threads.append(thread)
        thread.start()
    return threads


def join_threads(threads):
    for thread in threads:
        thread.join()


def process_errors(output):
    error_lines = [line for line in output if "error" in line.lower()]
    for line in error_lines:
        print(f"{RED}{line}{RESET}")


def compile_script(script_path, import_dir, output_dir, executable, verbose=False):
    if isinstance(import_dir, list):
        import_dir = ";".join(import_dir)

    cmd = [executable, script_path, "-f=Starfield_Papyrus_Flags.flg", f"-i={import_dir}", f"-o={output_dir}"]

    if executable == DEFAULT_CAPRICA:
        cmd.insert(1, "--game")
        cmd.insert(2, "starfield")

    if verbose:
        print("Compiling {} with command: {}".format(script_path, " ".join(cmd)))
    else:
        print(f"Compiling {script_path}")

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout_collector, stderr_collector = [], []
    threads = start_output_threads(
        [(process.stdout, stdout_collector), (process.stderr, stderr_collector)],
        verbose=verbose,
    )

    join_threads(threads)
    exit_code = process.wait()

    if exit_code != 0:
        process_errors(stdout_collector + stderr_collector)
        raise BGBCompileError(f"{RED}Error compiling {script_path}{RESET}")


def compile_build_items(build_items, import_dir, output_dir, executable, verbose=False, continue_on_error=False, on_success=None):
    failures = []
    for item in build_items:
        try:
            compile_script(item.staged_path, import_dir, output_dir, executable, verbose=verbose)
        except BGBCompileError as error:
            failures.append((item, error))
            if not continue_on_error:
                sys.stderr.write(f"Error compiling {item.original_path}: {error}\n")
                raise
        else:
            if on_success:
                on_success(item)

    return failures
