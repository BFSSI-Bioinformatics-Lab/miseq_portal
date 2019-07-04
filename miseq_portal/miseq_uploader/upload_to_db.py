import logging
import os
import shutil
from pathlib import Path
from typing import Union

from config.settings.base import MEDIA_ROOT
from miseq_portal.analysis.tasks import assemble_sample_instance
from miseq_portal.miseq_uploader.parse_miseq_analysis_folder import parse_miseq_folder
from miseq_portal.miseq_uploader.parse_samplesheet import generate_sample_objects, validate_sample_id, \
    extract_samplesheet_headers
from miseq_portal.miseq_uploader.parse_stats_json import stats_json_to_df
from miseq_portal.miseq_viewer.models import Project, UserProjectRelationship, Run, RunInterOpData, Sample, \
    SampleLogData, RunSamplesheet, SampleSheetSampleData, \
    upload_run_file, upload_reads, upload_interop_file, upload_interop_dir, SampleDataObject, \
    RunDataObject
from miseq_portal.users.models import User

logger = logging.getLogger('django')


def determine_run_type(sample_object_list: list) -> str:
    sample_types = []
    for sample_object in sample_object_list:
        sample_types.append(sample_object.sample_type)
    sample_types = list(set(sample_types))
    if len(sample_types) != 1:
        raise Exception(f"Something went wrong. The sample type should be consistent but it was not: {sample_types}")
    run_type = sample_types[0]
    return run_type


def check_for_ignore_run_file(miseq_dir: Path) -> bool:
    """
    Checks a run directory for a file called "portal.ignore", if it's present then the upload won't proceed.
    This ensures that junk data is not uploaded to the portal.

    If a run has been deemed unworthy of upload, add the portal.ignore file to the directory instead of deleting it.
    """
    ignore_run = False
    portal_ignore_globber = len(list(miseq_dir.glob("portal.ignore")))
    if portal_ignore_globber == 1:
        logger.info(f"Detected portal.ignore file in {miseq_dir}, skipping upload!")
        ignore_run = True
    return ignore_run


def receive_miseq_run_dir(miseq_dir: Path):
    logger.info(f'CHECKING MISEQ DIRECTORY')

    ignore_run = check_for_ignore_run_file(miseq_dir)
    if ignore_run:
        return

    miseq_dict = parse_miseq_folder(miseq_dir=miseq_dir)

    logger.info(f'CHECKING SAMPLESHEET AND RUN DETAILS')
    run_data_object = miseq_dict['run_data_object']
    sample_object_list = generate_sample_objects(samplesheet=run_data_object.sample_sheet)

    # Update SampleObjects with stats and reads
    sample_object_list = append_sample_object_reads(sample_dict=miseq_dict['sample_dict'],
                                                    sample_object_list=sample_object_list)
    sample_object_list = append_sample_object_stats(json_stats_file=run_data_object.json_stats_file,
                                                    sample_object_list=sample_object_list)

    # Assign run_type to run_data_object
    run_type = determine_run_type(sample_object_list)
    run_data_object.run_type = run_type

    # Perform one final validation of the sample IDs of the samples to be uploaded
    for sample_object in sample_object_list:
        if sample_object.sample_type == 'BMH':
            validate_sample_id(sample_object.sample_id)

    sample_object_list = upload_to_db(sample_object_list=sample_object_list,
                                      run_data_object=run_data_object)

    logger.info(f'UPLOAD COMPLETE')

    # Call assembly pipeline on all valid sample objects
    for sample_object in sample_object_list:
        if sample_object.sequencing_type == 'WGS':
            assemble_sample_instance.apply_async(args=[],
                                                 kwargs={'sample_object_id': sample_object.sample_id},
                                                 queue='assembly_queue')
            logger.info(f"Submitted {sample_object.sample_id} to assembly queue")
        else:
            logger.info(f"Sample {sample_object.sample_id} sequencing type is"
                        f" {sample_object.sequencing_type}, skipping assembly")
            continue


def append_sample_object_reads(sample_dict: dict, sample_object_list: [SampleDataObject]) -> [SampleDataObject]:
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


def append_sample_object_stats(json_stats_file: Path, sample_object_list: [SampleDataObject]) -> [SampleDataObject]:
    """
    Given a list of SampleObjects + the Stats.json file from the same run, appends those stats to the SampleDataObject
    """
    if json_stats_file is None:
        logger.info("WARNING: Cannot append sample stats for this run because no Stats.json file was provided")
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


