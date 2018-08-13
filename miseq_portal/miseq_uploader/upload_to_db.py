import os
import shutil

from pathlib import Path
from config.settings.base import MEDIA_ROOT

from miseq_uploader.parse_samplesheet import parse_samplesheet, SampleObject
from miseq_uploader.parse_miseq_analysis_folder import parse_miseq_folder
from miseq_uploader.parse_stats_json import stats_json_to_df

from miseq_viewer.models import Project, Run, Sample, SampleLogData, \
    upload_samplesheet, upload_reads


def receive_miseq_run_dir(miseq_dir: Path):
    print(f'{"="*24}\nCHECKING MISEQ DIRECTORY\n{"="*24}')
    miseq_dict = parse_miseq_folder(miseq_folder=miseq_dir)

    print(f'{"="*20}\nCHECKING SAMPLESHEET\n{"="*20}')
    samplesheet = miseq_dict['samplesheet_path']
    json_stats_file = miseq_dict['json_stats_file']
    sample_object_list = parse_samplesheet(samplesheet=miseq_dict['samplesheet_path'])

    # Update SampleObjects with stats and reads
    sample_object_list = append_sample_object_reads(sample_dict=miseq_dict['sample_dict'],
                                                    sample_object_list=sample_object_list)
    sample_object_list = append_sample_object_stats(json_stats_file=json_stats_file,
                                                    sample_object_list=sample_object_list)

    upload_to_db(sample_object_list=sample_object_list,
                 samplesheet=samplesheet)


def append_sample_object_reads(sample_dict: dict, sample_object_list: [SampleObject]) -> [SampleObject]:
    """Appends read paths to SampleObjects given a sample_dict.
    Useful side effect of only returning SampleObjects that actually have reads associated with them."""
    sample_object_list_reads = list()
    for sample_id, reads in sample_dict.items():
        for sample_object in sample_object_list:
            if sample_object.sample_id == sample_id:
                sample_object.fwd_read_path = reads[0]
                sample_object.rev_read_path = reads[1]
                sample_object_list_reads.append(sample_object)
    return sample_object_list_reads


def append_sample_object_stats(json_stats_file: Path, sample_object_list: [SampleObject]) -> [SampleObject]:
    """Given a list of SampleObjects + the Stats.json file from the same run, appends those stats to the SampleObject"""
    sample_object_list_stats = list()
    for sample_object in sample_object_list:
        stats_df = stats_json_to_df(stats_json=json_stats_file)
        sample_object.number_reads = int(stats_df[stats_df['sample_id'] == sample_object.sample_id]['NumberReads'])
        sample_object.sample_yield = int(stats_df[stats_df['sample_id'] == sample_object.sample_id]['Yield'])
        sample_object.r1_qualityscoresum = int(
            stats_df[stats_df['sample_id'] == sample_object.sample_id]['R1_QualityScoreSum'])
        sample_object.r2_qualityscoresum = int(
            stats_df[stats_df['sample_id'] == sample_object.sample_id]['R2_QualityScoreSum'])
        sample_object.r1_trimmedbases = int(
            stats_df[stats_df['sample_id'] == sample_object.sample_id]['R1_TrimmedBases'])
        sample_object.r2_trimmedbases = int(
            stats_df[stats_df['sample_id'] == sample_object.sample_id]['R2_TrimmedBases'])
        sample_object.r1_yield = int(stats_df[stats_df['sample_id'] == sample_object.sample_id]['R1_Yield'])
        sample_object.r2_yield = int(stats_df[stats_df['sample_id'] == sample_object.sample_id]['R2_Yield'])
        sample_object.r1_yieldq30 = int(stats_df[stats_df['sample_id'] == sample_object.sample_id]['R1_YieldQ30'])
        sample_object.r2_yieldq30 = int(stats_df[stats_df['sample_id'] == sample_object.sample_id]['R2_YieldQ30'])
        sample_object_list_stats.append(sample_object)
    return sample_object_list_stats


def upload_to_db(sample_object_list: [SampleObject], samplesheet: Path):
    """Takes list of fully populated SampleObjects + path to SampleSheet and uploads to the database"""
    for sample_object in sample_object_list:
        # PROJECT
        project, p_created = Project.objects.get_or_create(project_id=sample_object.project_id)
        if p_created:
            print(f"\nCreated project '{project}'")

        # RUN
        run, r_created = Run.objects.get_or_create(run_id=sample_object.run_id, defaults={'project_id': project,
                                                                                          'sample_sheet': ''})
        if r_created:
            print(f"\nCreated run '{run}'")
            samplesheet_path = upload_samplesheet(instance=run, filename=samplesheet.name)
            os.makedirs(os.path.dirname(MEDIA_ROOT + '/' + samplesheet_path), exist_ok=True)
            shutil.copy(str(samplesheet), (MEDIA_ROOT + '/' + samplesheet_path))
            run.sample_sheet = samplesheet_path
            run.save()

        # SAMPLE
        sample, s_created = Sample.objects.get_or_create(sample_id=sample_object.sample_id,
                                                         defaults={'run_id': run, 'project_id': project})
        sample_log, sl_created = SampleLogData.objects.get_or_create(sample_id=sample)
        if s_created:
            print(f"\nUploading {sample_object.sample_id}...")

            # Sample data + read handling
            fwd_read_path = upload_reads(sample, sample_object.fwd_read_path.name)
            rev_read_path = upload_reads(sample, sample_object.rev_read_path.name)
            os.makedirs(os.path.dirname(MEDIA_ROOT + '/' + fwd_read_path), exist_ok=True)
            shutil.copy(str(sample_object.fwd_read_path), os.path.dirname(MEDIA_ROOT + '/' + fwd_read_path))
            shutil.copy(str(sample_object.rev_read_path), os.path.dirname(MEDIA_ROOT + '/' + fwd_read_path))
            sample.fwd_reads = fwd_read_path
            sample.rev_reads = rev_read_path
            sample.sample_name = sample_object.sample_name
            sample.save()

        # Save sample stats
        sample_log.number_reads = sample_object.number_reads
        sample_log.sample_yield = sample_object.sample_yield
        sample_log.r1_qualityscoresum = sample_object.r1_qualityscoresum
        sample_log.r2_qualityscoresum = sample_object.r2_qualityscoresum
        sample_log.r1_trimmedbases = sample_object.r1_trimmedbases
        sample_log.r2_trimmedbases = sample_object.r2_trimmedbases
        sample_log.r1_yield = sample_object.r1_yield
        sample_log.r2_yield = sample_object.r2_yield
        sample_log.r1_yieldq30 = sample_object.r1_yieldq30
        sample_log.r2_yieldq30 = sample_object.r2_yieldq30
        sample_log.save()
