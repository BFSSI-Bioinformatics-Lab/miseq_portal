from django.db import models
from django.core.exceptions import ValidationError

from core.models import TimeStampedModel


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


# Create your models here.
class Project(TimeStampedModel):
    """
    Each project contains runs, and each run contains samples
    """
    project_id = models.CharField(max_length=256, unique=True)

    def __str__(self):
        return f"{self.project_id}"


class Run(TimeStampedModel):
    """
    Stores information relating to a single BMH run
    - Each Run must be associated with a Project
    """
    run_id = models.CharField(max_length=256, unique=True)
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE)

    # TODO: upload_to uploads/projects/<project_id>/runs/<run_id>/SampleSheet.csv
    # sample_sheet = models.FileField()

    # TODO: upload_to uploads/projects/<project_id>/runs/<run_id>/SampleSheet.csv
    # interop_dir = models.FilePathField(path=None, allow_folders=True, allow_files=False)

    def __str__(self):
        return f"{self.run_id}"


class Sample(TimeStampedModel):
    """
    Stores information relating to a single BMH sample (i.e. R1, R2, corresponding assembly, etc.)
    - Must follow the BMH-YYYY-ZZZZZZ format, e.g. "BMH-2018-000001"
    - Each Sample must be associated with a Project + Run
    """
    sample_id = models.CharField(max_length=15, unique=True, validators=[validate_sample_id])
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE)
    run_id = models.ForeignKey(Run, on_delete=models.CASCADE)

    # TODO: upload_to uploads/projects/<project_id>/runs/<run_id>/samples/<sample_id>/*.fasta
    # assembly = models.FileField(upload_to='')

    # TODO: upload_to uploads/projects/<project_id>/runs/<run_id>/samples/<sample_id>/*_R1*.fastq.gz
    # fwd_reads = models.FileField(upload_to='')

    # TODO: upload_to uploads/projects/<project_id>/runs/<run_id>/samples/<sample_id>/*_R2*.fastq.gz
    # rev_reads = models.FileField(upload_to='')

    def __str__(self):
        return f"{self.sample_id}"