def upload_run_data(run_instance: Union[Run, RunInterOpData], run_data_object: RunDataObject,
                    run_model_fieldname: str, interop_flag: bool) -> Union[Run, RunInterOpData]:
    # Check if the attribute exists, quit if it doesn't
    try:
        model_attr = getattr(run_data_object, run_model_fieldname)
    except AttributeError:
        raise AttributeError(f"Attribute {run_model_fieldname} does not exist.")

    if not os.path.isfile(str(model_attr)):
        logger.info(f"WARNING: Could not find {str(model_attr)}. Skipping.")
        return run_instance

    # Create destination path for InterOp file
    if interop_flag:
        run_file_path = upload_interop_file(run_instance, model_attr.name)
    else:
        run_file_path = upload_run_file(run_instance, model_attr.name)

    # Create InterOp directory for file if it doesn't already exist
    run_dir_path = os.path.dirname(MEDIA_ROOT + '/' + run_file_path)
    os.makedirs(run_dir_path, exist_ok=True)
    os.chmod(run_dir_path, 0o777)

    # Transfer the file to the disk
    shutil.copy(src=str(model_attr), dst=(MEDIA_ROOT + '/' + run_file_path))

    # Update the run instance
    setattr(run_instance, run_model_fieldname, run_file_path)
    logger.info(f"Succesfully uploaded {model_attr.name} to {run_file_path}")
    return run_instance


def db_create_project(sample_object: SampleDataObject):
    # PROJECT
    project_instance, p_created = Project.objects.get_or_create(project_id=sample_object.project_id,
                                                                defaults={
                                                                    # Default to admin ownership
                                                                    'project_owner': User.objects.get(
                                                                        username="admin")
                                                                })
    if p_created:
        # Create admin relationship to project immediately
        UserProjectRelationship.objects.create(project_id=project_instance,
                                               user_id=User.objects.get(username="admin"))
        logger.info(f"Created Project '{project_instance}'")
    else:
        logger.info(f"Project '{project_instance}' already exists")
    return project_instance


def db_create_run(sample_object: SampleDataObject, run_data_object: RunDataObject):
    run_instance, r_created = Run.objects.get_or_create(run_id=sample_object.run_id,
                                                        defaults={'sample_sheet': '',
                                                                  'runinfoxml': '',
                                                                  'runparametersxml': '',
                                                                  'run_type': '',
                                                                  'interop_directory_path': ''})

    if r_created:
        logger.info(f"Created Run '{run_instance}'")

        # Set run type of instance
        run_instance.run_type = run_data_object.run_type

        # Set interop_dir (no upload necessary, it's just a string path)
        interop_dir_path = upload_interop_dir(run_instance)
        run_instance.interop_directory_path = interop_dir_path
        logger.info(f'Set interop_directory_path to {interop_dir_path}')

        # Upload XML files + SampleSheet
        xml_field_list = ['runinfoxml', 'runparametersxml', 'sample_sheet']
        for field in xml_field_list:
            run_instance = upload_run_data(run_instance=run_instance,
                                           run_data_object=run_data_object,
                                           run_model_fieldname=field,
                                           interop_flag=False)
        # Save instance
        run_instance.save()
        logger.info(f"Saved {run_instance} to the database")
    else:
        logger.info(f"Run '{run_instance}' already exists, skipping")

    return run_instance


def db_create_run_interop(run_instance: Run, run_data_object: RunDataObject):
    run_interop_instance, ri_created = RunInterOpData.objects.get_or_create(run_id=run_instance,
                                                                            defaults={'control_metrics': '',
                                                                                      'correctedintmetrics': '',
                                                                                      'errormetrics': '',
                                                                                      'extractionmetrics': '',
                                                                                      'indexmetrics': '',
                                                                                      'qmetrics2030': '',
                                                                                      'qmetricsbylane': '',
                                                                                      'qmetrics': '',
                                                                                      'tilemetrics': ''})

    if ri_created:
        logger.info(f"Created RunInterop '{run_interop_instance}'")

        # Upload InterOp files
        run_interop_data_field_list = [
            'control_metrics',
            'correctedintmetrics',
            'errormetrics',
            'extractionmetrics',
            'indexmetrics',
            'qmetrics2030',
            'qmetricsbylane',
            'qmetrics',
            'tilemetrics'
        ]

        for field in run_interop_data_field_list:
            run_interop_instance = upload_run_data(run_instance=run_interop_instance,
                                                   run_data_object=run_data_object,
                                                   run_model_fieldname=field,
                                                   interop_flag=True)

        # Save the changes to the run_interop model instance
        run_interop_instance.save()
        logger.info(f"Saved {run_interop_instance} to the database")

        return run_interop_instance


