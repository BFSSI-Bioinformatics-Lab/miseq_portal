import logging
from pathlib import Path

from miseq_portal.miseq_uploader.parse_samplesheet import extract_run_name, read_samplesheet
from miseq_portal.miseq_viewer.models import RunDataObject

# logger = logging.getLogger('raven')
logger = logging.getLogger(__name__)


def verify_miseq_folder_contents(miseq_folder: Path) -> bool:
    """
    Function to perform minimal check of input MiSeqAnalysis folder to ensure it follows the expected structure
    :param miseq_folder: Path to MiSeqAnalysis folder
    :return: True if folder meets expected structure, False if not
    """
    check_dict = dict()
    check_dict['sample_sheet'] = False
    check_dict['interop'] = False
    check_dict['data'] = False
    check_dict['basecalls'] = False
    check_dict['logs'] = False

    for f in miseq_folder.glob("*"):
        if f.name == "SampleSheet.csv":
            check_dict['sample_sheet'] = True
            logger.info("PASS: Detected 'SampleSheet.csv'")
        elif f.name == "InterOp" and f.is_dir():
            check_dict['interop'] = True
            logger.info("PASS: Detected 'InterOp' directory")
        elif f.name == "Data" and f.is_dir():
            check_dict['data'] = True
            logger.info("PASS: Detected 'Data' directory")
        elif f.name == "Logs" and f.is_dir():
            check_dict['logs'] = True
            logger.info("PASS: Detected 'Logs' directory")
        else:
            pass

    # Check for fastq files in expected location
    if len(list(miseq_folder.glob("Data/Intensities/BaseCalls/*.f*q*"))) > 0:
        check_dict['basecalls'] = True
        logger.info("PASS: Detected a non-zero number of *.fastq.gz files in ./Data/Intensities/BaseCalls/*")
    else:
        raise Exception("FAIL: Could not detect any *.fastq.gz files in ./Data/Intensities/BaseCalls/*")

    if False in check_dict.values():
        raise Exception(f"Input folder {miseq_folder} is not structured as expected."
                        f"{check_dict}")
    else:
        logger.info(f"Input folder {miseq_folder} passed all basic checks")
        return True


def retrieve_fastqgz(directory: Path) -> [Path]:
    """
    :param directory: Path to folder containing output from MiSeq run
    :return: LIST of all .fastq.gz files in directory
    """
    fastq_file_list = list(directory.glob("*.f*q*"))
    return fastq_file_list


def filter_undetermined_reads(fastq_file_list: list) -> list:
    filtered_list = [x for x in fastq_file_list if 'Undetermined_' not in x.name]
    return filtered_list


def retrieve_sampleids(fastq_file_list: [Path]) -> list:
    """
    :param fastq_file_list: List of fastq.gz filepaths generated by retrieve_fastqgz()
    :return: List of Sample IDs
    """
    # Iterate through all of the fastq files and grab the sampleID, append to list
    sample_id_list = list()
    for f in fastq_file_list:
        sample_id = f.name.split('_')[0]
        sample_id_list.append(sample_id)

    # Get unique sample IDs
    sample_id_list = list(set(sample_id_list))
    return sample_id_list


def get_readpair(sample_id: str, fastq_file_list: [Path], forward_id: str = "_R1",
                 reverse_id: str = "_R2") -> (list, None):
    """
    :param sample_id: String of sample ID
    :param fastq_file_list: List of fastq.gz file paths generated by retrieve_fastqgz()
    :param forward_id: ID indicating forward read in filename (e.g. _R1_)
    :param reverse_id: ID indicating reverse read in filename (e.g. _R2_)
    :return: the absolute filepaths of R1 and R2 for a given sample ID
    """

    r1, r2 = None, None
    for f in fastq_file_list:
        if sample_id == f.name.split("_")[0]:  # NOTE: Splitting on '_' is a bit brittle
            if forward_id in f.name:
                r1 = f
            elif reverse_id in f.name:
                r2 = f
    if r1 is not None and r2 is not None:
        return [r1, r2]
    else:
        logger.info('Could not pair {}'.format(sample_id))
        return None


def populate_sample_dictionary(sample_id_dict: dict, fastq_file_list: [Path]) -> dict:
    """
    :param sample_id_dict: Dict of unique Sample IDs generated by retrieve_sampleids()
    :param fastq_file_list: List of fastq.gz file paths generated by retrieve_fastqgz()
    :return: dictionary with each Sample ID as a key and the read pairs as values
    """
    # Find file pairs for each unique sample ID
    sample_dictionary = {}
    for sample_id, corrected_sample_id in sample_id_dict.items():
        read_pair = get_readpair(sample_id, fastq_file_list)
        if read_pair is not None:
            sample_dictionary[corrected_sample_id] = read_pair
        else:
            pass
    return sample_dictionary


