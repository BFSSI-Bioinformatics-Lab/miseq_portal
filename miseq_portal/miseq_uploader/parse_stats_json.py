import json
import pandas as pd
from pathlib import Path


def stats_json_to_df(stats_json: Path) -> pd.DataFrame:
    sample_stats_dict = read_stats_json(stats_json)
    stats_df = stats_dict_to_df(sample_stats_dict)
    return stats_df


def read_stats_json(stats_json: Path) -> dict:
    """
    :param stats_json: Path to Stats.json file from the MiSeq Log folder
    :return: dictionary containing stats on each sample: key is sample_id
    """
    with open(str(stats_json)) as f:
        data = json.loads(f.read())

    sample_json = data['ConversionResults'][0]['DemuxResults']
    sample_stats_dict = dict()
    for sample in sample_json:
        tmp_stats_dict = dict()
        sample_id = sample['SampleId']

        # Basic information on sample
        tmp_stats_dict['SampleName'] = sample['SampleName']
        tmp_stats_dict['NumberReads'] = sample['NumberReads']
        tmp_stats_dict['Yield'] = sample['Yield']

        # ReadMetrics per read (R1, R2)
        tmp_stats_dict['R1_QualityScoreSum'] = sample['ReadMetrics'][0]['QualityScoreSum']
        tmp_stats_dict['R1_TrimmedBases'] = sample['ReadMetrics'][0]['TrimmedBases']
        tmp_stats_dict['R1_Yield'] = sample['ReadMetrics'][0]['Yield']
        tmp_stats_dict['R1_YieldQ30'] = sample['ReadMetrics'][0]['YieldQ30']
        tmp_stats_dict['R2_QualityScoreSum'] = sample['ReadMetrics'][1]['QualityScoreSum']
        tmp_stats_dict['R2_TrimmedBases'] = sample['ReadMetrics'][1]['TrimmedBases']
        tmp_stats_dict['R2_Yield'] = sample['ReadMetrics'][1]['Yield']
        tmp_stats_dict['R2_YieldQ30'] = sample['ReadMetrics'][1]['YieldQ30']
        sample_stats_dict[sample_id] = tmp_stats_dict
    return sample_stats_dict


def stats_dict_to_df(sample_stats_dict: dict) -> pd.DataFrame:
    df = pd.DataFrame.from_dict(sample_stats_dict).transpose()
    df.reset_index(drop=False, inplace=True)
    df.rename(columns={'index': 'sample_id'}, inplace=True)
    return df
