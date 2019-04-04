import logging
from pathlib import Path

import pandas as pd

from miseq_portal.miseq_viewer.models import SampleDataObject

logger = logging.getLogger('django')


def validate_samplesheet_header(header: list) -> bool:
    """
    Validates that column names match expected values.
    Expected column names for both iSeq and MiSeq sequencers are hardcoded here.
    :param header: List of column names
    :return: True if header meets all expected values, else False
    """
    header = sorted(header)
    expected_miseq_header = sorted(['Sample_ID', 'Sample_Name',
                                    'Sample_Plate', 'Sample_Well',
                                    'I7_Index_ID', 'index',
                                    'I5_Index_ID', 'index2',
                                    'Sample_Project', 'Description'
                                    ])

    expected_iseq_header = sorted(['Sample_ID', 'Sample_Name', 'Description',
                                   'I7_Index_ID', 'index',
                                   'I5_Index_ID', 'index2',
                                   'Sample_Project'
                                   ])

    if not set(header) == set(expected_miseq_header) and not set(header) == set(expected_iseq_header):
        raise Exception(
            f"Provided header {header} does not match expected header.\nExpected:\n"
            f"MiSeq:\t{expected_miseq_header} or \n"
            f"iSeq:\t{expected_iseq_header}")
    return True


def read_samplesheet(samplesheet: Path) -> pd.DataFrame:
    """
    Reads SampleSheet.csv and returns dataframe (all header information will be stripped)
    :param samplesheet: Path to SampleSheet.csv
    :return: pandas df of SampleSheet.csv with head section stripped away
    """
    counter = 1
    with open(str(samplesheet)) as f:
        for line in f:
            if '[Data]' in line:
                break
            else:
                counter += 1
    df = pd.read_csv(samplesheet, sep=",", index_col=False, skiprows=counter)

    # Force Sample_Name and Sample_Project into str types
    df['Sample_Name'] = df['Sample_Name'].astype(str)
    df['Sample_Project'] = df['Sample_Project'].astype(str)

    # Fill in missing projects
    df['Sample_Project'] = df['Sample_Project'].replace(r"\s+", "MISSING_PROJECT", regex=True)
    df['Sample_Project'] = df['Sample_Project'].fillna(value="MISSING_PROJECT")

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
            elif 'Description' in line:
                experiment_name = line.split(',')[1].strip()
                return experiment_name
        else:
            raise Exception(f"Could not find 'Experiment Name' in {samplesheet}")


def check_sample_id(value: str, length: int = 15) -> bool:
    """
    Light validation of BMH Sample ID
    :param value: sample_id
    :param length: expected length of string
    """
    if len(value) != length:
        return False
    components = value.split("-")
    if len(components) != 3:
        return False
    elif components[0] != "BMH":
        return False
    elif not components[1].isdigit() or len(components[1]) != 4:
        return False
    elif not components[2].isdigit() or len(components[2]) != 6:
        return False
    else:
        return True


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


def generate_sample_objects(samplesheet: Path) -> [SampleDataObject]:
    df = read_samplesheet(samplesheet=samplesheet)

    # Validate header
    validate_samplesheet_header(header=list(df))
    logger.info("PASS: Header is valid")

    # Grab Run Name
    run_id = extract_run_name(samplesheet=samplesheet)
    logger.info(f"Detected the following Run name: {run_id}")

    # Get all Projects and associated samples from the SampleSheet
    project_dict = group_by_project(samplesheet_df=df)
    logger.info(f"Detected the following Projects within the SampleSheet:")
    for key, value in project_dict.items():
        logger.info(key)

    # Get all Sample IDs
    sample_id_list = get_sample_id_list(samplesheet_df=df)

    # Check all Sample IDs - if they are valid, assign sample_type BMH to each. Otherwise, assign EXT.
    valid_list = []
    for sample_id in sample_id_list:
        valid_list.append(check_sample_id(value=sample_id))
    if False not in valid_list:
        sample_type = "BMH"
    else:
        sample_type = "EXT"

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
                                                 project_id=project_id,
                                                 sample_type=sample_type)
                sample_object_list.append(sample_object)
    return sample_object_list


def extract_samplesheet_header_lines(samplesheet: Path):
    """
    Takes an input SampleSheet.csv file and extracts the lines between the [Header] and [Reads] subheaders.
    Fairly brittle approach with the assumption that Illumina won't change their SampleSheet format.
    :param samplesheet: Path to SampleSheet.csv generated by MiSeq or iSeq
    :return: List containing header lines
    """
    samplesheet_headers = []
    with open(str(samplesheet), 'r') as f:
        for line in f:
            line = line.strip()
            if line == '[Header]':
                continue
            elif line == '[Reads]':
                break
            samplesheet_headers.append(line)
    return samplesheet_headers


def samplesheet_headers_to_dict(samplesheet_headers: list) -> dict:
    """
    Given a list of headers extracted with extract_samplesheet_header_fields, will parse them into a dictionary
    :param samplesheet_headers: List of header lines
    :return: Dictionary containing data that can be fed directly into the RunSamplesheet model (keys are attributes)
    """
    attr_dict = {}
    for line in samplesheet_headers:
        components = line.split(',')
        _attr = components[0].lower().replace(" ", "_")
        try:
            _val = components[1]
        except IndexError:
            _val = ""
        attr_dict[_attr] = _val
    return attr_dict


def extract_samplesheet_headers(samplesheet: Path) -> dict:
    samplesheet_headers = extract_samplesheet_header_lines(samplesheet=samplesheet)
    attr_dict = samplesheet_headers_to_dict(samplesheet_headers=samplesheet_headers)
    return attr_dict
