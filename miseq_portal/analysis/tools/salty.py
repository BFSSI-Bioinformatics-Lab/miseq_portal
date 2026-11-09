"""
Run NextFlow pipeline to create a Salmonella typing report

"""

import logging
from pathlib import Path
from django.conf import settings
from miseq_portal.analysis.tools.helpers import run_subprocess
import re

logger = logging.getLogger('raven')
nfdir = settings.SALMNF_PATH
basedir = settings.SALMNF_RESOURCES
workdir = settings.SALMNF_WORKING
# TODO: maybe these should be passed from somewhere?
reportname = "summary_report.xlsx"
persample_result_schema = {"mlst": ["mlst", "_mlst.txt"], "serovar": ["serovar", "_serovar.txt"]}


def query_salmonella(assembly_dir: Path, outdir: Path):
    logger.info(f"Submitting Salmonella typing query for {assembly_dir}")
    assembly_input = str(assembly_dir) + "/*.fasta"
    cmd = f"nextflow run {nfdir}/main.nf -c {nfdir}/main.config --basedir {basedir} --genomes '{assembly_input}' --outdir {outdir} -w {workdir}"
    outlog = run_subprocess(cmd, get_stdout=True)
    logger.info(cmd)
    logger.info(outlog)
    report_xlsx = outdir / reportname

    try:
        assert report_xlsx.exists()
    except AssertionError:
        logger.warning(f"Could not find expected Salmonella analysis output file for {assembly_dir}")
        return None

    persample_result_vals = {}
    for result in persample_result_schema:
        for f in (outdir / persample_result_schema[result][0]).glob('*'):
            if f.name.endswith(persample_result_schema[result][1]):
                sample_id = re.sub(f"{persample_result_schema[result][1]}$", '', f.name)
                try:
                    thisval = f.read_text().strip()
                    logger.warning(f"Read Salmonella {result} file for {sample_id}: {thisval}")
                except Exception:
                    logger.warning(f"Could not read Salmonella {result} file for {sample_id}.")
                    thisval = None
                    continue
                if sample_id not in persample_result_vals:
                    persample_result_vals[sample_id] = {result: thisval}
                else:
                    persample_result_vals[sample_id][result] = thisval




    return {'report_xlsx': reportname, 'persample_result_vals': persample_result_vals}


