import logging
from pathlib import Path
from subprocess import Popen

import pandas as pd

from miseq_portal.analysis.models import SendsketchResult
from miseq_portal.miseq_viewer.models import Sample

logger = logging.getLogger('raven')


def run_sendsketch(fwd_reads: Path, rev_reads: Path, outpath: Path) -> Path:
    """
    System call to sendsketch.sh to determine closest taxonomy hit on RefSeq
    :param fwd_reads: Path to forward reads (.fastq.gz)
    :param rev_reads: Path to reverse reads (.fastq.gz)
    :param outpath: Desired path to output file
    :return: Path to output file
    """
    logger.info(f"Running sendsketch.sh with the following reads:")
    logger.info(f"R1: {fwd_reads}")
    logger.info(f"R2: {rev_reads}")
    logger.info(f"Outpath: {outpath}")
    cmd = f"sendsketch.sh in={fwd_reads} in2={rev_reads} out={outpath} reads=200k overwrite=true"
    p = Popen(cmd, shell=True)
    p.wait()
    return outpath


def read_sendsketch_results(sendsketch_result_file: Path) -> pd.DataFrame:
    """
    Parses output file from sendsketch.sh into a Dataframe, adds a rank column and sorts the 'best' hit to the top
    :param sendsketch_result_file: Path to sendsketch.sh output file
    :return: Pandas dataframe containing parsed and sorted sendsketch.sh results
    """
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
    """
    Grab the top hit from a sendsketch result file. See read_sendsketch_results to see how the top hit is determined.
    :param sendsketch_result_file: Path to sendsketch.sh output file
    :return: Dataframe containing a single row of the top hit from sendsketch.sh
    """
    df = read_sendsketch_results(sendsketch_result_file)
    top_hit = df.head(1).reset_index()
    return top_hit


def sendsketch_tophit_pipeline(fwd_reads: Path, rev_reads: Path, outpath: Path) -> pd.DataFrame:
    sendsketch_result_file = run_sendsketch(fwd_reads=fwd_reads, rev_reads=rev_reads, outpath=outpath)
    top_hit = get_top_sendsketch_hit(sendsketch_result_file)
    return top_hit


def create_sendsketch_result_object(sendsketch_tophit_df: pd.DataFrame, sample_object: Sample) -> SendsketchResult:
    sendsketch_object, sendsketch_object_created = SendsketchResult.objects.get_or_create(sample_id=sample_object)

    if sendsketch_object_created:
        logger.info("Creating new SendSketch results object")
    else:
        logger.info("Overwriting existing SendSketch results object")

    # Get top hit df and populate the database with results
    try:
        sendsketch_object.top_ANI = sendsketch_tophit_df['ANI'][0]
        sendsketch_object.top_Contam = sendsketch_tophit_df['Contam'][0]
        sendsketch_object.top_gSize = sendsketch_tophit_df['gSize'][0]
        sendsketch_object.top_taxName = sendsketch_tophit_df['taxName'][0]
        sendsketch_object.top_TaxID = sendsketch_tophit_df['TaxID'][0]
    except:
        sendsketch_object.top_ANI = None
        sendsketch_object.top_Contam = None
        sendsketch_object.top_gSize = None
        sendsketch_object.top_taxName = None
        sendsketch_object.top_TaxID = None
    return sendsketch_object
