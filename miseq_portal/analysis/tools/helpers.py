"""
Generic functions for miseq_portal tools to call
"""

import os
from pathlib import Path
from subprocess import Popen, PIPE


def run_subprocess(cmd: str, get_stdout=False) -> str:
    """
    Wrapper for subprocess.Popen()
    :param cmd: String containing command to pass to system
    :param get_stdout: Flag to grab stdout/stderr and return as str
    :return: If get_stdout, returns str of stdout/stderr, else doesn't return anything
    """
    if get_stdout:
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        out = out.decode().strip()
        err = err.decode().strip()
        if out != "":
            return out
        elif err != "":
            return err
        else:
            return ""
    else:
        p = Popen(cmd, shell=True)
        p.wait()


def remove_dir_files(target_directory: Path):
    """
    Delete all of the files in a given directory
    :param target_directory: Path to directory to delete files in
    """
    to_delete = list(target_directory.glob("*.*"))
    for f in to_delete:
        os.remove(str(f))
