from __future__ import absolute_import, unicode_literals
from celery import shared_task
from pathlib import Path
from config.settings.base import MEDIA_ROOT

from miseq_portal.miseq_viewer.models import Sample
from miseq_portal.analysis.models import AnalysisGroup, AnalysisSample, SendsketchResult, upload_analysis_file
from miseq_portal.analysis.tools.sendsketch import run_sendsketch, get_top_sendsketch_hit

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

    if job_type == 'SendSketch':
        logger.info(f"Starting {job_type} job for {user} for samples in group_id:{group_id}")
        for sample_instance in analysis_samples:
            # TODO: Factor this out into several functions
            fwd_reads = Path(MEDIA_ROOT) / str(sample_instance.sample_id.fwd_reads)
            rev_reads = Path(MEDIA_ROOT) / str(sample_instance.sample_id.rev_reads)
            outpath = Path(MEDIA_ROOT) / Path(
                str(sample_instance.sample_id.fwd_reads)).parent / 'SendSketch_results.txt'
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
        logger.info(f"Analysis for {analysis_group} completed")
        analysis_group.job_status = 'Complete'
        analysis_group.save()
