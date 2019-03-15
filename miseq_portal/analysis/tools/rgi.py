"""
TODO: Implement RGI for AMR detection.

Example cmd:
rgi main -i {input_file} -o {outpath} --clean

RGI also has subcommands to generate visuals (parser, heatmap), create summaries for > 1 samples (tab)
"""
from pathlib import Path
from typing import Optional

from miseq_portal.analysis.models import RGIResult
from miseq_portal.analysis.tools.helpers import run_subprocess


def call_rgi_main(fasta: Path, outdir: Path, sample_id: str) -> Optional[Path]:
    """
    RGI takes an output path with a basename, then creates output files in that directory with that basename
    The --clean parameter removes all temporary output files, leaving only the .json and .txt results
    :param fasta:
    :param outdir:
    :param sample_id:
    :return:
    """
    outpath = outdir / (sample_id + "_RGI_Results")
    cmd = f'rgi main -i {fasta} -o {outpath} --clean'
    run_subprocess(cmd)
    rgi_text_results = outpath.with_suffix(".txt")
    rgi_json_results = outpath.with_suffix(".json")
    try:
        assert rgi_text_results.exists()
        assert rgi_json_results.exists()
    except AssertionError:
        return None
    return outpath


def call_rgi_parser(rgi_json: Path, outdir: Path, sample_id: str):
    """ The RGI parser program generates categorical JSON files for the RGI wheel visualizer """
    outpath = outdir / (sample_id + "RGI_Parsed")
    cmd = f'rgi parser -i {rgi_json} -o {outpath} -t contig'
    run_subprocess(cmd)


def call_rgi_heatmap(rgi_json_dir: Path, outdir: Path, analysis_group_id: str,
                     category: str = 'drug_class', cluster: str = 'samples', display='text'):
    """
    Calls the RGI heatmap program. This takes an input directory containing all RGI .json results to compare.
    Has three adjustable parameters:
        1) --category {drug_class, resistance_mechanism, gene_family}
        2) --cluster {samples, genes, both}
        3) --display {plain, fill, text}
    """
    outpath = outdir / (analysis_group_id + '_heatmap')
    cmd = f'rgi heatmap -i {rgi_json_dir} --category {category} ' \
        f'--cluster {cluster} --display {display} --output {outpath}'
    run_subprocess(cmd)
    eps_out = list(outdir.glob(analysis_group_id + 'heatmap*.eps'))[0]
    png_out = list(outdir.glob(analysis_group_id + 'heatmap*.png'))[0]

    # Make sure output files exists
    try:
        assert eps_out.exists()
        assert png_out.exists()
    except AssertionError:
        return None

    # Remove the .png file, the .eps contains everything we need
    png_out.unlink()
    return eps_out


def gather_rgi_json_results(rgi_result_list: [RGIResult], outdir: Path):
    pass


def parse_rgi_output():
    pass
