"""
Run NextFlow pipeline to create an stx report

"""

import logging
from pathlib import Path
from django.conf import settings
from miseq_portal.analysis.tools.helpers import run_subprocess

logger = logging.getLogger('raven')
nfdir = settings.STXNF_PATH
basedir = settings.STXNF_DB
workdir = settings.STXNF_WORKING
subdir = "report" # maybe this should be passed from somewhere?

def query_stx(read_dir: Path, outdir: Path, assembly: Path = None):
    logger.info(f"Submitting stx query for {read_dir}")
    read_input = read_dir / "*_R{1,2}.fastq.gz"
    cmd = f'nextflow run {nfdir}/main.nf -c {nfdir}/main.config --basedir {basedir} --reads {read_input} --outdir {outdir} -w {workdir}'
    if assembly:
        cmd = cmd + " --genomes " + str(assembly)

    outlog = run_subprocess(cmd, get_stdout=True)
    logger.info(cmd)
    logger.info(outlog)
    filename = read_dir.name + "_report.pdf"
    report_pdf = outdir / subdir / filename

    try:
        assert report_pdf.exists()
    except AssertionError:
        logger.warning(f"Could not find expected stx result files for {read_dir}")
        return None
    return {'subdir': subdir, 'name': filename}