def db_create_sample(sample_object: SampleDataObject, run_instance: Run, project_instance: Project):
    if project_instance is not None:
        sample_instance, s_created = Sample.objects.get_or_create(sample_id=sample_object.sample_id,
                                                                  defaults={'run_id': run_instance,
                                                                            'project_id': project_instance})
    else:
        # EXT sample creation - check if SAMPLE_NAME is already in the DB so duplicates aren't created
        sample_name_exists = Sample.objects.filter(sample_name=sample_object.sample_name).exists()
        if not sample_name_exists:
            sample_instance = Sample.objects.create(sample_type='EXT', run_id=run_instance)
            s_created = True
            sample_instance.sample_id = sample_instance.generate_sample_id()
            sample_instance.save()
        else:
            sample_instance = Sample.objects.filter(sample_name=sample_object.sample_name)[0]
            s_created = False

    if s_created:
        logger.info(f"Uploading {sample_object.sample_id}...")

        # Sample data + read handling
        fwd_read_path = upload_reads(sample_instance, sample_object.fwd_read_path.name)
        rev_read_path = upload_reads(sample_instance, sample_object.rev_read_path.name)
        read_dir_path = os.path.dirname(MEDIA_ROOT + '/' + fwd_read_path)
        os.makedirs(read_dir_path, exist_ok=True)
        os.chmod(read_dir_path, 0o777)
        shutil.copy(str(sample_object.fwd_read_path), os.path.dirname(MEDIA_ROOT + '/' + fwd_read_path))
        shutil.copy(str(sample_object.rev_read_path), os.path.dirname(MEDIA_ROOT + '/' + fwd_read_path))
        sample_instance.fwd_reads = fwd_read_path
        sample_instance.rev_reads = rev_read_path
        sample_instance.sample_name = sample_object.sample_name
        sample_instance.sequencing_type = sample_object.sequencing_type
        sample_instance.save()
    else:
        logger.info(f"Sample '{sample_instance}' already exists, skipping'")
    return sample_instance


def db_create_sample_log(sample_object: SampleDataObject, sample_instance: Sample):
    # Save sample stats
    sample_log_instance, sl_created = SampleLogData.objects.get_or_create(sample_id=sample_instance)
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
            setattr(sample_log_instance, attribute, getattr(sample_object, attribute))
        sample_log_instance.save()
    return sample_log_instance


def db_create_samplesheetsampledata(sample_instance: Sample, run_instance: Run):
    """ Create SampleSheetSampleData instance and populate with relevant data from SampleSheet """
    samplesheet = run_instance.sample_sheet
    samplesheetsampledata_instance, samplesheetsampledata_created = SampleSheetSampleData.objects.get_or_create(
        sample_id=sample_instance)
    if samplesheetsampledata_created:
        row = samplesheetsampledata_instance.extract_sample_row_from_samplesheet(
            samplesheet=(Path(MEDIA_ROOT) / str(samplesheet))
        )
        attr_dict = samplesheetsampledata_instance.samplesheet_row_to_dict(row=row)
        for attribute, value in attr_dict.items():
            setattr(samplesheetsampledata_instance, attribute, value)
        samplesheetsampledata_instance.save()
    else:
        logger.info(f"{samplesheetsampledata_instance} already exists! Skipping!")

    return samplesheetsampledata_instance


def db_create_runsamplesheet(run_instance: Run) -> RunSamplesheet:
    """ Create RunSamplesheet instance and populate with relevant data from SampleSheet """
    runsamplesheet_instance, run_created = RunSamplesheet.objects.get_or_create(run_id=run_instance)
    if run_created:
        attr_dict = extract_samplesheet_headers(samplesheet=Path(MEDIA_ROOT) / str(run_instance.sample_sheet))
        for attribute, value in attr_dict.items():
            setattr(runsamplesheet_instance, attribute, value)
        runsamplesheet_instance.save()
    return runsamplesheet_instance


def upload_to_db(sample_object_list: [SampleDataObject], run_data_object: RunDataObject) -> [SampleDataObject]:
    """ Takes list of fully populated SampleObjects + path to SampleSheet and uploads to the database """
    updated_sample_object_list = []
    for sample_object in sample_object_list:
        # PROJECT
        # Accomodate EXT samples -> project_instance is None if the sample is EXT
        if sample_object.sample_type == "BMH":
            project_instance = db_create_project(sample_object=sample_object)
        else:
            project_instance = None

        # RUN
        run_instance = db_create_run(sample_object=sample_object, run_data_object=run_data_object)

        # RUN SAMPLESHEET
        run_samplesheet_instance = db_create_runsamplesheet(run_instance=run_instance)

        # RUN INTEROP
        run_interop_instance = db_create_run_interop(run_instance=run_instance, run_data_object=run_data_object)

        # SAMPLE
        sample_instance = db_create_sample(sample_object=sample_object,
                                           run_instance=run_instance,
                                           project_instance=project_instance)
        updated_sample_object_list.append(sample_instance)

        # SAMPLE LOG
        sample_log_instance = db_create_sample_log(sample_object=sample_object, sample_instance=sample_instance)

        # SAMPLESHEET SAMPLE DATA
        samplesheetsampledata_instance = db_create_samplesheetsampledata(sample_instance=sample_instance,
                                                                         run_instance=run_instance)

    return updated_sample_object_list
