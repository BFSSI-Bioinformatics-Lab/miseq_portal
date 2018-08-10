import os
import shutil
from pathlib import Path
from config.settings.base import MEDIA_ROOT

from miseq_uploader.parse_samplesheet import parse_samplesheet
from miseq_uploader.parse_miseq_analysis_folder import parse_miseq_folder
from miseq_uploader.parse_stats_json import stats_json_to_df

from miseq_viewer.models import Project, Run, Sample, SampleLogData, \
    upload_samplesheet, upload_reads


def receive_miseq_run_dir(miseq_dir: Path):
    print(f'{"="*24}\nCHECKING MISEQ DIRECTORY\n{"="*24}')
    miseq_dict = parse_miseq_folder(miseq_folder=miseq_dir)

    print(f'{"="*20}\nCHECKING SAMPLESHEET\n{"="*20}')
    samplesheet_dict = parse_samplesheet(samplesheet=miseq_dict['samplesheet_path'])

    print("\nChecking for correspondence between Basecalls folder and SampleSheet.csv...")

    for sample_id in set(miseq_dict['sample_dict'].keys()):
        if sample_id not in set(samplesheet_dict['sample_id_list']):
            print(f'FAIL: Could not find reads for {sample_id}')
            return
    print('PASS: All samples present in both SampleSheet.csv and the Basecalls directory')

    # TODO: There's a bug here where projects will be created if samples are listed in SampleSheet.csv, but are
    # TODO: not available as .fastq.gz files in the data folder. It's not a big deal, but should be fixed.
    print(f'{"="*21}\nUPLOADING TO DATABASE\n{"="*21}')
    for project_id in samplesheet_dict['project_dict'].keys():
        upload_to_db(project_id=project_id, run_id=samplesheet_dict['run_id'],
                     sample_dict=miseq_dict['sample_dict'], samplesheet=miseq_dict['samplesheet_path'],
                     sample_name_dict=samplesheet_dict['sample_name_dict'],
                     json_stats_file=miseq_dict['json_stats_file'])


def upload_to_db(project_id: str, run_id: str, sample_dict: dict, sample_name_dict: dict,
                 samplesheet: Path, json_stats_file: Path):
    stats_df = stats_json_to_df(stats_json=json_stats_file)
    project, p_created = Project.objects.get_or_create(project_id=project_id)
    if p_created:
        print(f"\nCreated project '{project}'")
    else:
        print(f"\nAdding run and samples to existing project '{project}'")

    # Saving Run and uploading SampleSheet.csv
    run, r_created = Run.objects.get_or_create(run_id=run_id, defaults={'project_id': project, 'sample_sheet': ''})
    if r_created:
        print(f"\nCreated run '{run}'")
        samplesheet_path = upload_samplesheet(instance=run, filename=samplesheet.name)
        os.makedirs(os.path.dirname(MEDIA_ROOT + '/' + samplesheet_path), exist_ok=True)
        shutil.copy(str(samplesheet), (MEDIA_ROOT + '/' + samplesheet_path))
        run.sample_sheet = samplesheet_path
        run.save()
    else:
        print(f"\nAdding samples to existing run '{run}'")

    # Uploading samples + metadata
    for sample_id, reads in sample_dict.items():
        sample, s_created = Sample.objects.get_or_create(sample_id=sample_id,
                                                         defaults={'run_id': run, 'project_id': project})
        sample_log, sl_created = SampleLogData.objects.get_or_create(sample_id=sample)

        if s_created:
            print(f"\nUploading {sample_id}")

            # Sample data + read handling
            fwd_read_path = upload_reads(sample, reads[0].name)
            rev_read_path = upload_reads(sample, reads[1].name)
            os.makedirs(os.path.dirname(MEDIA_ROOT + '/' + fwd_read_path), exist_ok=True)
            shutil.copy(str(reads[0]), os.path.dirname(MEDIA_ROOT + '/' + fwd_read_path))
            shutil.copy(str(reads[1]), os.path.dirname(MEDIA_ROOT + '/' + fwd_read_path))
            sample.fwd_reads = fwd_read_path
            sample.rev_reads = rev_read_path
            sample.sample_name = sample_name_dict[sample_id]  # TODO: test this
            sample.save()

        else:
            print(f"Sample {sample} already exists")

        # Update the stats of the samples regardless of being newly created or not
        # Sample log stats retrieved from stats_df
        number_reads = int(stats_df[stats_df['sample_id'] == sample_id]['NumberReads'])
        sample_yield = int(stats_df[stats_df['sample_id'] == sample_id]['Yield'])
        r1_qualityscoresum = int(stats_df[stats_df['sample_id'] == sample_id]['R1_QualityScoreSum'])
        r2_qualityscoresum = int(stats_df[stats_df['sample_id'] == sample_id]['R2_QualityScoreSum'])

        # TODO: @Bug trimmed bases are always 0?
        r1_trimmedbases = int(stats_df[stats_df['sample_id'] == sample_id]['R1_TrimmedBases'])
        r2_trimmedbases = int(stats_df[stats_df['sample_id'] == sample_id]['R2_TrimmedBases'])

        r1_yield = int(stats_df[stats_df['sample_id'] == sample_id]['R1_Yield'])
        r2_yield = int(stats_df[stats_df['sample_id'] == sample_id]['R2_Yield'])
        r1_yieldq30 = int(stats_df[stats_df['sample_id'] == sample_id]['R1_YieldQ30'])
        r2_yieldq30 = int(stats_df[stats_df['sample_id'] == sample_id]['R2_YieldQ30'])

        # Save sample stats
        sample_log.number_reads = number_reads
        sample_log.sample_yield = sample_yield
        sample_log.r1_qualityscoresum = r1_qualityscoresum
        sample_log.r2_qualityscoresum = r2_qualityscoresum
        sample_log.r1_trimmedbases = r1_trimmedbases
        sample_log.r2_trimmedbases = r2_trimmedbases
        sample_log.r1_yield = r1_yield
        sample_log.r2_yield = r2_yield
        sample_log.r1_yieldq30 = r1_yieldq30
        sample_log.r2_yieldq30 = r2_yieldq30
        sample_log.save()

