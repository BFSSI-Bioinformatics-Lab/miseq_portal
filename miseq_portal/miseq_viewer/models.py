import logging
from pathlib import Path

from dataclasses import dataclass
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from config.settings.base import MEDIA_ROOT
from miseq_portal.core.models import TimeStampedModel
from miseq_portal.users.models import User

logger = logging.getLogger('django')


def validate_sample_id(value: str, length: int = 15):
    """
    Strict validation of BMH Sample ID
    :param value: sample_id
    :param length: expected length of string
    """
    components = value.split("-")

    if len(value) != length:
        raise ValidationError(f"Sample ID '{value}' does not meet the expected length of 15 characters. "
                              f"Sample ID must be in the following format: 'BMH-2018-000001'")

    if len(components) != 3:
        raise ValidationError(f"Sample ID '{value}' does not appear to meet expected format. "
                              f"Sample ID must be in the following format: 'BMH-2018-000001'")
    elif components[0] != 'BMH' and components[0] != 'MER' and components[0] != 'EXT':
        raise ValidationError(
            f"TEXT component of Sample ID ('{components[0]}') does not equal expected 'BMH', 'MER', or 'EXT'")
    elif not components[1].isdigit() or len(components[1]) != 4:
        raise ValidationError(f"YEAR component of Sample ID ('{components[1]}') does not equal expected 'YYYY' format")
    elif not components[2].isdigit() or len(components[2]) != 6:
        raise ValidationError(f"ID component of Sample ID ('{components[2]}') does not equal expected 'XXXXXX' format")
    return True


def upload_run_file(instance, filename: str):
    """instance must be Run"""
    if instance.run_type == "BMH":
        return f'uploads/runs/{instance.run_id}/{filename}'
    elif instance.run_type == "EXT":
        return f'external_samples/runs/{instance.run_id}/{filename}'


def upload_interop_file(instance, filename: str):
    """instance must be RunInterOpData"""
    if instance.run_id.run_type == "BMH":
        return f'uploads/runs/{instance.run_id}/InterOp/{filename}'
    elif instance.run_id.run_type == "EXT":
        return f'external_samples/runs/{instance.run_id}/InterOp/{filename}'


def upload_interop_dir(instance):
    """instance must be Run"""
    if instance.run_type == "BMH":
        return f'uploads/runs/{instance.run_id}/InterOp/'
    elif instance.run_type == "EXT":
        return f'external_samples/runs/{instance.run_id}/InterOp/'


def upload_reads(instance, filename: str):
    """instance must be Sample"""
    if instance.sample_type == 'BMH':
        return f'uploads/runs/{instance.run_id}/{instance.sample_id}/{filename}'
    elif instance.sample_type == 'MER':
        return f'merged_samples/{instance.sample_id}/{filename}'
    elif instance.sample_type == 'EXT':
        return f'external_samples/runs/{instance.run_id}/{instance.sample_id}/{filename}'


def upload_assembly(instance, filename: str):
    """instance must be SampleAssemblyData"""
    if instance.sample_id.sample_type == 'BMH':
        return f'uploads/runs/{instance.sample_id.run_id}/{instance.sample_id}/assembly/{filename}'
    elif instance.sample_id.sample_type == 'MER':
        return f'merged_samples/{instance.sample_id}/assembly/{filename}'
    elif instance.sample_id.sample_type == 'EXT':
        return f'external_samples/runs/{instance.sample_id.run_id}/{instance.sample_id}/assembly/{filename}'


def upload_merged_sample(instance, filename: str):
    """Deprecated, replaced by upload_reads, can't delete due to it being stuck in earlier migrations"""
    return f'uploads/merged_samples/{instance.sample_id}/{filename}'


