import re
from pathlib import Path

import pandas as pd
from django.db import models

from django.conf import settings
from miseq_portal.analysis.tools.helpers import run_subprocess
from miseq_portal.core.models import TimeStampedModel
from miseq_portal.miseq_viewer.models import Sample
from miseq_portal.users.models import User

MEDIA_ROOT = settings.MEDIA_ROOT
MASH_REFSEQ_DATABASE = settings.MASH_REFSEQ_DATABASE
CONFINDR_DB = settings.CONFINDR_DB
CONFINDR_EXE = settings.CONFINDR_EXE
MEDIA_ROOT = Path(MEDIA_ROOT)


def upload_analysis_file(instance: Sample, filename: str, analysis_folder: str = 'analysis') -> str:
    """
    Method for generating an analysis upload path for a particular sample. Final path is dependent on sample_type.
    :param instance: Sample object
    :param filename: Name of the output analysis file
    :param analysis_folder: Directory to store analysis file
    :return: Upload path
    """
    if instance.sample_type == "BMH":
        return f'uploads/runs/{instance.run_id}/{instance.sample_id}/{analysis_folder}/{filename}'
    elif instance.sample_type == "MER":
        return f'merged_samples/{instance.sample_id}/{analysis_folder}/{filename}'
    elif instance.sample_type == "EXT":
        return f'external_samples/{instance.sample_id}/{analysis_folder}/{filename}'


def upload_mobsuite_file(instance: Sample, filename: str, mobsuite_dir_name: str) -> str:
    """
    TODO: This method is redundant and could be replaced by upload_analyis_file(). Remove and refactor.
    Method for generating an MOB suite analysis upload path for a particular sample.
    :param instance: Sample object
    :param filename: Name of the output analysis file
    :param mobsuite_dir_name: Directory to store analysis file
    :return: Upload path
    """
    if instance.sample_type == "BMH":
        return f'uploads/runs/{instance.run_id}/{instance.sample_id}/{mobsuite_dir_name}/{filename}'
    elif instance.sample_type == "MER":
        return f'merged_samples/{instance.sample_id}/{mobsuite_dir_name}/{filename}'
    elif instance.sample_type == "EXT":
        return f'external_samples/{instance.sample_id}/{mobsuite_dir_name}/{filename}'


