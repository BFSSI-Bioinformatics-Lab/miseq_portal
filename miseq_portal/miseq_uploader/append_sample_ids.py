"""
Standalone script to append Sample IDs to all *.fastq.gz files in a directory given a SampleSheet
"""

import os
from pathlib import Path
from miseq_uploader.parse_samplesheet import get_sample_name_dictionary, read_samplesheet, extract_run_name, \
    group_by_project, get_sample_id_list, validate_sample_id, validate_samplesheet_header
from miseq_uploader.parse_miseq_analysis_folder import retrieve_fastqgz, filter_undetermined_reads


def samplesheet_to_samplename_dict(samplesheet: Path) -> dict:
    df = read_samplesheet(sample_sheet=samplesheet)

    # Validate header
    validate_samplesheet_header(header=list(df))
    print("PASS: Header is valid")

    # Grab Run Name
    run_id = extract_run_name(sample_sheet=samplesheet)
    print(f"\nDetected the following Run name: {run_id}")

    # Get all Projects and associated samples from the SampleSheet
    project_dict = group_by_project(samplesheet_df=df)
    print(f"\nDetected the following Projects within the SampleSheet:")
    for key, value in project_dict.items():
        print(key)

    # Get all Sample IDs
    sample_id_list = get_sample_id_list(samplesheet_df=df)

    # Check all Sample IDs
    for sample_id in sample_id_list:
        validate_sample_id(value=sample_id)

    # Get Sample Names
    sample_name_dictionary = get_sample_name_dictionary(df=df)
    return sample_name_dictionary


def get_read_list(data_folder: Path) -> list:
    fastq_list = retrieve_fastqgz(data_folder)
    fastq_list = filter_undetermined_reads(fastq_list)
    return fastq_list


def check_sample_ids_in_filenames(data_folder: Path, samplesheet: Path):
    fastq_list = get_read_list(data_folder=data_folder)
    sample_name_dictionary = samplesheet_to_samplename_dict(samplesheet=samplesheet)

    # Check if Sample ID or Sample Name is the first element of filenames
    for fastq_file in fastq_list:
        name_element = fastq_file.name.split('_')[0]
        if name_element in sample_name_dictionary.keys():
            pass
        else:
            for sample_id, sample_name in sample_name_dictionary.items():
                if sample_name == name_element:
                    # Append sample_id to beginning of filename
                    fastq_file_renamed = fastq_file.parent / (sample_id + '_' + fastq_file.name)
                    print(f"Renaming {fastq_file.name} to {fastq_file_renamed.name}")
                    os.rename(fastq_file, fastq_file_renamed)


def main():
    # TODO: Make this CLI friendly instead of this hardcoded nonsense
    data_folder = Path("/home/brock/Projects/BMH-MiSeq/Basemount_MiSeqPortal/180816_M01308_0087_000000000-BMH68/Data/Intensities/BaseCalls")
    samplesheet = Path("/home/brock/Projects/BMH-MiSeq/Basemount_MiSeqPortal/180816_M01308_0087_000000000-BMH68/SampleSheet.csv")
    check_sample_ids_in_filenames(data_folder=data_folder, samplesheet=samplesheet)


if __name__ == "__main__":
    main()
