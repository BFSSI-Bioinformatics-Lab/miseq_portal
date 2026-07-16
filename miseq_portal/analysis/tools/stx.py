"""
Run NextFlow pipeline to create an stx report

"""

import logging
from pathlib import Path
from django.conf import settings
from miseq_portal.analysis.tools.helpers import run_subprocess
import re

logger = logging.getLogger('raven')
nfdir = settings.STXNF_PATH
basedir = settings.STXNF_DB
workdir = settings.STXNF_WORKING
# TODO: maybe these should be passed from somewhere?
reportdir = "report"
reportname = "summary_report.xlsx"
persample_result_schema = {"kma": ["kma", ".res"], "stxtyper": ["stxtyper", "_stxtyper.tsv"], "stx1blast": ["blast_processed", "_stx1_properpairs.tsv"], "stx2blast": ["blast_processed", "_stx2_properpairs.tsv"]}
perstx_result_schema = {"motif": ["motifs", "_aligned_motif.txt"], "alignment": ["alignments", "_aligned.fasta"], "tree": ["trees", "_aligned.tree"]}


def query_stx(read_dir: Path, outdir: Path, assembly_dir: Path = None, samples_str: str = None, coverage_str: str = None):
    logger.info(f"Submitting stx query for {read_dir}")
    read_input = str(read_dir) + "/*_R{1,2}.fastq.gz"
    assembly_input = str(assembly_dir) + "/*.fasta"
    cmd = f"nextflow run {nfdir}/main.nf -c {nfdir}/main.config --basedir {basedir} --reads '{read_input}' --genomes '{assembly_input}' --outdir {outdir} -w {workdir}"
    if samples_str:
        cmd += f" --samplenames '{samples_str}'"
    if coverage_str:
        cmd += f" --coverage '{coverage_str}'"
    outlog = run_subprocess(cmd, get_stdout=True)
    logger.info(cmd)
    logger.info(outlog)
    report_xlsx = outdir / reportdir / reportname

    try:
        assert report_xlsx.exists()
    except AssertionError:
        logger.warning(f"Could not find expected stx result files for {read_dir}")
        return None

    persample_results = {}
    for result in persample_result_schema:
        for f in (outdir / persample_result_schema[result][0]).glob('*'):
            if f.name.endswith(persample_result_schema[result][1]):
                sample_id = re.sub(f"{persample_result_schema[result][1]}$", '', f.name)
                fpath = persample_result_schema[result][0] + "/" + f.name
                if sample_id not in persample_results:
                    persample_results[sample_id] = {result: fpath}
                else:
                    persample_results[sample_id][result] = fpath

    persample_result_vals = {}
    for sample in persample_results:
        singlereport = outdir / reportdir / f"{sample}_row.tsv"
        if singlereport.exists():
            try:
                with singlereport.open('r', encoding='utf-8') as fh:
                    lines = [l.rstrip('\n') for l in fh.readlines()]
            except Exception:
                logger.warning(f"Could not read singlereport for {sample}: {singlereport}")
                continue

            if len(lines) != 2:
                logger.warning(f"Unexpected singlereport format for {sample}: {singlereport}")
                continue

            headers = lines[0].split('\t')
            values = lines[1].split('\t')

            if len(headers) != len(values):
                logger.warning(f"Header/value count mismatch in {singlereport}: {len(headers)} headers vs {len(values)} values")
                continue

            # Zip safely: extra headers or values will be truncated
            rowdict = dict(zip(headers, values))
            persample_result_vals[sample] = rowdict

    perstx_results = {}
    for result in perstx_result_schema:
        for f in (outdir / perstx_result_schema[result][0]).glob('*'):
            if f.name.endswith(perstx_result_schema[result][1]):
                idandstx = re.sub(f"{perstx_result_schema[result][1]}$", '', f.name)
                matched_sample_id = None
                matched_geneandcontig = None

                for s_id in persample_results:
                    if idandstx.startswith(f"{s_id}_"):
                        matched_sample_id = s_id
                        matched_geneandcontig = re.sub(f"^{s_id}_", '', idandstx)
                        break

                if not matched_sample_id or not matched_geneandcontig:
                    logger.warning(f"Skipping unmatched STX gene result file: {f.name}")
                    continue

                fpath = perstx_result_schema[result][0] + "/" + f.name
                if matched_sample_id not in perstx_results:
                    perstx_results[matched_sample_id] = {matched_geneandcontig: {result: fpath}}
                elif matched_geneandcontig not in perstx_results[matched_sample_id]:
                    perstx_results[matched_sample_id][matched_geneandcontig] = {result: fpath}
                else:
                    perstx_results[matched_sample_id][matched_geneandcontig][result] = fpath


    return {'report_xlsx': reportdir + "/" + reportname, 'persample_results': persample_results, 'persample_result_vals': persample_result_vals, 'perstx_results': perstx_results}


