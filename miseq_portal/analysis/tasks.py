from __future__ import absolute_import, unicode_literals

import logging
import os
import shutil
from pathlib import Path

import pandas as pd
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.utils.dateparse import parse_date

from config.settings.base import MEDIA_ROOT
from miseq_portal.analysis.models import AnalysisGroup, AnalysisSample, \
    SendsketchResult, MobSuiteAnalysisGroup, MobSuiteAnalysisPlasmid, RGIResult, RGIGroupResult, MashResult, \
    ConfindrGroupResult, ConfindrResult, upload_analysis_file, upload_mobsuite_file, upload_group_analysis_file
from miseq_portal.analysis.tools.assemble_run import assembly_pipeline, call_qualimap, \
    extract_coverage_from_qualimap_results, assembly_cleanup, run_quast, get_quast_df, upload_sampleassembly_data, \
    prodigal_pipeline
from miseq_portal.analysis.tools.plasmid_report import call_mob_recon
from miseq_portal.analysis.tools.rgi import call_rgi_main, call_rgi_heatmap
from miseq_portal.analysis.tools.sendsketch import run_sendsketch, get_top_sendsketch_hit
from miseq_portal.miseq_viewer.models import Sample, SampleAssemblyData

MEDIA_ROOT = Path(MEDIA_ROOT)

logger = logging.getLogger('django')


@shared_task(serializer='json')
def submit_analysis_job(analysis_group: AnalysisGroup):
    """
    Given an AnalysisGroup, retrieves all AnalysisSample members and runs an asynchronous call to the specified job_type
    :param analysis_group: Instance of AnalysisGroup object
    :return: Instance of AnalysisGroup updated by this method
    """
    analysis_group = AnalysisGroup.objects.get(id=analysis_group)
    job_type = analysis_group.job_type
    group_id = analysis_group.id
    user = analysis_group.user
    analysis_samples = AnalysisSample.objects.filter(group_id=group_id)

    # Update job status from Queued to Working
    analysis_group.job_status = 'Working'
    analysis_group.save()

    logger.info(f"Starting {job_type} job for user '{user}' for samples in group ID {group_id}")

    # TODO: Implement handling for failed jobs so they actually switch over to 'FAILED' instead of 'Working' forever

    # Iterate over each sample instance and pass them to according method depending on job type
    if job_type == 'SendSketch':
        [submit_sendsketch_job(sample_instance) for sample_instance in analysis_samples]
    elif job_type == 'MobRecon':
        [submit_mob_recon_job(sample_instance) for sample_instance in analysis_samples]
    elif job_type == 'Confindr':
        submit_confindr_job(analysis_group=analysis_group)
    elif job_type == 'RGI':
        rgi_sample_list = [submit_rgi_job(sample_instance) for sample_instance in analysis_samples]
        # If multiple samples are selected, generate group analysis job
        if len(rgi_sample_list) > 1:
            submit_rgi_heatmap_job(analysis_group=analysis_group, rgi_sample_list=rgi_sample_list)

    logger.info(f'Analysis for Group {analysis_group} completed')
    analysis_group.job_status = 'Complete'
    analysis_group.save()


