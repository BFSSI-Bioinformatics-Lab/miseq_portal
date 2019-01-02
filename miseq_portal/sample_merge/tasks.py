import os
from pathlib import Path
from celery import shared_task
from miseq_portal.miseq_viewer.models import Sample, Project, upload_reads
from miseq_portal.analysis.tools.helpers import run_subprocess
from miseq_portal.analysis.tools.assemble_run import assemble_sample_instance
from config.settings.base import MEDIA_ROOT

import logging

logger = logging.getLogger('raven')


@shared_task()
def merge_reads(sample_object_id_list: [int], merged_sample_id: int):
    """
    Receives a list of Sample object pk values (components for the merged sample) as well as the pk for a
    newly created merged sample. Retrieves relevant objects by their pk values, then passes the Sample objects to the
    actual merging function.
    """
    sample_object_list = [Sample.objects.get(pk=sample_id) for sample_id in sample_object_id_list]
    merged_sample = Sample.objects.get(pk=merged_sample_id)
    merge_reads_sample_objects(sample_object_list=sample_object_list, merged_sample=merged_sample)


def determine_merged_sample_name(sample_object_list: [Sample]) -> str:
    """
    Takes a list of sample objects to be merged and figures out the most informative sample name.
    If all sample names share the same sample_name, that will be returned. Otherwise this will return a string joined
    by '+' containing each sample_name.
    """
    sample_names = [sample_object.sample_name for sample_object in sample_object_list]
    sample_names = list(set(sample_names))
    return "+".join(sample_names)


def determine_merged_sample_project_id(sample_object_list: [Sample]) -> (Project, None):
    """
    Takes a list of sample objects to be merged and returns a shared project_id if there is one, otherwise returns None
    """
    sample_projects = [sample_object.project_id for sample_object in sample_object_list]
    sample_names = list(set(sample_projects))

    if len(sample_names) == 1:
        return sample_names[0]
    else:
        return None


def merge_reads_sample_objects(sample_object_list: [Sample], merged_sample: Sample):
    fwd_out, rev_out = create_merge_sample_dir(merged_sample)

    # Create full file paths to R1 and R2 reads for each sample object, then concatenate R1 and R2 respectively
    fwd_reads = [Path(MEDIA_ROOT) / str(sample_object.fwd_reads) for sample_object in sample_object_list]
    rev_reads = [Path(MEDIA_ROOT) / str(sample_object.rev_reads) for sample_object in sample_object_list]
    concatenate_read_files(fwd_read_list=fwd_reads, rev_read_list=rev_reads, fwd_out=fwd_out, rev_out=rev_out)

    # Determine sample name
    sample_name = determine_merged_sample_name(sample_object_list)
    merged_sample.sample_name = sample_name

    # Determine project_id
    project_id = determine_merged_sample_project_id(sample_object_list)
    merged_sample.project_id = project_id

    # Update merged_sample object in database
    merged_sample.fwd_reads = upload_reads(merged_sample, fwd_out.name)
    merged_sample.rev_reads = upload_reads(merged_sample, rev_out.name)
    logger.info(f"Successfully updated {merged_sample} with merged R1 and R2 read files!")
    merged_sample.save()

    # Queue up assembly for the newly merged sample
    assemble_sample_instance.delay(sample_object_id=merged_sample.sample_id)


def create_merge_sample_dir(merged_sample: Sample):
    merge_dir = Path(MEDIA_ROOT) / 'merged_samples'
    merged_sample_path = merge_dir / merged_sample.sample_id
    os.makedirs(merged_sample_path, exist_ok=False)
    merged_sample_path_fwd = merged_sample_path / str(merged_sample.sample_id + "_R1.fastq.gz")
    merged_sample_path_rev = merged_sample_path / str(merged_sample.sample_id + "_R2.fastq.gz")
    return merged_sample_path_fwd, merged_sample_path_rev


def concatenate_read_files(fwd_read_list: [Path], rev_read_list: [Path], fwd_out: Path, rev_out: Path):
    fwd_read_list_text = " ".join([str(read) for read in fwd_read_list])
    rev_read_list_text = " ".join([str(read) for read in rev_read_list])
    fwd_cmd = f"cat {fwd_read_list_text} > {fwd_out}"
    rev_cmd = f"cat {rev_read_list_text} > {rev_out}"
    logger.info(f"Running the following command: {fwd_cmd}")
    run_subprocess(fwd_cmd)
    logger.info(f"Running the following command: {rev_cmd}")
    run_subprocess(rev_cmd)
    logger.info(f"R1: {fwd_out}")
    logger.info(f"R2: {rev_out}")
