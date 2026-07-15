import logging

import pandas as pd
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from miseq_portal.core.models import TimeStampedModel
from miseq_portal.miseq_viewer.models import Sample, Project

logger = logging.getLogger('django')


def upload_minion_run_file(instance, filename: str):
    """instance must be MinIONRun"""
    return f'uploads/minion_runs/{instance.run_id}/{filename}'


def upload_minion_reads(instance, filename: str):
    """instance must be MinIONSample"""
    return f'uploads/minion_runs/{instance.run_id}/{instance.sample_id}/{filename}'


def validate_hybrid_sample_id(value: str, length: int = 15):
    """
      Strict validation of Hybrid MiSeq/MinION Sample ID
      :param value: sample_id
      :param length: expected length of string
      """
    components = value.split("-")

    if len(value) != length:
        raise ValidationError(f"Hybrid Sample ID '{value}' does not meet the expected length of 15 characters. "
                              f"Hybrid Sample ID must be in the following format: 'MIN-2020-000001'")
    if len(components) != 3:
        raise ValidationError(f"Hybrid Sample ID '{value}' does not appear to meet expected format. "
                              f"Hybrid Sample ID must be in the following format: 'BMH-2018-000001'")
    elif components[0] != 'HYB':
        raise ValidationError(
            f"TEXT component of Hybrid Sample ID ('{components[0]}') does not equal expected 'MIN'")
    elif not components[1].isdigit() or len(components[1]) != 4:
        raise ValidationError(
            f"YEAR component of Hybrid Sample ID ('{components[1]}') does not equal expected 'YYYY' format")
    elif not components[2].isdigit() or len(components[2]) != 6:
        raise ValidationError(
            f"ID component of Hybrid Sample ID ('{components[2]}') does not equal expected 'XXXXXX' format")
    return True


def validate_minion_sample_id(value: str, length: int = 15):
    """
      Strict validation of BMH MinION Sample ID
      :param value: sample_id
      :param length: expected length of string
      """
    components = value.split("-")

    if len(value) != length:
        raise ValidationError(f"MinION Sample ID '{value}' does not meet the expected length of 15 characters. "
                              f"MinION Sample ID must be in the following format: 'MIN-2020-000001'")
    if len(components) != 3:
        raise ValidationError(f"MinION Sample ID '{value}' does not appear to meet expected format. "
                              f"MinION Sample ID must be in the following format: 'BMH-2018-000001'")
    elif components[0] != 'MIN' and components[0] != 'RDL':
        raise ValidationError(
            f"TEXT component of MinION Sample ID ('{components[0]}') does not equal expected 'MIN'")
    elif not components[1].isdigit() or len(components[1]) != 4:
        raise ValidationError(
            f"YEAR component of MinION Sample ID ('{components[1]}') does not equal expected 'YYYY' format")
    elif not components[2].isdigit() or len(components[2]) != 6:
        raise ValidationError(
            f"ID component of MinION Sample ID ('{components[2]}') does not equal expected 'XXXXXX' format")
    return True


class MinIONRun(TimeStampedModel):
    """
    Stores information relating to a single sequencing run
    """
    run_id = models.CharField(max_length=256, unique=True)

    @property
    def run_url(self) -> str:
        return reverse('miseq_viewer:miseq_viewer_run_detail', args=(self.pk,))

    @property
    def num_samples(self) -> int:
        return len(MinIONSample.objects.filter(run_id=self.pk))

    def __str__(self):
        return str(self.run_id)

    def __len__(self):
        return self.num_samples

    class Meta:
        verbose_name = 'MinION Run'
        verbose_name_plural = 'MinION Runs'


class MinIONRunSamplesheet(TimeStampedModel):
    sample_sheet = models.FileField(upload_to=upload_minion_run_file, blank=True, max_length=1000)
    run_id = models.OneToOneField(MinIONRun, on_delete=models.CASCADE, null=True, blank=True)

    def get_fields(self):
        return [(field.name, field.value_to_string(self)) for field in MinIONRunSamplesheet._meta.fields]

    def read_samplesheet(self):
        """ Method to read in an input .xlsx """
        df = pd.read_excel(self.sample_sheet)
        return df

    def get_run_id(self):
        df = self.read_samplesheet()
        run_id = df['Run_ID'][0]
        return run_id

    def set_run_id(self):
        run_id = self.get_run_id()
        created, run_object = MinIONRun.objects.get_or_create(run_id=run_id)
        if created and self.run_id is None:
            run_object.save()
            self.run_id = run_object
        self.save()

    class Meta:
        verbose_name = 'MinION Run Samplesheet'
        verbose_name_plural = 'MinION Run Samplesheets'

    def __str__(self):
        return str(self.run_id)


class MinIONSample(TimeStampedModel):
    # Basic sample info
    sample_id = models.CharField(max_length=15, unique=True, validators=[validate_minion_sample_id])
    sample_name = models.TextField(blank=True)
    long_reads = models.FileField(upload_to=upload_minion_reads, blank=True, max_length=1000)

    # Project/MinIONRun
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True)
    run_id = models.ForeignKey(MinIONRun, on_delete=models.CASCADE, blank=True, null=True)

    # Metadata from the samplesheet
    run_protocol = models.CharField(blank=True, max_length=1028)
    instrument_id = models.CharField(blank=True, max_length=1028)
    sequencing_kit = models.CharField(blank=True, max_length=1028)
    flowcell_type = models.CharField(blank=True, max_length=1028)
    read_type = models.CharField(blank=True, max_length=1028)
    user = models.CharField(blank=True, max_length=1028)

    class Meta:
        verbose_name = 'MinION Sample'
        verbose_name_plural = 'MinION Samples'

    def __str__(self):
        return str(self.sample_id)


class MiSeqMinIONPair(models.Model):
    sample_id = models.CharField(max_length=15, unique=True, validators=[validate_hybrid_sample_id])
    miseq_sample = models.ForeignKey(Sample, on_delete=models.CASCADE)
    minion_sample = models.ForeignKey(MinIONSample, on_delete=models.CASCADE)
