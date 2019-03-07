import logging

from django.db import models

from miseq_portal.core.models import TimeStampedModel
from miseq_portal.miseq_viewer.models import Sample
from miseq_portal.users.models import User

logger = logging.getLogger('django')


class Workbook(TimeStampedModel):
    """
    Base Workbook model for representing a group of samples
    """
    workbook_title = models.CharField(max_length=128, unique=False)
    workbook_description = models.CharField(max_length=512, unique=False)
    workbook_notes = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{str(self.pk)}: {self.workbook_title}"

    def workbook_samples(self):
        return WorkbookSample.objects.filter(workbook=self.id)

    class Meta:
        verbose_name = 'Workbook'
        verbose_name_plural = 'Workbooks'


class WorkbookSample(TimeStampedModel):
    """
    Model for storing a Sample that is associated with a Workbook.
    A workbook + sample pair must be unique, i.e. a sample cannot belong to the same workbook twice.
    """
    workbook = models.ForeignKey(Workbook, on_delete=models.CASCADE, related_name="workbook")
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name="sample")
    sample_notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.sample.sample_id} ({self.workbook.workbook_title})"

    class Meta:
        unique_together = ('workbook', 'sample')  # These two fields form a unique pair
        verbose_name = 'Workbook Sample'
        verbose_name_plural = 'Workbook Samples'
