import os
import shutil

from pathlib import Path
from config.settings.base import MEDIA_ROOT

from miseq_uploader.parse_samplesheet import generate_sample_objects, SampleObject
from miseq_uploader.parse_miseq_analysis_folder import parse_miseq_folder, RunInterOpDataObject
from miseq_uploader.parse_stats_json import stats_json_to_df

from miseq_viewer.models import Project, UserProjectRelationship, Run, RunInterOpData, Sample, SampleLogData, \
    upload_run_file, upload_reads, upload_interop_file
from miseq_portal.users.models import User


def receive_miseq_run_dir(miseq_dir: Path):
    print(f'{"="*24}\nCHECKING MISEQ DIRECTORY\n{"="*24}')
    miseq_dict = parse_miseq_folder(miseq_folder=miseq_dir)

    print(f'{"="*20}\nCHECKING SAMPLESHEET\n{"="*20}')
    samplesheet = miseq_dict['samplesheet_path']
    json_stats_file = miseq_dict['json_stats_file']
    sample_object_list = generate_sample_objects(samplesheet=miseq_dict['samplesheet_path'])
    run_interop_object = miseq_dict['run_interop_object']

    # Update SampleObjects with stats and reads
    sample_object_list = append_sample_object_reads(sample_dict=miseq_dict['sample_dict'],
                                                    sample_object_list=sample_object_list)
    sample_object_list = append_sample_object_stats(json_stats_file=json_stats_file,
                                                    sample_object_list=sample_object_list)

    upload_to_db(sample_object_list=sample_object_list,
                 run_interop_data_object=run_interop_object,
                 samplesheet=samplesheet)
    print(f'{"="*15}\nUPLOAD COMPLETE\n{"="*15}')


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
    if json_stats_file is None:
        print("WARNING: Cannot append sample stats for this run because no Stats.json file was provided")
        return sample_object_list

    sample_object_list_stats = list()
    attribute_dict = {
        'number_reads': 'NumberReads',
        'sample_yield': 'Yield',
        'r1_qualityscoresum': 'R1_QualityScoreSum',
        'r2_qualityscoresum': 'R2_QualityScoreSum',
        'r1_trimmedbases': 'R1_TrimmedBases',
        'r2_trimmedbases': 'R2_TrimmedBases',
        'r1_yield': 'R1_Yield',
        'r2_yield': 'R2_Yield',
        'r1_yieldq30': 'R1_YieldQ30',
        'r2_yieldq30': 'R2_YieldQ30'
    }
    for sample_object in sample_object_list:
        stats_df = stats_json_to_df(stats_json=json_stats_file)
        for attribute, value in attribute_dict.items():
            set_value = int(stats_df[stats_df['sample_id'] == sample_object.sample_id][value])
            setattr(sample_object, attribute, set_value)
        sample_object_list_stats.append(sample_object)
    return sample_object_list_stats


def upload_run_interop_data(run_interop_instance: RunInterOpData, run_interop_data_object: RunInterOpDataObject,
                            run_interop_model_fieldname: str) -> RunInterOpData:
    """
    TODO: Maybe implement this pattern for other file uploads. This could be a generic function.
    :param run_interop_instance:
    :param run_interop_data_object:
    :param run_interop_model_fieldname:
    :return:
    """
    # Check if the attribute exists, quit if it doesn't
    try:
        interop_attr = getattr(run_interop_data_object, run_interop_model_fieldname)
    except AttributeError:
        raise AttributeError(f"Attribute {run_interop_model_fieldname} does not exist.")

    # Create destination path for InterOp file
    interop_file_path = upload_interop_file(run_interop_instance, interop_attr.name)

    # Create InterOp directory for file if it doesn't already exist
    os.makedirs(os.path.dirname(MEDIA_ROOT + '/' + interop_file_path), exist_ok=True)

    # Transfer the file to the disk
    shutil.copy(src=str(interop_attr), dst=(MEDIA_ROOT + '/' + interop_file_path))

    # Update the run instance
    setattr(run_interop_instance, run_interop_model_fieldname, interop_file_path)
    print(f"Succesfully uploaded {interop_attr.name}")
    return run_interop_instance