def submit_confindr_job(analysis_group: AnalysisGroup) -> ConfindrGroupResult:
    analysis_dir = Path(upload_group_analysis_file(analysis_group=analysis_group, filename='confindr'))
    outdir = MEDIA_ROOT / analysis_dir
    outdir.mkdir(parents=True, exist_ok=False)

    # Prepare reads directory
    reads_dir = outdir / 'reads'
    reads_dir.mkdir(parents=True, exist_ok=True)

    # Grab all of the reads and symlink them to the reads_dir
    analysis_samples = AnalysisSample.objects.filter(group_id=analysis_group)
    samples = [analysis_sample.sample_id for analysis_sample in analysis_samples]
    reads_dict = {sample: {'fwd_reads': MEDIA_ROOT / str(sample.fwd_reads),
                           'rev_reads': MEDIA_ROOT / str(sample.rev_reads)}
                  for sample in samples}

    # Create symlinks. Note that these are being renamed to stricly the sample ID + direction
    for sample_id, reads in reads_dict.items():
        fwd_dst = reads_dir / f"{sample_id}_R1.fastq.gz"
        rev_dst = reads_dir / f"{sample_id}_R2.fastq.gz"
        fwd_dst.symlink_to(reads['fwd_reads'])
        rev_dst.symlink_to(reads['rev_reads'])

    # Create group instance
    confindr_group_result = ConfindrGroupResult.objects.create(analysis_group=analysis_group)

    # Run confindr on input read directory
    report, logfile = confindr_group_result.call_confindr(reads_dir=reads_dir, outdir=outdir)

    confindr_group_result.confindr_report = str(report)
    confindr_group_result.confindr_log = str(logfile)
    confindr_group_result.save()

    # Create and populate individual result objects
    report_path = MEDIA_ROOT / str(confindr_group_result.confindr_report)
    report_df = pd.read_csv(report_path)
    logger.info(f"report_path: {report_path}")

    for analysis_sample in analysis_samples:
        contam_csv = outdir / f"{analysis_sample.sample_id}_contamination.csv"
        rmlst_csv = outdir / f"{analysis_sample.sample_id}_rmlstcsv"
        confindr_result = ConfindrResult.objects.create(analysis_sample=analysis_sample,
                                                        contamination_csv=str(contam_csv),
                                                        rmlst_csv=str(rmlst_csv))
        confindr_result.save()

        # Filter to only sample of interest
        df = report_df[report_df['Sample'] == str(analysis_sample.sample_id)].reset_index()

        # Populate ConfindrResult object
        if not df.empty:
            try:
                confindr_result.genus = str(df['Genus'][0])
                confindr_result.num_contam_snvs = int(df['NumContamSNVs'][0])
                confindr_result.contam_status = str(df['ContamStatus'][0])
                confindr_result.percent_contam = float(df['PercentContam'][0])
                confindr_result.percent_contam_std_dev = float(df['PercentContamStandardDeviation'][0])
                confindr_result.bases_examined = int(df['BasesExamined'][0])
                confindr_result.database_download_date = parse_date(df['DatabaseDownloadDate'][0])
            except BaseException as e:
                logger.warning(f"Something is wrong with the Confindr report for {analysis_sample.sample_id}")
                logger.warning(e)

                confindr_result.genus = None
                confindr_result.num_contam_snvs = None
                confindr_result.contam_status = None
                confindr_result.percent_contam = None
                confindr_result.percent_contam_std_dev = None
                confindr_result.bases_examined = None
                confindr_result.database_download_date = None

            confindr_result.save()

    return confindr_group_result


def submit_rgi_heatmap_job(analysis_group: AnalysisGroup, rgi_sample_list: [RGIResult]) -> RGIGroupResult:
    """
    Given an input AnalysisGroup instance and list of RGIResult instances, calls 'rgi heatmap' command on them all
    :param analysis_group: Instance of AnalysisGroup object
    :param rgi_sample_list: List of RGIResult object instances
    :return: Populated RGIGroupResult object generated by the method
    """
    # outdir = MEDIA_ROOT / Path(upload_group_analysis_file(analysis_group=analysis_group, filename='x')).parent
    analysis_dir = Path(upload_group_analysis_file(analysis_group=analysis_group, filename='x')).parent
    outdir = MEDIA_ROOT / analysis_dir
    outdir.mkdir(parents=True, exist_ok=False)

    # Create object instance
    rgi_group_result = RGIGroupResult.objects.create(analysis_group=analysis_group)

    # Collect results
    rgi_json_dir, rgi_txt_dir = gather_rgi_results(rgi_sample_list=rgi_sample_list, outdir=outdir)

    # Zip the gathered JSON and TXT result files
    rgi_json_zip = zip_rgi_results(rgi_group_result=rgi_group_result, result_dir=rgi_json_dir, result_type='json')
    rgi_txt_zip = zip_rgi_results(rgi_group_result=rgi_group_result, result_dir=rgi_txt_dir, result_type='txt')

    png_out = call_rgi_heatmap(rgi_json_dir=rgi_json_dir, outdir=outdir, analysis_group=analysis_group)
    if png_out is None:
        logger.info(f"ERROR: Could not generate heatmap for {analysis_group}")
    else:
        rgi_group_result.rgi_heatmap_result = upload_group_analysis_file(analysis_group=analysis_group,
                                                                         filename=png_out.name)
    # Update fields for the model
    rgi_group_result.rgi_json_results_zip = upload_group_analysis_file(analysis_group=analysis_group,
                                                                       filename=rgi_json_zip.name)
    rgi_group_result.rgi_txt_results_zip = upload_group_analysis_file(analysis_group=analysis_group,
                                                                      filename=rgi_txt_zip.name)
    rgi_group_result.save()
    return rgi_group_result


