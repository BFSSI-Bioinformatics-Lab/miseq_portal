import pandas as pd
from pathlib import Path


# TODO: Query Sample_IDs against database to ensure they don't already exist
# TODO: Query Sample_Project to see if it already exists; if not, create new one


def validate_samplesheet_header(header: list) -> bool:
    """
    Validates that column names match expected values
    :param header: List of column names
    :return: True if header meets all expected values, False if not
    """
    expected_header = [
        'Sample_ID',
        'Sample_Name',
        'Sample_Plate',
        'Sample_Well',
        'I7_Index_ID',
        'index',
        'I5_Index_ID',
        'index2',
        'Sample_Project',
        'Description'
    ]
    return set(header) == set(expected_header)


def read_samplesheet(samplesheet: Path) -> pd.DataFrame:
    """
    Reads SampleSheet.csv and returns dataframe (all header information will be stripped)
    :param samplesheet: Path to SampleSheet.csv
    :return: pandas df of SampleSheet.csv with head section stripped away
    """
    # TODO: Verify that it's always 22 rows that need to be skipped. Will need to change approach if it varies.
    df = pd.read_csv(samplesheet, sep=",", index_col=False, skiprows=22)
    return df


def get_sample_id_list(samplesheet_df: pd.DataFrame) -> list:
    """
    Returns list of all SampleIDs in SampleSheet dataframe
    :param samplesheet_df: df returned from read_samplesheet()
    :return: list of all Sample IDs
    """
    sample_id_list = list(samplesheet_df['Sample_ID'])
    return sample_id_list


def group_by_project(samplesheet_df: pd.DataFrame) -> dict:
    """
    Groups samples by project extracted from SampleSheet.csv.
    :param samplesheet_df: df returned from read_samplesheet()
    :return: project dictionary (Keys are project names, values are lists of associated samples)
    """
    project_list = list(samplesheet_df.groupby(['Sample_Project']).groups.keys())
    project_dict = {}
    for project in project_list:
        project_dict[project] = list(samplesheet_df[samplesheet_df['Sample_Project'] == project]['Sample_ID'])
    return project_dict


def extract_run_name(samplesheet: Path) -> str:
    """
    Retrieves the 'Experiment Name' from SampleSheet.csv
    :param samplesheet: Path to SampleSheet.csv
    :return: value of 'Experiment Name'
    """
    with open(str(samplesheet)) as f:
        for line in f:
            if 'Experiment Name' in line:
                experiment_name = line.split(',')[1].strip()
                return experiment_name
        else:
            raise Exception(f"Could not find 'Experiment Name' in {samplesheet}")


def validate_sample_id(value: str, length: int = 15) -> bool:
    """
    Strict validation of BMH Sample ID
    :param value: sample_id
    :param length: expected length of string
    """
    if len(value) != length:
        raise Exception(f"Sample ID '{value}' does not meet the expected length of 15 characters. "
                        f"Sample ID must be in the following format: 'BMH-2018-000001'")

    components = value.split("-")
    if len(components) != 3:
        raise Exception(f"Sample ID '{value}' does not appear to meet expected format. "
                        f"Sample ID must be in the following format: 'BMH-2018-000001'")
    elif components[0] != "BMH":
        raise Exception(f"BMH component of Sample ID ('{components[0]}') does not equal expected 'BMH'")
    elif not components[1].isdigit() or len(components[1]) != 4:
        raise Exception(f"YEAR component of Sample ID ('{components[1]}') does not equal expected 'YYYY' format")
    elif not components[2].isdigit() or len(components[2]) != 6:
        raise Exception(f"ID component of Sample ID ('{components[2]}') does not equal expected 'XXXXXX' format")
    else:
        return True
