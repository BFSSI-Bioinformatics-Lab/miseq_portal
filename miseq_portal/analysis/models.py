import pandas as pd
from django.db import models
from pathlib import Path
from miseq_portal.core.models import TimeStampedModel
from miseq_portal.miseq_viewer.models import Sample
from miseq_portal.users.models import User
from config.settings.base import MEDIA_ROOT


def upload_analysis_file(instance: Sample, filename: str):
    return f'uploads/runs/{instance.run_id}/{instance.sample_id}/{filename}'


def upload_mobsuite_file(instance: Sample, filename: str, mobsuite_dir_name: str):
    return f'uploads/runs/{instance.run_id}/{instance.sample_id}/{mobsuite_dir_name}/{filename}'


class AnalysisGroup(models.Model):
    """

    """
    # This determines what options appear on the Analysis tool selection form
    job_choices = (
        ('SendSketch', 'SendSketch'),
        ('MobRecon', 'MobRecon'),
        # ('PlasmidAMR', 'PlasmidAMR'),
        # ('TotalAMR', 'TotalAMR')
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
        return f"{str(self.id)} ({str(self.job_type)})"


class AnalysisSample(models.Model):
    sample_id = models.ForeignKey(Sample, on_delete=models.CASCADE)
    group_id = models.ForeignKey(AnalysisGroup, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{str(self.sample_id)} - {self.group_id}"


class SendsketchResult(TimeStampedModel):
    sample_id = models.OneToOneField(Sample, on_delete=models.CASCADE, primary_key=True)
    sendsketch_result_file = models.FileField(upload_to=upload_analysis_file, blank=True, max_length=1000)

    # TODO: Refactor much of the tools/sendsketch.py parsing logic to this model's methods

    top_taxName = models.CharField(max_length=128, blank=True)
    top_TaxID = models.CharField(max_length=32, blank=True)
    top_ANI = models.CharField(max_length=32, blank=True)
    top_Contam = models.CharField(max_length=32, blank=True)
    top_gSize = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return str(self.sample_id)


class MobSuiteAnalysisGroup(TimeStampedModel):
    analysis_sample = models.OneToOneField(AnalysisSample, on_delete=models.CASCADE)
    contig_report = models.FileField(upload_to=upload_mobsuite_file, blank=True, max_length=1000)
    mobtyper_aggregate_report = models.FileField(upload_to=upload_mobsuite_file, blank=True, max_length=1000)

    def sample_id(self):
        return self.analysis_sample.sample_id

    def group_id(self):
        return self.analysis_sample.group_id

    def get_plasmid_attribute(self, plasmid_basename: str, attribute: str, aggregate_report_path: Path = None) -> (
    str, None):
        valid_attributes = [
            'file_id', 'num_contigs', 'total_length',
            'gc', 'rep_type(s)', 'rep_type_accession(s)',
            'relaxase_type(s)', 'relaxase_type_accession(s)', 'PredictedMobility',
            'mash_nearest_neighbor', 'mash_neighbor_distance', 'mash_neighbor_cluster'
        ]
        if attribute not in valid_attributes:
            raise AttributeError(f"Attribute {attribute} is not valid. "
                                 f"List of acceptable attributes: {valid_attributes}")
        df = self.read_aggregate_report(aggregate_report_path=aggregate_report_path)
        if len(df) == 0:
            return None
        else:
            plasmid_row = df[df["file_id"] == plasmid_basename].reset_index()
            return plasmid_row[attribute][0]

    def read_aggregate_report(self, aggregate_report_path: Path = None) -> pd.DataFrame:
        if aggregate_report_path is None:
            aggregate_report_path = self.get_aggregate_report_path()
        df = pd.read_csv(aggregate_report_path, sep="\t")
        return df

    def get_aggregate_report_path(self):
        aggregate_report_path = MEDIA_ROOT / Path(str(self.mobtyper_aggregate_report))
        if self.aggregate_report_exists():
            return aggregate_report_path
        else:
            raise FileNotFoundError(
                f"Mob recon aggregate report at {self.mobtyper_aggregate_report} for {self.sample_id} does not exist!")

    def aggregate_report_exists(self):
        agg_report_path = MEDIA_ROOT / Path(str(self.mobtyper_aggregate_report))
        if not agg_report_path.exists():
            return False
        elif self.mobtyper_aggregate_report is None or str(self.mobtyper_aggregate_report) == "":
            return False
        elif agg_report_path.exists():
            return True

    def __str__(self):
        return str(f"MobSuiteAnalysisGroup ({self.analysis_sample})")


class MobSuiteAnalysisPlasmid(TimeStampedModel):
    sample_id = models.ForeignKey(Sample, on_delete=models.CASCADE)
    group_id = models.ForeignKey(MobSuiteAnalysisGroup, on_delete=models.CASCADE)
    plasmid_fasta = models.FileField(upload_to=upload_mobsuite_file, blank=True, max_length=1000)

    # This data is pulled from mobtyper_aggregate_report.txt
    num_contigs = models.IntegerField(blank=True, null=True)
    total_length = models.BigIntegerField(blank=True, null=True)
    gc_content = models.FloatField(blank=True, null=True)
    rep_type = models.CharField(max_length=128, blank=True, null=True)
    rep_type_accession = models.CharField(max_length=128, blank=True, null=True)
    relaxase_type = models.CharField(max_length=128, blank=True, null=True)
    relaxase_type_accession = models.CharField(max_length=128, blank=True, null=True)
    predicted_mobility = models.CharField(max_length=128, blank=True, null=True)
    mash_nearest_neighbor = models.CharField(max_length=128, blank=True, null=True)
    mash_neighbor_distance = models.FloatField(blank=True, null=True)
    mash_neighbor_cluster = models.CharField(max_length=128, blank=True, null=True)

    def plasmid_basename(self):
        return Path(str(self.plasmid_fasta)).name

    def __str__(self):
        return str(f"{self.pk} - {self.sample_id}")