@dataclass
class SampleDataObject:
    """
    Dataclass to store metadata for a sample which will eventually be passed to the Sample and SampleLogData models
    """

    # Must be instantiated with these attributes
    sample_id: str
    run_id: str
    project_id: str
    sample_name: str

    # Updated later in the lifecycle
    sample_type: str = None  # i.e. BMH, EXT
    sequencing_type: str = None  # i.e. META, WGS, RNA, AMP
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

    run_type: str = None
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
    Samples can belong to Projects. Used to help organize sample data.
    """
    project_id = models.CharField(max_length=256, unique=True)
    project_owner = models.ForeignKey(User, on_delete=models.CASCADE)

    # TODO: Consider adding flags for viral, prokaryotic, eukaryotic, metagenomic, mixed sample types

    def last_updated(self) -> str:
        """ Finds the most recently created Sample object belonging to this project """
        samples = Sample.objects.filter(project_id=self.id).order_by('-created')
        return samples[0].modified

    @property
    def num_samples(self):
        return len(Sample.objects.filter(project_id=self.pk))

    def __str__(self):
        return self.project_id

    def __len__(self):
        return self.num_samples

    class Meta:
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'


class UserProjectRelationship(TimeStampedModel):
    """
    Stores relationship between a Project and User, as well as their access level for the project
    """
    ACCESS_LEVELS = (
        ('MANAGER', 'Manager'),  # Delete, modify
        ('ADMIN', 'Admin'),  # Same as MANAGER
        ('USER', 'User'),  # View
        ('NONE', 'None'),  # No access
    )
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='relationship_project', null=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name='relationship_user', null=True)
    access_level = models.CharField(max_length=32, choices=ACCESS_LEVELS, default='NONE')

    def __str__(self):
        return str(self.project_id) + ' : ' + str(self.user_id) + ' : ' + str(self.access_level)

    class Meta:
        verbose_name = 'User Project Relationship'
        verbose_name_plural = 'User Project Relationships'


class Run(TimeStampedModel):
    """
    Stores information relating to a single sequencing run
    """
    run_id = models.CharField(max_length=256, unique=True)
    sample_sheet = models.FileField(upload_to=upload_run_file, blank=True, max_length=1000)
    runinfoxml = models.FileField(upload_to=upload_run_file, blank=True, null=True, max_length=1000)
    runparametersxml = models.FileField(upload_to=upload_run_file, blank=True, null=True, max_length=1000)
    interop_directory_path = models.CharField(unique=True, blank=True, null=True, max_length=1000)

    # run_type indicates whether the Sample was generated by the BMH sequencing lab or by an external lab
    RUN_TYPES = (
        ('BMH', 'BMH'),
        ('EXT', 'EXT'),
    )
    run_type = models.CharField(max_length=3, choices=RUN_TYPES, default="BMH")

    def get_interop_directory(self) -> Path:
        return Path(self.interop_directory_path)

    @property
    def run_url(self) -> str:
        return reverse('miseq_viewer:miseq_viewer_run_detail', args=(self.pk,))

    @property
    def num_samples(self) -> int:
        return len(Sample.objects.filter(run_id=self.pk))

    def __str__(self):
        return str(self.run_id)

    def __len__(self):
        return self.num_samples

    class Meta:
        verbose_name = 'Run'
        verbose_name_plural = 'Runs'


class RunSamplesheet(TimeStampedModel):
    run_id = models.OneToOneField(Run, on_delete=models.CASCADE, primary_key=True)

    # Attempts to capture all possible fields within the [Header] section of a MiSeq or iSeq samplesheet
    iemfileversion = models.CharField(blank=True, max_length=1028)
    local_run_manager_analysis_id = models.CharField(blank=True, max_length=1028)
    investigator_name = models.CharField(blank=True, max_length=1028)
    experiment_name = models.CharField(blank=True, max_length=1028)
    samplesheet_date = models.CharField(blank=True, max_length=1028)
    workflow = models.CharField(blank=True, max_length=1028)
    date = models.CharField(blank=True, max_length=1028)
    instrument_type = models.CharField(blank=True, max_length=1028)
    module = models.CharField(blank=True, max_length=1028)
    library_prep_kit = models.CharField(blank=True, max_length=1028)
    application = models.CharField(blank=True, max_length=1028)
    assay = models.CharField(blank=True, max_length=1028)
    index_adapters = models.CharField(blank=True, max_length=1028)
    description = models.CharField(blank=True, max_length=1028)
    chemistry = models.CharField(blank=True, max_length=1028)

    def get_fields(self):
        return [(field.name, field.value_to_string(self)) for field in RunSamplesheet._meta.fields]

    class Meta:
        verbose_name = 'Run Samplesheet'
        verbose_name_plural = 'Run Samplesheets'

    def __str__(self):
        return str(self.run_id)


class RunInterOpData(TimeStampedModel):
    """
    Stores metadata on a MiSeq run derived from the Illumnina InterOp files
    """
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
        verbose_name = 'Run InterOp Data'
        verbose_name_plural = 'Run InterOp Data'


class MergedSampleComponentGroup(models.Model):
    """
    Model for reference by MergedSample.
    Maintains the linkage between a MergedSample and its constituent Sample objects via MergedSampleComponent
    """
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    @property
    def get_components(self):
        components = MergedSampleComponent.objects.filter(group_id=self.pk)
        return components

    def __str__(self):
        return f"{str(self.pk)} - {self.created.date()} - " + ", ".join(
            [component.component_id.sample_id for component in self.get_components])

    class Meta:
        verbose_name = 'Merged Sample Component Group'
        verbose_name_plural = 'Merged Sample Component Groups'


class Sample(TimeStampedModel):
    """
    Stores basic information relating to a single BMH sample (i.e. R1, R2, corresponding assembly, etc.)
    - Must follow the XXX-YYYY-ZZZZZZ format, e.g. "BMH-2018-000001", "MER-2019-000004"
    - Each Sample can be associated with a Project and Run
    - sample_type controls how the sample will be handled within the analysis/assembly pipelines + upload destination
    - component_group is used to track the relationship between a merged sample and its constituent components
    """
    sample_id = models.CharField(max_length=15, unique=True, validators=[validate_sample_id])
    sample_name = models.TextField(blank=True)

    # The sample_type and component_group fields exist to accommodate merged samples
    sample_type_choices = (
        ('BMH', 'BMH'),
        ('MER', 'MERGED'),
        ('EXT', 'EXTERNAL')
    )
    sample_type = models.CharField(choices=sample_type_choices, max_length=3, default='BMH')

    # sequencing_type is used to track the sample sequencing type which can be used to determine assembly method
    SEQUENCING_TYPES = (
        ('WGS', 'Whole-Genome Sequence'),
        ('META', 'Metagenomic Sequence'),
        ('RNA', 'RNA-Seq'),
        ('AMP', 'Amplicon')
    )
    sequencing_type = models.CharField(max_length=32, choices=SEQUENCING_TYPES, default="WGS")

    component_group = models.ForeignKey(MergedSampleComponentGroup, on_delete=models.CASCADE, blank=True, null=True)

    # All BMH samples must be associated with a Project and Run
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True)
    run_id = models.ForeignKey(Run, on_delete=models.CASCADE, blank=True, null=True)

    # Read upload location varies depending on sample_type
    fwd_reads = models.FileField(upload_to=upload_reads, blank=True, max_length=1000)
    rev_reads = models.FileField(upload_to=upload_reads, blank=True, max_length=1000)

    hide_flag = models.BooleanField(default=False)  # Activate this to hide the sample from view for regular users
    additional_notes = models.TextField(blank=True)

    def generate_sample_id(self):
        """
        This method must be used for EXT or MER samples. First, instantiate the object, then call this method and assign
        the generated value to Sample.sample_id
        """
        return f'{self.sample_type}-{self.sample_year}-{self.pk:06}'

    @property
    def sample_year(self):
        return str(self.created.year)

    def __str__(self):
        return self.sample_id

    class Meta:
        verbose_name = 'Sample'
        verbose_name_plural = 'Samples'


class MergedSampleComponent(models.Model):
    """
    Model to store the relationship between a Sample (i.e. a "component") and a MergedSampleComponentGroup
    """
    component_id = models.ForeignKey(Sample, on_delete=models.CASCADE)
    group_id = models.ForeignKey(MergedSampleComponentGroup, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.component_id} ({self.group_id})"

    class Meta:
        verbose_name = 'Merged Sample Component'
        verbose_name_plural = 'Merged Sample Components'


class SampleLogData(TimeStampedModel):
    """
    Stores Sample metadata derived from Stats.json, a file generated by BaseSpace for a MiSeq run
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

    @property
    def sample_yield_mbp(self):
        if self.sample_yield is not None:
            return float(self.sample_yield / 1000000)

    def __str__(self):
        return str(self.sample_id)

    class Meta:
        verbose_name = 'Sample Log Data'
        verbose_name_plural = 'Sample Log Data'


