import os
import platform
import subprocess
import sys
import time

from logless import logged, get_logger, flush_buffers

logging = get_logger("runnow")


def _grep(full_text, match_with, insensitive=True, fn=any):
    lines = full_text.splitlines()
    if isinstance(match_with, str):
        match_with = [match_with]
    if insensitive:
        return "\n".join(
            [l for l in lines if fn([m.lower() in l.lower() for m in match_with])]
        )
    else:
        return "\n".join([l for l in lines if fn([m in l for m in match_with])])


@logged("running command: {'(hidden)' if hide else cmd}")
def run(
    cmd: str,
    working_dir=None,
    echo=True,
    raise_error=True,
    log_file_path: str = None,
    shell=True,
    daemon=False,
    hide=False,
    cwd=None,
    wait_test=None,
    wait_max=None,
):
    """ Run a CLI command and return a tuple: (return_code, output_text) """
    loglines = []
    if working_dir:
        prev_working_dir = os.getcwd()
        os.chdir(working_dir)
    if isinstance(cmd, list):
        pass  # cmd = " ".join(cmd)
    elif platform.system() == "Windows":
        cmd = " ".join(cmd.split())
    else:
        cmd = cmd.replace("\n", " \\\n")
    proc = subprocess.Popen(
        cmd,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        universal_newlines=True,
        shell=shell,
        cwd=cwd,
    )
    start_time = time.time()
    if working_dir:
        os.chdir(prev_working_dir)
    if log_file_path:
        logfile = open(log_file_path, "w", encoding="utf-8")
    else:
        logfile = None
    line = proc.stdout.readline()
    flush_buffers()
    while (proc.poll() is None) or line:
        if daemon:
            if wait_max is None and wait_test is None:
                logging.info("Daemon process is launched. Returning...")
                break
            if callable(wait_test) and wait_test(line):
                logging.info(f"Returning. Wait test passed: {line}")
                break
            if wait_max and time.time() >= start_time + wait_max:
                logging.info(
                    f"{line}\nMax timeout expired (wait_max={wait_max})."
                    f" Returning..."
                )
                if callable(wait_test):
                    return_code = 1
                else:
                    return_code = 0
                break
        if line:
            line = line.rstrip()
            loglines.append(line)
            if echo:
                for l in line.splitlines():
                    sys.stdout.write(l.rstrip() + "\r\n")
            if logfile:
                logfile.write(line + "\n")
        else:
            time.sleep(0.5)  # Sleep half a second if no new output
        line = proc.stdout.readline()
    flush_buffers()
    output_text = chr(10).join(loglines)
    if logfile:
        logfile.close()
    if not proc:
        return_code = None
        raise RuntimeError(f"Command failed: {cmd}\n\n")
    else:
        return_code = proc.returncode
        if (
            return_code != 0
            and raise_error
            and ((daemon == False) or (return_code is not None))
        ):
            err_msg = f"Command failed (exit code {return_code}): {cmd}"
            if not echo:
                print_str = output_text
            elif len(output_text.splitlines()) > 10:
                print_str = _grep(
                    output_text, ["error", "exception", "warning", "fail", "deprecat"]
                )
            else:
                print_str = ""
            if print_str:
                err_msg += (
                    f"{'-' * 80}\n"
                    f"SCRIPT ERRORS:\n{'-' * 80}\n"
                    f"{print_str}\n{'-' * 80}\n"
                    f"END OF SCRIPT OUTPUT\n{'-' * 80}"
                )
            raise RuntimeError(err_msg)
    return return_code, output_text