class AnalysisGroup(models.Model):
    """
    Generic model for associating an analysis job
    """
    # This determines what options appear on the Analysis tool selection form
    job_choices = (
        ('SendSketch', 'SendSketch'),
        ('MobRecon', 'MobRecon'),
        ('RGI', 'RGI'),
        ('Confindr', 'Confindr'),
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

    class Meta:
        verbose_name = 'Analysis Group'
        verbose_name_plural = 'Analysis Groups'


def upload_group_analysis_file(analysis_group: AnalysisGroup, filename: str) -> str:
    """ Method for generating upload path for group analysis results (e.g. results from RGI heatmap)"""
    timestamped_dir = str(analysis_group.id) + '_' + analysis_group.created.strftime('%Y%m%d')
    return f'analysis_groups/{analysis_group.job_type}/{timestamped_dir}/{filename}'


class AnalysisSample(models.Model):
    """
    Generic model for associating a User, Sample ID and Group
    """
    sample_id = models.ForeignKey(Sample, on_delete=models.CASCADE)
    group_id = models.ForeignKey(AnalysisGroup, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{str(self.sample_id)} - {self.group_id}"

    class Meta:
        verbose_name = 'Analysis Sample'
        verbose_name_plural = 'Analysis Samples'


class SendsketchResult(TimeStampedModel):
    """
    Model for storing Sendsketch results on an individual sample
    """
    sample_id = models.OneToOneField(Sample, on_delete=models.CASCADE, primary_key=True)
    sendsketch_result_file = models.FileField(upload_to=upload_analysis_file, blank=True, max_length=1000)

    # TODO: Refactor much of the tools/sendsketch.py parsing logic to this model's methods

    top_taxName = models.CharField(max_length=128, blank=True, null=True)
    top_TaxID = models.CharField(max_length=32, blank=True, null=True)
    top_ANI = models.CharField(max_length=32, blank=True, null=True)
    top_Contam = models.CharField(max_length=32, blank=True, null=True)
    top_gSize = models.CharField(max_length=32, blank=True, null=True)

    def __str__(self):
        return str(self.sample_id)

    class Meta:
        verbose_name = 'Sendsketch Result'
        verbose_name_plural = 'Sendsketch Results'


class ProkkaResult(TimeStampedModel):
    """
    TODO: Finish implementing this
    """
    sample_id = models.OneToOneField(Sample, on_delete=models.CASCADE, primary_key=True)
    prokka_dir = models.FileField(upload_to=upload_analysis_file, blank=True, max_length=1000)

    @staticmethod
    def call_prokka(fasta_path: Path, sample_id: str, outdir: Path, n_cpu: int) -> Path:
        cmd = f"prokka --centre PORTAL --compliant --kingdom Bacteria " \
              f"--cpus {n_cpu} --prefix {sample_id} --locustag {sample_id} --force --outdir {outdir} {fasta_path}"
        run_subprocess(cmd, get_stdout=False)
        return outdir

    def __str__(self):
        return f"{self.sample_id}"

    class Meta:
        verbose_name = 'Prokka Result'
        verbose_name_plural = 'Prokka Results'


class ConfindrGroupResult(TimeStampedModel):
    """
    Model for storing overall Confindr results of entire AnalysisGroup e.g. the confindr_report.csv file
    """
    analysis_group = models.ForeignKey(AnalysisGroup, on_delete=models.CASCADE)
    confindr_report = models.FileField(upload_to=upload_group_analysis_file, blank=True)
    confindr_log = models.FileField(upload_to=upload_group_analysis_file, blank=True)

    @staticmethod
    def call_confindr(reads_dir: Path, outdir: Path, forward_id: str = "_R1", reverse_id: str = "_R2") -> tuple:
        """
        System call to confindr.py. Uses a Conda environment specifically for Confindr.
        This takes ~3 minutes to run per sample.

        :param reads_dir: Path to directory containing paired-end reads (.fastq.gz)
        :param outdir: Desired path to output directory
        :param forward_id: ID for forwards reads. Uses sensible default for Portal .fastq.gz files.
        :param reverse_id: ID for reverse reads. Uses sensible default for Portal .fastq.gz files.
        :return: Path to output file
        """
        cmd = f"{CONFINDR_EXE} -i {reads_dir} -o {outdir} -d {CONFINDR_DB} " \
              f"-fid {forward_id} -rid {reverse_id} -Xmx 20g -t 16"
        run_subprocess(cmd, get_stdout=False)

        report = outdir / 'confindr_report.csv'
        logfile = outdir / 'confindr_log.txt'

        return report, logfile

    class Meta:
        verbose_name = 'Confindr Group Result'
        verbose_name_plural = 'Confindr Group Results'


class ConfindrResult(TimeStampedModel):
    """
    Model for storing individual sample output files and results produced by Confindr
    """
    # Must be instantiated with these values
    analysis_sample = models.OneToOneField(AnalysisSample, on_delete=models.CASCADE)
    contamination_csv = models.FileField(upload_to=upload_analysis_file, blank=True, max_length=1000)
    rmlst_csv = models.FileField(upload_to=upload_analysis_file, blank=True, max_length=1000)

    # Fields parsed from confindr_report.csv
    genus = models.CharField(max_length=256, blank=True, null=True)
    num_contam_snvs = models.IntegerField(blank=True, null=True)
    contam_status = models.CharField(max_length=32, blank=True, null=True)
    percent_contam = models.FloatField(blank=True, null=True)
    percent_contam_std_dev = models.FloatField(blank=True, null=True)
    bases_examined = models.IntegerField(blank=True, null=True)
    database_download_date = models.DateField(blank=True, null=True)

    def get_contamination_df(self):
        df = pd.read_csv(self.contamination_csv)
        return df

    def get_rmlst_df(self):
        df = pd.read_csv(self.rmlst_csv)
        return df

    @property
    def sample_id(self):
        return self.analysis_sample.sample_id

    def __str__(self):
        return str(f"{self.pk} - {self.sample_id}")

    class Meta:
        verbose_name = 'Confindr Result'
        verbose_name_plural = 'Confindr Results'


class MashResult(TimeStampedModel):
    """
    Model for storing Mash results against RefSeq for an individual sample
    """
    sample_id = models.OneToOneField(Sample, on_delete=models.CASCADE, primary_key=True)
    mash_result_file = models.FileField(upload_to=upload_analysis_file, blank=True, max_length=1000)

    top_hit = models.CharField(max_length=256, blank=True, null=True)
    top_shared_hashes = models.CharField(max_length=32, blank=True, null=True)
    top_identity = models.FloatField(blank=True, null=True)
    top_query_id = models.CharField(max_length=128, blank=True, null=True)

    @staticmethod
    def call_mash(assembly: Path, outdir: Path, n_cpu: int = 16, pct_identity: float = 0.80) -> Path:
        outfile = outdir / 'mash_refseq_results.tab'
        cmd = f"mash screen -i {pct_identity} -p {n_cpu} {str(MASH_REFSEQ_DATABASE)} {assembly} > {outfile}"
        run_subprocess(cmd)
        return outfile

    @staticmethod
    def parse_mash_results(mash_result_file: Path) -> pd.DataFrame:
        # Read in CSV with proper headers
        df = pd.read_csv(mash_result_file, sep="\t", header=None, index_col=None)
        df.columns = ['identity', 'shared-hashes', 'median-multiplicity', 'p-value', 'query-ID', 'query-comment']
        # Filter out phages and plasmids - TODO: validate that this is desired behaviour
        df['valid_row'] = df['query-comment'].apply(
            lambda x: 'false' if ' phage ' in x.lower() or ' plasmid ' in x.lower() else 'true')
        df = df[df['valid_row'] == 'true']
        # Sort the best match to the top
        df = df.sort_values(by=['identity'], ascending=False).reset_index(drop=True)
        return df

    @staticmethod
    def parse_top_mash_hit(top_mash_hit: str) -> str:
        """ Removes extraneous characters from the Mash query-comment string """
        # Remove square bracketed terms if there are any
        top_mash_hit_parsed = re.sub(r'\[[^\]]*\]', '', top_mash_hit).lstrip()
        # Remove the identifier (useless)
        top_mash_hit_parsed = top_mash_hit_parsed.split(" ", 1)[1].strip()
        # Remove everything after the first comma
        top_mash_hit_parsed = top_mash_hit_parsed.split(",")[0].strip()
        return top_mash_hit_parsed

    def get_top_mash_hit(self) -> tuple:
        """ Grabs the assembly for the parent Sample, calls Mash on it, and parses the result """
        assembly_path = self.sample_id.sampleassemblydata.get_assembly_path()
        mash_result_file = self.call_mash(assembly=assembly_path, outdir=assembly_path.parent)

        # Check if the file actually has any data in it
        if mash_result_file.stat().st_size > 1:
            df = self.parse_mash_results(mash_result_file=mash_result_file)
            # df is sorted so we can use grab the data from the first row for the top result
            top_mash_result = {
                'hit': self.parse_top_mash_hit(df['query-comment'][0]),
                'shared_hashes': df['shared-hashes'][0],
                'identity': float(df['identity'][0]),
                'query_id': df['query-ID'][0]
            }
        else:
            top_mash_result = None
        return top_mash_result, mash_result_file

    def __str__(self):
        return f"{self.sample_id} - {self.top_hit}"

    class Meta:
        verbose_name = 'Mash Result'
        verbose_name_plural = 'Mash Results'


class MobSuiteAnalysisGroup(TimeStampedModel):
    """
    Model for storing all general MOB suite results for a single AnalysisSample
    See MobSuiteAnalysisPlasmid for individual plasmid results
    """
    analysis_sample = models.OneToOneField(AnalysisSample, on_delete=models.CASCADE)
    contig_report = models.FileField(upload_to=upload_mobsuite_file, blank=True, max_length=1000)
    mobtyper_aggregate_report = models.FileField(upload_to=upload_mobsuite_file, blank=True, max_length=1000)

    def sample_id(self):
        return self.analysis_sample.sample_id

    def group_id(self):
        return self.analysis_sample.group_id

    def get_plasmid_attribute(self, plasmid_basename: str, attribute: str, aggregate_report_path: Path = None) -> (str,
                                                                                                                   None):
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

    class Meta:
        verbose_name = 'MobSuite Analysis Group'
        verbose_name_plural = 'MobSuite Analysis Groups'


class MobSuiteAnalysisPlasmid(TimeStampedModel):
    """
    Model for storing individual plasmid results for MOB suite output on a per-sample basis
    """
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

    class Meta:
        verbose_name = 'MobSuite Plasmid'
        verbose_name_plural = 'MobSuite Plasmids'


class RGIResult(TimeStampedModel):
    """
    Model for storing output files from rgi main
    """
    analysis_sample = models.OneToOneField(AnalysisSample, on_delete=models.CASCADE)
    rgi_main_text_results = models.FileField(upload_to=upload_analysis_file, blank=True, max_length=1000)
    rgi_main_json_results = models.FileField(upload_to=upload_analysis_file, blank=True, max_length=1000)

    def sample_id(self):
        return self.analysis_sample.sample_id

    def __str__(self):
        return str(f"{self.pk} - {self.sample_id()}")

    class Meta:
        verbose_name = 'RGI Result'
        verbose_name_plural = 'RGI Results'


class RGIGroupResult(TimeStampedModel):
    """
    Model for storing overall RGI analysis of entire AnalysisGroup e.g. the RGI heatmap
    """
    analysis_group = models.ForeignKey(AnalysisGroup, on_delete=models.CASCADE)
    rgi_heatmap_result = models.ImageField(upload_to=upload_group_analysis_file, blank=True)  # Stores .png file
    rgi_json_results_zip = models.FileField(upload_to=upload_group_analysis_file, blank=True)  # .zip of all .json
    rgi_txt_results_zip = models.FileField(upload_to=upload_group_analysis_file, blank=True)  # .zip of all .txt

    class Meta:
        verbose_name = 'RGI Group Result'
        verbose_name_plural = 'RGI Group Results'
