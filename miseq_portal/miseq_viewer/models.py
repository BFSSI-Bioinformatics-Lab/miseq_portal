from pathlib import Path
from django.db import models
from django.core.exceptions import ValidationError

from core.models import TimeStampedModel
from miseq_portal.users.models import User

from dataclasses import dataclass


def validate_sample_id(value: str, length: int = 15):
    """
    Strict validation of BMH Sample ID
    :param value: sample_id
    :param length: expected length of string
    """
    if len(value) != length:
        raise ValidationError(f"Sample ID '{value}' does not meet the expected length of 15 characters. "
                              f"Sample ID must be in the following format: 'BMH-2018-000001'")

    components = value.split("-")
    if len(components) != 3:
        raise ValidationError(f"Sample ID '{value}' does not appear to meet expected format. "
                              f"Sample ID must be in the following format: 'BMH-2018-000001'")
    elif components[0] != "BMH":
        raise ValidationError(f"BMH component of Sample ID ('{components[0]}') does not equal expected 'BMH'")
    elif not components[1].isdigit() or len(components[1]) != 4:
        raise ValidationError(f"YEAR component of Sample ID ('{components[1]}') does not equal expected 'YYYY' format")
    elif not components[2].isdigit() or len(components[2]) != 6:
        raise ValidationError(f"ID component of Sample ID ('{components[2]}') does not equal expected 'XXXXXX' format")


def upload_run_file(instance, filename):
    return f'uploads/runs/{instance.run_id}/{filename}'


def upload_interop_file(instance, filename):
    return f'uploads/runs/{instance.run_id}/InterOp/{filename}'


def upload_interop_dir(instance):
    return f'uploads/runs/{instance.run_id}/InterOp/'


def upload_reads(instance, filename):
    """
    TODO: Research and fix the below described bug
    There is a bizarre bug when serving .fastq.gz files. When accessing a media file via the browser, e.g.
    http://192.168.1.61:8000/media/uploads/runs/20180709_WGS_M01308/BMH-2018-000049/something.fastq.gz, the file will
    download only a partial, UNCOMPRESSED version of the file. Changing the extension from .gz to .zip allows the file
    to be fully downloaded, though when the user tries to open it, they will receive an error from their decompression
    program - the fix is to then change the extension back to .gz.

    :param instance:
    :param filename:
    :return:
    """
    return f'uploads/runs/{instance.run_id}/{instance.sample_id}/{filename}'


@dataclass
class SampleDataObject:
    """Dataclass to store metadata for a sample"""

    # Must be instantiated with these attributes
    sample_id: str
    run_id: str
    project_id: str
    sample_name: str

    # Updated later in the lifecycle
    fwd_read_path: Path = None
    rev_read_path: Path = None
    number_reads: int = None
    sample_yield: int = None
    r1_qualityscoresum: int = None
    r2_qualityscoresum: int = None
    r1_trimmedbases: int = None
    r2_trimmedbases: int = None
    r1_yield: int = None
    r2_yield: int = None
    r1_yieldq30: int = None
    r2_yieldq30: int = None


@dataclass
class RunDataObject:
    """
    Dataclass to store metadata for a run
    """
    run_id: str

    interop_dir: Path = None
    sample_sheet: Path = None
    json_stats_file: Path = None
    runinfoxml: Path = None
    runparametersxml: Path = None
    control_metrics: Path = None
    correctedintmetrics: Path = None
    errormetrics: Path = None
    extractionmetrics: Path = None
    indexmetrics: Path = None
    qmetrics2030: Path = None
    qmetricsbylane: Path = None
    qmetrics: Path = None
    tilemetrics: Path = None
    logfiles: list = None


# Create your models here.
class Project(TimeStampedModel):
    """
    Each Sample must be associated with a Project.
    """
    project_id = models.CharField(max_length=256, unique=True)
    project_owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.project_id

    class Meta:
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'


class UserProjectRelationship(TimeStampedModel):
    ACCESS_LEVELS = (
        ('MANAGER', 'Manager'),  # Delete, modify
        ('USER', 'User'),  # View
        ('ADMIN', 'Admin'),  # Same as MANAGER
        ('NONE', 'None'),  # No access
    )
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='relationship_project', null=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name='relationship_user', null=True)
    access_level = models.CharField(max_length=32, choices=ACCESS_LEVELS, default='NONE')

    def __str__(self):
        return str(self.project_id) + ':' + str(self.user_id)

    class Meta:
        verbose_name = 'UserProjectRelationship'
        verbose_name_plural = 'UserProjectRelationships'


