from __future__ import absolute_import, unicode_literals

import logging
import os
import shutil
from pathlib import Path

from celery import shared_task

from miseq_portal.analysis.models import AnalysisGroup, AnalysisSample, \
    SendsketchResult, MobSuiteAnalysisGroup, MobSuiteAnalysisPlasmid, RGIResult, \
    upload_analysis_file, upload_mobsuite_file
from miseq_portal.analysis.tools.assemble_run import logger, MEDIA_ROOT, assembly_pipeline, call_qualimap, \
    extract_coverage_from_qualimap_results, assembly_cleanup, run_quast, get_quast_df, upload_sampleassembly_data
from miseq_portal.analysis.tools.plasmid_report import call_mob_recon
from miseq_portal.analysis.tools.rgi import call_rgi_main
from miseq_portal.analysis.tools.sendsketch import run_sendsketch, get_top_sendsketch_hit
from miseq_portal.analysis.tools.sendsketch import sendsketch_tophit_pipeline, create_sendsketch_result_object
from miseq_portal.miseq_viewer.models import Sample, SampleAssemblyData

logger = logging.getLogger('django')


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

    # TODO: Impement handling for failed jobs so they actually switch over to 'FAILED' instead of 'Working' forever

    # Iterate over each sample instance and pass them to according method depending on job type
    for sample_instance in analysis_samples:
        logger.info(f"Processing {sample_instance}")
        if job_type == 'SendSketch':
            submit_sendsketch_job(sample_instance=sample_instance)
        elif job_type == 'MobRecon':
            submit_mob_recon_job(sample_instance=sample_instance)
        elif job_type == 'RGI':
            submit_rgi_job(sample_instance=sample_instance)

    logger.info(f"Analysis for {analysis_group} completed")
    analysis_group.job_status = 'Complete'
    analysis_group.save()


def submit_rgi_job(sample_instance: AnalysisSample):
    logger.info(f"Received RGI job request for {sample_instance}")
    assembly_instance = SampleAssemblyData.objects.get(sample_id=sample_instance.sample_id)
    rgi_dir_name = f'RGI_{sample_instance.user}_{sample_instance.pk}'
    root_sample_instance = Sample.objects.get(sample_id=sample_instance.sample_id)
    outdir = Path(MEDIA_ROOT) / Path(str(sample_instance.sample_id.fwd_reads)).parent / rgi_dir_name

    if not assembly_instance.assembly_exists():
        logger.error(f"Could not find assembly for {assembly_instance} - cannot proceed with job")
        return
    else:
        assembly_path = assembly_instance.get_assembly_path()

    # Remove previous analysis if it exists
    if outdir.exists():
        shutil.rmtree(outdir, ignore_errors=True)
    outdir.mkdir(parents=True)

    # Call RGI
    rgi_text_results, rgi_json_results = call_rgi_main(fasta=assembly_path, outdir=outdir,
                                                       sample_id=root_sample_instance.sample_id)

    # Populate database with results
    rgi_result_object = RGIResult.objects.create(analysis_sample=sample_instance)
    rgi_result_object.rgi_main_text_results = upload_analysis_file(instance=root_sample_instance,
                                                                   filename=rgi_text_results.name,
                                                                   analysis_folder=rgi_dir_name)
    rgi_result_object.rgi_main_json_results = upload_analysis_file(instance=root_sample_instance,
                                                                   filename=rgi_json_results.name,
                                                                   analysis_folder=rgi_dir_name)
    rgi_result_object.save()
    logger.info(f"Completed running RGI on {sample_instance}")


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
    outdir.mkdir(exist_ok=True)

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
    sample_folder = Path(MEDIA_ROOT) / Path(str(sample_instance.sample_id.fwd_reads)).parent
    outpath = sample_folder / sendsketch_filename
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
    try:
        df = get_top_sendsketch_hit(sendsketch_result_file=sendsketch_result_file)
        sendsketch_object.top_ANI = df['ANI'][0]
        sendsketch_object.top_Contam = df['Contam'][0]
        sendsketch_object.top_gSize = df['gSize'][0]
        sendsketch_object.top_taxName = df['taxName'][0]
        sendsketch_object.top_TaxID = df['TaxID'][0]
    except:
        sendsketch_object.top_ANI = None
        sendsketch_object.top_Contam = None
        sendsketch_object.top_gSize = None
        sendsketch_object.top_taxName = None
        sendsketch_object.top_TaxID = None

    # Correct the path to the result file
    root_sample_instance = Sample.objects.get(sample_id=sample_instance.sample_id)

    # Update path to result file in database
    sendsketch_object.sendsketch_result_file = upload_analysis_file(instance=root_sample_instance,
                                                                    filename=sendsketch_result_file.name,
                                                                    analysis_folder=sample_folder)
    sendsketch_object.save()
    logger.info(f"Saved {sendsketch_object} successfully")