class SampleAssemblyData(TimeStampedModel):
    """
    Stores metadata on a Sample assembly.
    """
    sample_id = models.OneToOneField(Sample, on_delete=models.CASCADE, primary_key=True)
    assembly = models.FileField(blank=True, max_length=512)

    # Assembly metrics
    num_contigs = models.IntegerField(blank=True, null=True)
    largest_contig = models.BigIntegerField(blank=True, null=True)
    total_length = models.BigIntegerField(blank=True, null=True)
    gc_percent = models.FloatField(blank=True, null=True)
    n50 = models.BigIntegerField(blank=True, null=True)
    num_predicted_genes = models.BigIntegerField(blank=True, null=True)
    mean_coverage = models.TextField(blank=True, null=True)
    std_coverage = models.TextField(blank=True, null=True)

    # Pipeline versioning
    bbduk_version = models.TextField(blank=True)
    bbmap_version = models.TextField(blank=True)
    tadpole_version = models.TextField(blank=True)
    skesa_version = models.TextField(blank=True)
    pilon_version = models.TextField(blank=True)
    quast_version = models.TextField(blank=True)

    def get_assembly_path(self) -> Path:
        """
        Returns the expected assembly path, if it exists
        """
        assembly_path = MEDIA_ROOT / Path(str(self.assembly))
        if self.assembly_exists():
            return assembly_path
        else:
            raise FileNotFoundError(f"Assembly at {self.assembly} for {self.sample_id} does not exist!")

    def assembly_exists(self) -> bool:
        """
        Returns True if assembly file exists, False if not
        """
        assembly_path = MEDIA_ROOT / Path(str(self.assembly))
        if not assembly_path.exists() or self.assembly is None or str(self.assembly) == "":
            return False
        elif assembly_path.exists():
            return True

    def __str__(self):
        return str(self.sample_id)

    class Meta:
        verbose_name = 'Sample Assembly Data'
        verbose_name_plural = 'Sample Assembly Data'