def upload_run_xml_file(run_interop_instance: RunInterOpData, run_interop_data_object: RunInterOpDataObject,
                        run_xml_fieldname: str):
    xml_attr = getattr(run_interop_data_object, run_xml_fieldname)

    # Create destination path for XML file
    xml_file_path = upload_run_file(run_interop_instance, xml_attr.name)

    # Create XML directory for file if it doesn't already exist
    os.makedirs(os.path.dirname(MEDIA_ROOT + '/' + xml_file_path), exist_ok=True)

    # Transfer the file to the disk
    shutil.copy(src=str(xml_attr), dst=(MEDIA_ROOT + '/' + xml_file_path))

    # Update the run instance
    setattr(run_interop_instance, run_xml_fieldname, xml_file_path)
    print(f"Succesfully uploaded {xml_attr.name} to {xml_file_path}")
    return run_interop_instance


def upload_to_db(sample_object_list: [SampleObject], run_interop_data_object: RunInterOpDataObject, samplesheet: Path):
    """
    Takes list of fully populated SampleObjects + path to SampleSheet and uploads to the database
    TODO: Factor out a lot of this code into little functions. It's getting unwieldy.
    """

    for sample_object in sample_object_list:
        # PROJECT
        project, p_created = Project.objects.get_or_create(project_id=sample_object.project_id,
                                                           defaults={
                                                               # Default to admin ownership
                                                               'project_owner': User.objects.get(username="admin")
                                                           })
        if p_created:
            # Create admin relationship to project immediately
            UserProjectRelationship.objects.create(project_id=project, user_id=User.objects.get(username="admin"))
            print(f"\nCreated project '{project}'")

        # RUN
        run, r_created = Run.objects.get_or_create(run_id=sample_object.run_id,
                                                   defaults={'sample_sheet': ''})
        run_interop, ri_created = RunInterOpData.objects.get_or_create(run_id=run,
                                                                       defaults={})
        if r_created:
            print(f"\nCreated run '{run}'")
            samplesheet_path = upload_run_file(instance=run, filename=samplesheet.name)
            os.makedirs(os.path.dirname(MEDIA_ROOT + '/' + samplesheet_path), exist_ok=True)
            shutil.copy(str(samplesheet), (MEDIA_ROOT + '/' + samplesheet_path))
            run.sample_sheet = samplesheet_path
            run.save()
        if ri_created:
            # Upload InterOp files
            run_interop_data_field_list = [
                'control_metrics',
                'errormetrics',
                'extractionmetrics',
                'extractionmetrics',
                'indexmetrics',
                'qmetrics2030',
                'qmetricsbylane',
                'qmetrics',
                'tilemetrics'
            ]
            for field in run_interop_data_field_list:
                run_interop = upload_run_interop_data(run_interop_instance=run_interop,
                                                      run_interop_data_object=run_interop_data_object,
                                                      run_interop_model_fieldname=field)

            # Upload XML files
            xml_field_list = ['runinfoxml', 'runparametersxml']
            for field in xml_field_list:
                run_interop = upload_run_xml_file(run_interop_instance=run_interop,
                                                  run_interop_data_object=run_interop_data_object,
                                                  run_xml_fieldname=field)
            # Save the changes to the run_interop model instance
            run_interop.save()

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
        if sl_created:
            sample_log_attribute_list = [
                'number_reads',
                'sample_yield',
                'r1_qualityscoresum',
                'r2_qualityscoresum',
                'r1_trimmedbases',
                'r2_trimmedbases',
                'r1_yield',
                'r2_yield',
                'r1_yieldq30',
                'r2_yieldq30'
            ]
            for attribute in sample_log_attribute_list:
                setattr(sample_log, attribute, getattr(sample_object, attribute))
            sample_log.save()