def correct_sample_id_list(sample_id_list: list, sample_sheet: Path) -> dict:
    """
    This function will prioritize taking the Sample_ID value over the Sample_Name value and will associate it with
    the reads downstream if they are different.
    """

    # Correct the sample_id_list if necessary
    df = read_samplesheet(sample_sheet)
    sample_id_dict = {}
    for sample_id in sample_id_list:
        sample_id_values = list(df['Sample_ID'].values)
        sample_name_values = list(df['Sample_Name'].values)

        # Verify sample_id is in Sample_ID or Sample_Name column
        if sample_id in sample_id_values:
            sample_id_dict[sample_id] = sample_id
        elif sample_id in sample_name_values:
            sample_id_value = df[df['Sample_Name'] == sample_id].reset_index()['Sample_ID'][0]
            sample_id_dict[sample_id] = sample_id_value
        else:
            raise ValueError(f"Couldn't find provided sample ID {sample_id} in SampleSheet")
    return sample_id_dict


def get_sample_dictionary(directory: Path, sample_sheet: Path) -> dict:
    """
    Creates a sample dictionary with unique/valid sample IDs as keys and paths to forward and reverse reads as values
    :param directory: Path to a directory containing .fastq.gz files
    :param sample_sheet: Path to a SampleSheet.csv
    :return: Validated sample dictionary with sample_ID:R1,R2 structure
    """
    fastq_file_list = retrieve_fastqgz(directory)
    fastq_file_list = filter_undetermined_reads(fastq_file_list)
    sample_id_list = retrieve_sampleids(fastq_file_list)
    sample_id_dict = correct_sample_id_list(sample_id_list=sample_id_list, sample_sheet=sample_sheet)
    sample_dictionary = populate_sample_dictionary(sample_id_dict, fastq_file_list)
    logger.info(f"Successfully paired {len(sample_dictionary)} of {len(sample_id_list)} samples:")
    return sample_dictionary


def populate_run_object_interop(interop_dir: Path, run_id: str):
    # Instantiate
    run_data_object = RunDataObject(run_id=run_id)

    # Populate
    run_data_object.interop_dir = interop_dir
    run_data_object.control_metrics = interop_dir / 'ControlMetricsOut.bin'
    run_data_object.correctedintmetrics = interop_dir / 'CorrectedIntMetricsOut.bin'
    run_data_object.errormetrics = interop_dir / 'ErrorMetricsOut.bin'
    run_data_object.extractionmetrics = interop_dir / 'ExtractionMetricsOut.bin'
    run_data_object.indexmetrics = interop_dir / 'IndexMetricsOut.bin'
    run_data_object.qmetrics2030 = interop_dir / 'QMetrics2030Out.bin'
    run_data_object.qmetricsbylane = interop_dir / 'QMetricsByLaneOut.bin'
    run_data_object.qmetrics = interop_dir / 'QMetricsOut.bin'
    run_data_object.tilemetrics = interop_dir / 'TileMetricsOut.bin'
    return run_data_object


def parse_miseq_folder(miseq_dir: Path) -> dict:
    # Folder setup
    read_folder = None
    interop_folder = None

    # Make sure folder is ok
    if verify_miseq_folder_contents(miseq_dir):
        read_folder = miseq_dir / "Data" / "Intensities" / "BaseCalls"
        interop_folder = miseq_dir / "InterOp"

    # SampleSheet.csv
    sample_sheet = Path(list(miseq_dir.glob('SampleSheet.csv'))[0])

    # Get sample dict
    sample_dict = get_sample_dictionary(read_folder, sample_sheet)
    for sample, reads in sorted(sample_dict.items()):
        logger.info(f"{sample} ({reads[0].name}, {reads[1].name})")

    # RunInfo.xml
    try:
        runinfoxml = Path(list(miseq_dir.glob('RunInfo.xml'))[0])
    except IndexError as e:
        logger.info("WARNING: Could not find RunInfo.xml")
        logger.info(f"TRACEBACK: {e}")
        runinfoxml = None

    # RunParameters.xml
    try:
        runparametersxml = Path(list(miseq_dir.glob('RunParameters.xml'))[0])
    except IndexError as e:
        logger.info("WARNING: Could not find RunParameters.xml")
        logger.info(f"TRACEBACK: {e}")
        runparametersxml = None

    run_id = extract_run_name(sample_sheet)
    run_data_object = populate_run_object_interop(interop_dir=interop_folder, run_id=run_id)
    run_data_object.runinfoxml = runinfoxml
    run_data_object.runparametersxml = runparametersxml
    run_data_object.sample_sheet = sample_sheet

    # Get log files
    log_folder = miseq_dir / "Logs"
    log_files = list(log_folder.glob("*"))
    run_data_object.logfiles = log_files

    # NOTE: The stats file is only created when the run is uploaded to BaseSpace. It will be missing from local runs.
    try:
        json_stats_file = Path(list(log_folder.glob("Stats.json"))[0])
        run_data_object.json_stats_file = json_stats_file
    except IndexError as e:
        logger.info("WARNING: Could not locate ./Logs/Stats.json file")
        logger.info(f"TRACEBACK: {e}")

    # Create dict for all MiSeq data
    miseq_dict = dict()
    miseq_dict['sample_dict'] = sample_dict
    miseq_dict['run_data_object'] = run_data_object

    return miseq_dict