class Run(TimeStampedModel):
    """
    Stores information relating to a single BMH run. An individual Sample must be associated with a Run.
    """
    run_id = models.CharField(max_length=256, unique=True)
    sample_sheet = models.FileField(upload_to=upload_run_file, blank=True, max_length=1000)
    runinfoxml = models.FileField(upload_to=upload_run_file, blank=True, null=True, max_length=1000)
    runparametersxml = models.FileField(upload_to=upload_run_file, blank=True, null=True, max_length=1000)
    interop_directory_path = models.CharField(unique=True, blank=True, null=True, max_length=1000)

    def __str__(self):
        return str(self.run_id)

    def get_interop_directory(self) -> Path:
        return Path(self.interop_directory_path)

    class Meta:
        verbose_name = 'Run'
        verbose_name_plural = 'Runs'


class RunInterOpData(TimeStampedModel):
    run_id = models.OneToOneField(Run, on_delete=models.CASCADE, primary_key=True)

    control_metrics = models.FileField(upload_to=upload_interop_file, blank=True, null=True, max_length=1000)
    correctedintmetrics = models.FileField(upload_to=upload_interop_file, blank=True, null=True, max_length=1000)
    errormetrics = models.FileField(upload_to=upload_interop_file, blank=True, null=True, max_length=1000)
    extractionmetrics = models.FileField(upload_to=upload_interop_file, blank=True, null=True, max_length=1000)
    indexmetrics = models.FileField(upload_to=upload_interop_file, blank=True, null=True, max_length=1000)
    qmetrics2030 = models.FileField(upload_to=upload_interop_file, blank=True, null=True, max_length=1000)
    qmetricsbylane = models.FileField(upload_to=upload_interop_file, blank=True, null=True, max_length=1000)
    qmetrics = models.FileField(upload_to=upload_interop_file, blank=True, null=True, max_length=1000)
    tilemetrics = models.FileField(upload_to=upload_interop_file, blank=True, null=True, max_length=1000)

    def __str__(self):
        return str(self.run_id) + "_InterOp"

    class Meta:
        verbose_name = 'RunInterOpData'
        verbose_name_plural = 'RunInterOpData'


class Sample(TimeStampedModel):
    """
    Stores basic information relating to a single BMH sample (i.e. R1, R2, corresponding assembly, etc.)
    - Must follow the BMH-YYYY-ZZZZZZ format, e.g. "BMH-2018-000001"
    - Each Sample must be associated with a Project + Run
    """
    sample_id = models.CharField(max_length=15, unique=True, validators=[validate_sample_id])
    sample_name = models.CharField(max_length=64, unique=False, blank=True)
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE)
    run_id = models.ForeignKey(Run, on_delete=models.CASCADE)

    fwd_reads = models.FileField(upload_to=upload_reads, blank=True, max_length=1000)
    rev_reads = models.FileField(upload_to=upload_reads, blank=True, max_length=1000)

    def __str__(self):
        return self.sample_id

    class Meta:
        verbose_name = 'Sample'
        verbose_name_plural = 'Samples'


class SampleLogData(TimeStampedModel):
    """
    Stores Sample metadata derived from Stats.json
    """
    sample_id = models.OneToOneField(Sample, on_delete=models.CASCADE, primary_key=True)
    number_reads = models.BigIntegerField(blank=True, null=True)
    sample_yield = models.BigIntegerField(blank=True, null=True)

    # R1
    r1_qualityscoresum = models.BigIntegerField(blank=True, null=True)
    r1_trimmedbases = models.BigIntegerField(blank=True, null=True)
    r1_yield = models.BigIntegerField(blank=True, null=True)
    r1_yieldq30 = models.BigIntegerField(blank=True, null=True)

    # R2
    r2_qualityscoresum = models.BigIntegerField(blank=True, null=True)
    r2_trimmedbases = models.BigIntegerField(blank=True, null=True)
    r2_yield = models.BigIntegerField(blank=True, null=True)
    r2_yieldq30 = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return str(self.sample_id)

    def sample_yield_mbp(self):
        if self.sample_yield is not None:
            return float(self.sample_yield / 1000000)

    class Meta:
        verbose_name = 'SampleLogData'
        verbose_name_plural = 'SampleLogData'