def submit_rgi_job(sample_instance: AnalysisSample) -> RGIResult:
    """
    Given an input AnalysisSample instance, runs RGI and stores result in the database
    :param sample_instance: Instance of AnalysisSample object
    :return: Populated RGIResult object generated by the method
    """
    logger.info(f"Received RGI job request for {sample_instance}")
    assembly_instance = SampleAssemblyData.objects.get(sample_id=sample_instance.sample_id)
    rgi_dir_name = f'RGI_{sample_instance.user}_{sample_instance.pk}'
    root_sample_instance = Sample.objects.get(sample_id=sample_instance.sample_id)
    outdir = MEDIA_ROOT / Path(str(sample_instance.sample_id.fwd_reads)).parent / rgi_dir_name

    if not assembly_instance.assembly_exists():
        logger.warning(f"Could not find assembly for {assembly_instance} - cannot proceed with job")
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
    return rgi_result_object


def submit_mob_recon_job(sample_instance: AnalysisSample) -> MobSuiteAnalysisGroup:
    """
    Given an input AnalysisSample instance, runs Mob Recon and stores result in the database
    :param sample_instance: Instance of AnalysisSample object
    :return: Populated MobSuiteAnalysisGroup object generated by the method
    """
    logger.info(f"Running Mob Suite on {sample_instance}")
    assembly_instance = SampleAssemblyData.objects.get(sample_id=sample_instance.sample_id)
    mobsuite_dir_name = f'mob_suite_{sample_instance.user}_{sample_instance.pk}'
    outdir = MEDIA_ROOT / Path(str(sample_instance.sample_id.fwd_reads)).parent / mobsuite_dir_name
    root_sample_instance = Sample.objects.get(sample_id=sample_instance.sample_id)

    if not assembly_instance.assembly_exists():
        logger.warning(f"Could not find assembly for {assembly_instance} - cannot proceed with job")
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
    mob_suite_analysis_group.mobtyper_aggregate_report = upload_mobsuite_file(
        root_sample_instance, mob_recon_data_object.mobtyper_aggregate_report.name, mobsuite_dir_name=mobsuite_dir_name)
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


def submit_sendsketch_job(sample_instance: AnalysisSample) -> SendsketchResult:
    """
    Given an input AnalysisSample instance, runs SendSketch and stores result in the database
    :param sample_instance: Instance of AnalysisSample object
    :return: Populated SendsketchResult object generated by the method
    """
    logger.info(f"Running Sendsketch on {sample_instance}")
    fwd_reads = MEDIA_ROOT / str(sample_instance.sample_id.fwd_reads)
    rev_reads = MEDIA_ROOT / str(sample_instance.sample_id.rev_reads)
    sendsketch_filename = f'{sample_instance.user}_{sample_instance.pk}_SendSketch_results.txt'
    sample_folder = MEDIA_ROOT / Path(str(sample_instance.sample_id.fwd_reads)).parent
    outpath = sample_folder / sendsketch_filename
    parent_sample = Sample.objects.get(sample_id=sample_instance.sample_id)

    sendsketch_result_file = run_sendsketch(fwd_reads=fwd_reads, rev_reads=rev_reads, outpath=outpath)
    sendsketch_object, sendsketch_object_created = SendsketchResult.objects.get_or_create(sample_id=parent_sample)

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
                                                                    filename=sendsketch_result_file.name)
    sendsketch_object.save()
    logger.info(f"Saved {sendsketch_object} successfully")
    return sendsketch_object


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
        logger.warning(f"Could not retrieve {sample_object_id} - does not exist. Skipping assembly.")
        return

    # Get/create SampleAssemblyData instance
    sample_assembly_instance, sa_created = SampleAssemblyData.objects.get_or_create(sample_id=sample_instance)
    if sa_created or str(sample_assembly_instance.assembly) == '' or sample_assembly_instance.assembly is None:
        """
        Check if it's even worth attempting the assembly by quickly checking the # of reads available.
        Note that this is contingent on there being # reads data available, which is not always the case.
        """
        try:
            if sample_instance.samplelogdata.number_reads < 1000 and sample_instance.samplelogdata.number_reads is not None:
                logger.warning(
                    f"Number of reads for sample {sample_instance} is less than 1000 "
                    f"(number_reads={sample_instance.samplelogdata.number_reads}). "
                    f"Skipping assembly step.")
                return
        except ObjectDoesNotExist:
            # Continue on like usual if samplelogdata doesn't exist yet
            pass

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
        # Do a check to make sure the assembly isn't empty
        if polished_assembly.stat().st_size == 0:
            logger.warning(f"The input assembly for {sample_instance} is empty. Skipping downstream analyses.")
            return

        # Run and parse Qualimap
        qualimap_result_file = call_qualimap(bamfile=bamfile, outdir=outdir)
        mean_coverage, std_coverage = extract_coverage_from_qualimap_results(qualimap_result_file=qualimap_result_file)

        # Clean up extraneous files and move the assembly to the root of the sample folder
        polished_assembly = assembly_cleanup(assembly_dir=outdir, assembly=polished_assembly)

        # Run and parse Quast
        report_file = run_quast(assembly=polished_assembly, outdir=outdir)
        quast_df = get_quast_df(report_file)

        # Run prodigal to get gene count
        num_predicted_genes = prodigal_pipeline(assembly=polished_assembly, outdir=outdir)

        # Push the data to the database for SampleAssemblyData
        sample_assembly_instance = upload_sampleassembly_data(sample_assembly_instance=sample_assembly_instance,
                                                              assembly=polished_assembly,
                                                              quast_df=quast_df,
                                                              mean_coverage=mean_coverage,
                                                              std_coverage=std_coverage,
                                                              num_predicted_genes=num_predicted_genes)
        sample_assembly_instance.save()
        logger.info(f"Saved assembly data for {sample_instance}")

        # Run Mash and save the results to a MashResult model instance
        if sample_assembly_instance.get_assembly_path().stat().st_size > 800:
            print(sample_assembly_instance.get_assembly_path().stat().st_size)
            logger.info(f"Running Mash on {sample_instance}...")
            mash_result_object = create_mash_result_object(assembly_instance=assemble_sample_instance,
                                                           sample=sample_instance)
            mash_result_object.save()
        else:
            logger.warning(f"The input assembly for {sample_instance} is too small to pass to Mash. Skipping.")
    else:
        logger.info(f"Assembly for {sample_assembly_instance.sample_id} already exists. Skipping.")


