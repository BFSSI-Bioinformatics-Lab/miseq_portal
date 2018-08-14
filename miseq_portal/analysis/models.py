from django.db import models
from core.models import TimeStampedModel
from miseq_viewer.models import Sample


# Create your models here.
class SampleAnalysisGroup(TimeStampedModel):
    """
    Temporary table to store Samples destined for analysis.
    Should be cleared out whenever an analysis is submitted.
    """
    sample_id = models.OneToOneField(Sample, on_delete=models.CASCADE, primary_key=True)
    analysis_type = models.CharField(max_length=256, blank=True)

    def __str__(self):
        return self.sample_id
