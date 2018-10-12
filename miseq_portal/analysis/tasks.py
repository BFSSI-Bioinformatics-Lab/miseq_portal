from __future__ import absolute_import, unicode_literals
import os
import shutil
from celery import shared_task
from pathlib import Path
from config.settings.base import MEDIA_ROOT
from miseq_portal.miseq_viewer.models import Sample, SampleAssemblyData
from miseq_portal.analysis.models import AnalysisGroup, AnalysisSample, \
    SendsketchResult, MobSuiteAnalysisGroup, MobSuiteAnalysisPlasmid, \
    upload_analysis_file, upload_mobsuite_file
from miseq_portal.analysis.tools.sendsketch import run_sendsketch, get_top_sendsketch_hit
from miseq_portal.analysis.tools.plasmid_report import call_mob_recon
import logging

logger = logging.getLogger('raven')


@shared_task()
def submit_analysis_job(analysis_group_id: AnalysisGroup):
    analysis_group = AnalysisGroup.objects.get(id=analysis_group_id)
    job_type = analysis_group.job_type
    group_id = analysis_group.id
    user = analysis_group.user
    analysis_samples = AnalysisSample.objects.filter(group_id=group_id)

    # Update job status from Queued to Working
    analysis_group.job_status = 'Working'
    analysis_group.save()

    logger.info(f"Starting {job_type} job for user '{user}' for samples in group ID {group_id}")
    if job_type == 'SendSketch':
        for sample_instance in analysis_samples:
            logger.info(f"Processing {sample_instance}")
            submit_sendsketch_job(sample_instance=sample_instance)
    elif job_type == 'MobRecon':
        for sample_instance in analysis_samples:
            logger.info(f"Processing {sample_instance}")
            submit_mob_recon_job(sample_instance=sample_instance)

    logger.info(f"Analysis for {analysis_group} completed")
    analysis_group.job_status = 'Complete'
    analysis_group.save()


def submit_mob_recon_job(sample_instance: AnalysisSample):
    assembly_instance = SampleAssemblyData.objects.get(sample_id=sample_instance.sample_id)
    mobsuite_dir_name = f'mob_suite_{sample_instance.user}_{sample_instance.pk}'
    outdir = Path(MEDIA_ROOT) / Path(str(sample_instance.sample_id.fwd_reads)).parent / mobsuite_dir_name
    root_sample_instance = Sample.objects.get(sample_id=sample_instance.sample_id)

    if not assembly_instance.assembly_exists():
        logger.error(f"Could not find assembly for {assembly_instance} - cannot proceed with job")
        return
    else:
        assembly_path = assembly_instance.get_assembly_path()

    # Remove previous analysis if it exists
    if outdir.exists():
        shutil.rmtree(outdir, ignore_errors=True)

    os.makedirs(outdir, exist_ok=True)
    mob_recon_data_object = call_mob_recon(assembly=assembly_path, outdir=outdir)

    # We now create a new MobSuiteAnalysisGroup entry in the db for the AnalysisSample instance
    mob_suite_analysis_group = MobSuiteAnalysisGroup.objects.create(analysis_sample=sample_instance)

    # Update database for MobSuiteAnalysisGroup
    mob_suite_analysis_group.contig_report = upload_mobsuite_file(root_sample_instance,
                                                                  mob_recon_data_object.contig_report.name,
                                                                  mobsuite_dir_name=mobsuite_dir_name)
    mob_suite_analysis_group.mobtyper_aggregate_report = upload_mobsuite_file(root_sample_instance,
                                                                              mob_recon_data_object.mobtyper_aggregate_report.name,
                                                                              mobsuite_dir_name=mobsuite_dir_name)
    mob_suite_analysis_group.save()

    # Update database for MobSuiteAnalysisPlasmid
    # Quit early if there aren't any plasmids. This could potentially occur even earlier.
    if len(mob_recon_data_object.plasmid_fasta_list) == 0:
        logger.warning(f"No plasmids detected by mob_recon for {assembly_instance}")
        return

    # Iterate over each plasmid and update entry in db accordingly
    for plasmid_fasta in mob_recon_data_object.plasmid_fasta_list:
        logger.info(f"Processing {plasmid_fasta}")
        mob_suite_plasmid_instance = MobSuiteAnalysisPlasmid.objects.create(
            sample_id=mob_suite_analysis_group.analysis_sample.sample_id,
            group_id=mob_suite_analysis_group,
        )

        logger.info(f"Creating new Mob Suite Plasmid object with {plasmid_fasta}")
        plasmid_db_path = upload_mobsuite_file(root_sample_instance, plasmid_fasta.name, mobsuite_dir_name)
        mob_suite_plasmid_instance.plasmid_fasta = plasmid_db_path

        # Pull data from mobtype_aggregate_report.txt and place it in the database
        attr_dict = {
            'num_contigs': 'num_contigs', 'total_length': 'total_length', 'gc': 'gc_content', 'rep_type(s)': 'rep_type',
            'rep_type_accession(s)': 'rep_type_accession', 'relaxase_type(s)': 'relaxase_type',
            'relaxase_type_accession(s)': 'relaxase_type_accession', 'PredictedMobility': 'predicted_mobility',
            'mash_nearest_neighbor': 'mash_nearest_neighbor', 'mash_neighbor_distance': 'mash_neighbor_distance',
            'mash_neighbor_cluster': 'mash_neighbor_cluster'
        }
        for df_key, model_attr in attr_dict.items():
            df_value = mob_suite_analysis_group.get_plasmid_attribute(
                plasmid_basename=plasmid_fasta.name,
                attribute=df_key)
            setattr(mob_suite_plasmid_instance,
                    model_attr,
                    df_value)
        # Save instance
        mob_suite_plasmid_instance.save()


def submit_sendsketch_job(sample_instance: AnalysisSample):
    fwd_reads = Path(MEDIA_ROOT) / str(sample_instance.sample_id.fwd_reads)
    rev_reads = Path(MEDIA_ROOT) / str(sample_instance.sample_id.rev_reads)
    sendsketch_filename = f'{sample_instance.user}_{sample_instance.pk}_SendSketch_results.txt'
    outpath = Path(MEDIA_ROOT) / Path(str(sample_instance.sample_id.fwd_reads)).parent / sendsketch_filename
    parent_sample = Sample.objects.get(sample_id=sample_instance.sample_id)

    sendsketch_result_file = run_sendsketch(fwd_reads=fwd_reads,
                                            rev_reads=rev_reads,
                                            outpath=outpath)
    sendsketch_object, sendsketch_object_created = SendsketchResult.objects.get_or_create(
        sample_id=parent_sample)

    if sendsketch_object_created:
        logger.info("Creating new SendSketch results object")
    else:
        logger.info("Overwriting existing SendSketch results object")

    # Get top hit df and populate the database with results
    df = get_top_sendsketch_hit(sendsketch_result_file=sendsketch_result_file)
    sendsketch_object.top_ANI = df['ANI'][0]
    sendsketch_object.top_Contam = df['Contam'][0]
    sendsketch_object.top_gSize = df['gSize'][0]
    sendsketch_object.top_taxName = df['taxName'][0]
    sendsketch_object.top_TaxID = df['TaxID'][0]

    # Correct the path to the result file
    root_sample_instance = Sample.objects.get(sample_id=sample_instance.sample_id)
    sendsketch_result_file = upload_analysis_file(root_sample_instance, sendsketch_result_file.name)

    # Update path to result file in database
    sendsketch_object.sendsketch_result_file = sendsketch_result_file
    sendsketch_object.save()
    logger.info(f"Saved {sendsketch_object} successfully")
