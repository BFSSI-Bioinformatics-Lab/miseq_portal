from django.db import models
from pathlib import Path
from django.utils import timezone
from miseq_portal.analysis.tools.sendsketch import get_top_sendsketch_hit
from miseq_portal.core.models import TimeStampedModel
from miseq_portal.miseq_viewer.models import Sample
from miseq_portal.users.models import User


def upload_analysis_file(instance, filename):
    return f'uploads/runs/{instance.run_id}/Analysis/{filename}'


class AnalysisGroup(models.Model):
    job_choices = (
        ('SendSketch', 'SendSketch'),
        ('Prokka', 'Prokka'),
        ('Mash', 'Mash'),
    )
    job_type = models.CharField(choices=job_choices, max_length=50, blank=False, default="SendSketch")

    status_choices = (
        ('Queued', 'Queued'),
        ('Working', 'Working'),
        ('Complete', 'Complete'),
        ('Failed', 'Failed'),
    )
    job_status = models.CharField(choices=status_choices, max_length=50, blank=False, default='Queued')
    group_name = models.CharField(max_length=128, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analysis Group {str(self.id)} ({str(self.user)})"


class AnalysisSample(models.Model):
    sample_id = models.ForeignKey(Sample, on_delete=models.CASCADE)
    group_id = models.ForeignKey(AnalysisGroup, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


class SampleAnalysisTemporaryGroup(models.Model):
    """
    TODO: DEPRECATED. Delete this model and corresponding table in DB. Make sure this is done correctly!
    Temporary table to store Samples destined for analysis.
    Should be cleared out whenever an analysis is submitted.
    """
    sample_id = models.ForeignKey(Sample, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # TODO: Consider making this amenable to submitting multiple jobs at once
    job_choices = (
        ('SendSketch', 'SendSketch'),
        ('Prokka', 'Prokka'),
        ('Mash', 'Mash'),
    )
    job_type = models.CharField(choices=job_choices, max_length=50, blank=True)

    def __str__(self):
        return str(self.sample_id)


class SendsketchResult(TimeStampedModel):
    sample_id = models.OneToOneField(Sample, on_delete=models.CASCADE, primary_key=True)
    sendsketch_result_file = models.FileField(upload_to=upload_analysis_file, blank=True, max_length=1000)

    def __str__(self):
        return str(self.sample_id)

    def get_top_hit(self):
        top_hit = get_top_sendsketch_hit(sendsketch_result_file=Path(str(self.sendsketch_result_file)))
        return top_hit
