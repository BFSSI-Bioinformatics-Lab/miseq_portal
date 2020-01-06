"""
Generic functions for miseq_portal tools to call
"""

import os
from pathlib import Path
from subprocess import Popen, PIPE


def run_subprocess(cmd: str, get_stdout=False, cwd=None) -> str:
    """
    Wrapper for subprocess.Popen()
    :param cmd: String containing command to pass to system
    :param get_stdout: Flag to grab stdout/stderr and return as str
    :param cwd: Path to desired working dir
    :return: If get_stdout, returns str of stdout/stderr, else doesn't return anything
    """
    if get_stdout:
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, cwd=cwd)
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
        p = Popen(cmd, shell=True, cwd=cwd)
        p.wait()


def remove_fastq_and_bam_files(target_directory: Path):
    """
    Delete all of the files in a given directory
    :param target_directory: Path to directory to delete files in
    """
    to_delete = list(target_directory.glob("*.bam")) + list(target_directory.glob("*.fastq.gz")) + list(
        target_directory.glob("*.bai"))
    for f in to_delete:
        os.remove(str(f))
