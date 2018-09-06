import pandas as pd
from pathlib import Path
from miseq_viewer.models import SampleDataObject

import logging
logger = logging.getLogger('raven')


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
    if not set(header) == set(expected_header):
        raise Exception(f"Provided header {header} does not match expected header {expected_header}")
    else:
        return True


def read_samplesheet(sample_sheet: Path) -> pd.DataFrame:
    """
    Reads SampleSheet.csv and returns dataframe (all header information will be stripped)
    :param sample_sheet: Path to SampleSheet.csv
    :return: pandas df of SampleSheet.csv with head section stripped away
    """
    counter = 1
    with open(str(sample_sheet)) as f:
        for line in f:
            if '[Data]' in line:
                break
            else:
                counter += 1
    df = pd.read_csv(sample_sheet, sep=",", index_col=False, skiprows=counter)
    return df


def read_samplesheet_to_html(sample_sheet: Path) -> pd.DataFrame:
    df = read_samplesheet(sample_sheet)
    return df.to_html(table_id="samplesheet", index=None, classes=['compact'], bold_rows=False, )


def get_sample_id_list(samplesheet_df: pd.DataFrame) -> list:
    """
    Returns list of all SampleIDs in SampleSheet dataframe
    :param samplesheet_df: df returned from read_samplesheet()
    :return: list of all Sample IDs
    """
    sample_id_list = list(samplesheet_df['Sample_ID'])
    return sample_id_list


def get_sample_name_dictionary(df: pd.DataFrame):
    sample_name_dictionary = df.set_index('Sample_ID').to_dict()['Sample_Name']
    return sample_name_dictionary


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


def extract_run_name(sample_sheet: Path) -> str:
    """
    Retrieves the 'Experiment Name' from SampleSheet.csv
    :param sample_sheet: Path to SampleSheet.csv
    :return: value of 'Experiment Name'
    """
    with open(str(sample_sheet)) as f:
        for line in f:
            if 'Experiment Name' in line:
                experiment_name = line.split(',')[1].strip()
                return experiment_name
        else:
            raise Exception(f"Could not find 'Experiment Name' in {sample_sheet}")


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


def generate_sample_objects(sample_sheet: Path) -> [SampleDataObject]:
    df = read_samplesheet(sample_sheet=sample_sheet)

    # Validate header
    validate_samplesheet_header(header=list(df))
    logger.info("PASS: Header is valid")

    # Grab Run Name
    run_id = extract_run_name(sample_sheet=sample_sheet)
    logger.info(f"\nDetected the following Run name: {run_id}")

    # Get all Projects and associated samples from the SampleSheet
    project_dict = group_by_project(samplesheet_df=df)
    logger.info(f"\nDetected the following Projects within the SampleSheet:")
    for key, value in project_dict.items():
        logger.info(key)

    # Get all Sample IDs
    sample_id_list = get_sample_id_list(samplesheet_df=df)

    # Check all Sample IDs
    for sample_id in sample_id_list:
        validate_sample_id(value=sample_id)

    # Get Sample Names
    sample_name_dictionary = get_sample_name_dictionary(df=df)

    # Create SampleDataObject list. Need to consolidate sample_id, sample_name, project_id, and run_id per-sample
    sample_object_list = list()
    for sample_id in sample_id_list:
        for project_id, sample_list in project_dict.items():
            if sample_id in sample_list:
                sample_object = SampleDataObject(sample_id=sample_id,
                                                 sample_name=sample_name_dictionary[sample_id],
                                                 run_id=run_id,
                                                 project_id=project_id)
                sample_object_list.append(sample_object)

    return sample_object_list
