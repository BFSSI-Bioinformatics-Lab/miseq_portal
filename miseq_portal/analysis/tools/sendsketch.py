from subprocess import Popen
from pathlib import Path
import pandas as pd
import logging

logger = logging.getLogger('raven')


def run_sendsketch(fwd_reads: Path, rev_reads: Path, outpath: Path) -> Path:
    logger.info(f"Running sendsketch.sh with the following reads:")
    logger.info(f"R1: {fwd_reads}")
    logger.info(f"R2: {rev_reads}")
    logger.info(f"Outpath: {outpath}")
    cmd = f"sendsketch.sh in={fwd_reads} in2={rev_reads} out={outpath} reads=200k overwrite=true"
    p = Popen(cmd, shell=True)
    p.wait()
    return outpath


def read_sendsketch_results(sendsketch_result_file: Path) -> pd.DataFrame:
    # Read raw result file
    df = pd.read_csv(str(sendsketch_result_file), sep='\t', skiprows=2)
    # Drop N/A values
    df = df.dropna(1)
    # Sort by ANI
    df = df.sort_values(by=['Matches', 'WKID'], ascending=False)
    # Add ranking column
    df.insert(0, 'Rank', range(1, len(df) + 1))
    # Set Rank to the index
    df.set_index('Rank')
    return df


def get_top_sendsketch_hit(sendsketch_result_file: Path) -> pd.DataFrame:
    df = read_sendsketch_results(sendsketch_result_file)
    top_hit = df.head(1).reset_index()
    return top_hit
