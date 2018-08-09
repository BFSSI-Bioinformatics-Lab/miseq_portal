import os
import shutil
from pathlib import Path
from config.settings.base import MEDIA_ROOT

from miseq_uploader.parse_samplesheet import parse_samplesheet
from miseq_uploader.parse_miseq_analysis_folder import parse_miseq_folder

from miseq_viewer.models import Project, Run, Sample, upload_samplesheet, upload_reads


def receive_miseq_run_dir(miseq_dir: Path):
    print(f'{"="*24}\nCHECKING MISEQ DIRECTORY\n{"="*24}')
    miseq_dict = parse_miseq_folder(miseq_folder=miseq_dir)

    print(f'{"="*20}\nCHECKING SAMPLESHEET\n{"="*20}')
    samplesheet_dict = parse_samplesheet(samplesheet=miseq_dict['samplesheet_path'])

    print("\nChecking for correspondence between Basecalls folder and SampleSheet.csv...")
    if not set(miseq_dict['sample_dict'].keys()) == set(samplesheet_dict['sample_id_list']):
        s = set(miseq_dict['sample_dict'].keys())
        discrepancy_list = [x for x in set(samplesheet_dict['sample_id_list']) if x not in s]
        print(f'FAIL: Discrepencies detected ({discrepancy_list})')
    else:
        print('PASS: All samples present in both SampleSheet.csv and the Basecalls directory')

    print(f'{"="*21}\nUPLOADING TO DATABASE\n{"="*21}')
    for project_id in samplesheet_dict['project_dict'].keys():
        upload_to_db(project_id=project_id, run_id=samplesheet_dict['run_id'],
                     sample_dict=miseq_dict['sample_dict'], samplesheet=miseq_dict['samplesheet_path'],
                     sample_name_dict=samplesheet_dict['sample_name_dict'])


def upload_to_db(project_id: str, run_id: str, sample_dict: dict, sample_name_dict: dict, samplesheet: Path):
    project, p_created = Project.objects.get_or_create(project_id=project_id)
    if p_created:
        print(f"Created project '{project}'")
    else:
        print(f"Adding run and samples to existing project '{project}'")

    # Saving Run and uploading SampleSheet.csv
    run, r_created = Run.objects.get_or_create(run_id=run_id, project_id=project)
    if r_created:
        print(f"Created run '{run}'")
        samplesheet_path = upload_samplesheet(instance=run, filename=samplesheet.name)
        os.makedirs(os.path.dirname(MEDIA_ROOT + '/' + samplesheet_path), exist_ok=True)
        shutil.copy(str(samplesheet), (MEDIA_ROOT + '/' + samplesheet_path))
        run.sample_sheet = samplesheet_path
        run.save()
    else:
        print(f"Adding samples to existing run '{run}'")

    # Uploading samples
    for sample_id, reads in sample_dict.items():
        print(f"Uploading {sample_id}")
        sample, s_created = Sample.objects.get_or_create(sample_id=sample_id, run_id=run, project_id=project)

        if s_created:
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
