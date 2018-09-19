import os
from pathlib import Path
from subprocess import Popen, PIPE


def run_subprocess(cmd: str, get_stdout=False):
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


def remove_dir_files(outdir: Path):
    to_delete = list(outdir.glob("*.*"))
    for f in to_delete:
        os.remove(str(f))