def create_mash_result_object(assembly_instance: SampleAssemblyData, sample: Sample) -> MashResult:
    mash_result_object, mr_created = MashResult.objects.get_or_create(sample_id=sample)
    top_mash_result, mash_result_file = mash_result_object.get_top_mash_hit()
    mash_result_object.mash_result_file = upload_analysis_file(sample,
                                                               filename=mash_result_file.name,
                                                               analysis_folder='assembly')
    if top_mash_result is not None:
        mash_result_object.top_hit = top_mash_result['hit']
        mash_result_object.top_identity = top_mash_result['identity']
        mash_result_object.top_query_id = top_mash_result['query_id']
        logger.info(f"Top mash hit: {mash_result_object.top_hit}")
    else:
        logger.warning(f"WARNING: Mash failed for {assembly_instance}. This is likely due to poor assembly quality.")

    logger.info(f"Mash complete for {assembly_instance}")
    return mash_result_object


def gather_rgi_results(rgi_sample_list: [RGIResult], outdir: Path) -> tuple:
    """
    Symlinks RGI result files to a single destination folder -- required for rgi heatmap command
    :param rgi_sample_list: List containing RGIResult object instances
    :param outdir: Destination directory for result files
    :return: Tuple containing paths to (json directory, text directory)
    """
    json_dir = outdir / 'json'
    txt_dir = outdir / 'txt'
    json_dir.mkdir(parents=True, exist_ok=False)
    txt_dir.mkdir(parents=True, exist_ok=False)
    for rgi_sample in rgi_sample_list:
        src_json_path = Path(MEDIA_ROOT / str(rgi_sample.rgi_main_json_results))
        dst_json_path = Path(json_dir) / Path(str(rgi_sample.rgi_main_json_results)).name
        dst_json_path.symlink_to(src_json_path)

        src_txt_path = Path(MEDIA_ROOT / str(rgi_sample.rgi_main_text_results))
        dst_txt_path = Path(txt_dir) / Path(str(rgi_sample.rgi_main_text_results)).name
        dst_txt_path.symlink_to(src_txt_path)
    return json_dir, txt_dir


def zip_rgi_results(rgi_group_result: RGIGroupResult, result_dir: Path, result_type: str):
    """
    Compresses final RGI results (.json or .txt) into an archive
    :param rgi_group_result: RGIGroupResult object instance
    :param result_dir: Directory to zip
    :param result_type: String for naming the archive; typically either 'txt' or 'json'
    :return: Path to compressed zip file
    """
    outname = result_dir.parent / rgi_group_result.created.strftime(f"RGI_{result_type}_%Y%m%d")
    outzip = shutil.make_archive(base_name=str(outname), format='zip', base_dir=str(result_dir.name),
                                 root_dir=str(result_dir.parent))
    return Path(outzip)