@shared_task()
def assemble_sample_instance(sample_object_id: str):
    """
    Assembles a sample. Locates the sample in the database via sample_id.
    Must be called via assemble_sample_instance.delay(sample_object_id=sample_id) to queue in Celery
    :param sample_object_id: sample_id value, e.g. BMH-2017-000001
    """
    try:
        sample_instance = Sample.objects.get(sample_id=sample_object_id)
    except Sample.DoesNotExist:
        logger.error(f"Could not retrieve {sample_object_id} - does not exist. Skipping assembly.")
        return

    # Get/create SampleAssemblyData instance
    # TODO: Don't even attempt the assembly if the number_reads (if available) is less than 1000.
    sample_assembly_instance, sa_created = SampleAssemblyData.objects.get_or_create(sample_id=sample_instance)
    if sa_created or str(sample_assembly_instance.assembly) == '' or sample_assembly_instance.assembly is None:
        logger.info(f"Running assembly pipeline on {sample_instance}...")

        # Setup assembly directory on NAS
        outdir = MEDIA_ROOT / Path(str(sample_instance.fwd_reads)).parent / "assembly"
        # Delete any old assembly lying around without an attached database record
        if outdir.exists():
            shutil.rmtree(outdir)
        outdir.mkdir(exist_ok=True)
        os.chmod(outdir, 0o777)

        fwd_reads = MEDIA_ROOT / Path(str(sample_instance.fwd_reads))
        rev_reads = MEDIA_ROOT / Path(str(sample_instance.rev_reads))
        bamfile, polished_assembly = assembly_pipeline(
            fwd_reads=fwd_reads,
            rev_reads=rev_reads,
            outdir=outdir,
            sample_id=str(sample_instance.sample_id)
        )
        # Run and parse Qualimap
        qualimap_result_file = call_qualimap(bamfile=bamfile, outdir=outdir)
        mean_coverage, std_coverage = extract_coverage_from_qualimap_results(qualimap_result_file=qualimap_result_file)

        # Clean up extraneous files and move the assembly to the root of the sample folder
        polished_assembly = assembly_cleanup(assembly_dir=outdir, assembly=polished_assembly)

        # Run and parse Quast
        report_file = run_quast(assembly=polished_assembly, outdir=outdir)
        quast_df = get_quast_df(report_file)

        sendsketch_outpath = outdir / 'best_refseq_hit.txt'
        sendsketch_tophit_df = sendsketch_tophit_pipeline(fwd_reads=fwd_reads,
                                                          rev_reads=rev_reads,
                                                          outpath=sendsketch_outpath)

        # Run sendsketch and save the results to a SendsketchResult model instance
        sendsketch_result_object = create_sendsketch_result_object(sendsketch_tophit_df=sendsketch_tophit_df,
                                                                   sample_object=sample_instance)
        sendsketch_result_object.save()
        logging.info(f"Saved Sendsketch results for {sample_instance}")

        # Push the data to the database for SampleAssemblyData
        sample_assembly_instance = upload_sampleassembly_data(sample_assembly_instance=sample_assembly_instance,
                                                              assembly=polished_assembly,
                                                              quast_df=quast_df,
                                                              mean_coverage=mean_coverage,
                                                              std_coverage=std_coverage)
        sample_assembly_instance.save()
        logging.info(f"Saved assembly data for {sample_instance}")
    else:
        logger.info(f"Assembly for {sample_assembly_instance.sample_id} already exists. Skipping.")
