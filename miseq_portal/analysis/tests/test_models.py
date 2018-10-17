import pytest
import tempfile
from mock import Mock
from model_mommy import mommy
from django.test import TestCase

from miseq_portal.analysis.models import *
from miseq_portal.miseq_viewer.models import Run

pytestmark = pytest.mark.django_db


def test_upload_analysis_file():
    filename = "test_file"

    # Run mock
    run = Mock(spec=Run)
    run.id = 1
    run.run_id = "MOCK_RUN_01"

    # BMH sample mock
    sample = Mock(spec=Sample)
    sample.id = 1
    sample.run_id = run
    sample.sample_type = 'BMH'
    sample.sample_id = "BMH-2017-000001"

    assert upload_analysis_file(sample, filename) == f'uploads/runs/{sample.run_id}/{sample.sample_id}/{filename}'


def test_upload_mobsuite_file():
    filename = 'test_file'
    mobsuite_dir_name = 'test'

    # Run mock
    run = Mock(spec=Run)
    run.id = 1
    run.run_id = 'MOCK_RUN_01'

    # BMH sample mock
    sample = Mock(spec=Sample)
    sample.id = 1
    sample.run_id = run
    sample.sample_type = 'BMH'
    sample.sample_id = 'BMH-2017-000001'

    assert upload_mobsuite_file(sample, filename,
                                mobsuite_dir_name) == f'uploads/runs/{sample.run_id}/{sample.sample_id}/{mobsuite_dir_name}/{filename}'


class AnalysisGroupTest(TestCase):
    @staticmethod
    def test_analysis_group_creation():
        group = mommy.make(AnalysisGroup)
        assert isinstance(group, AnalysisGroup)
        assert group.__str__() == f"{str(group.id)} ({str(group.job_type)})"


class AnalysisSampleTest(TestCase):
    @staticmethod
    def test_analysis_sample_creation():
        sample = mommy.make(AnalysisSample)
        assert isinstance(sample, AnalysisSample)
        assert sample.__str__() == f"{str(sample.sample_id)} - {sample.group_id}"


class SendsketchResultTest(TestCase):
    @staticmethod
    def test_sendsketch_result_creation():
        result = mommy.make(SendsketchResult)
        assert isinstance(result, SendsketchResult)
        assert result.__str__() == f"{str(result.sample_id)}"


class MobSuiteAnalysisGroupTest(TestCase):
    def setUp(self):
        # Setup MobSuiteAnalysisGroup
        self.group = mommy.make(MobSuiteAnalysisGroup)
        self.group.analysis_sample = mommy.make(AnalysisSample)

        # Setup AnalysisSample
        self.sample_id = mommy.make(Sample)
        self.group.analysis_sample.sample_id = self.sample_id

        # Setup AnalysisGroup
        self.group_id = mommy.make(AnalysisGroup)
        self.group.analysis_sample.group_id = self.group_id

    def test_mob_suite_analysis_group_creation(self):
        assert isinstance(self.group, MobSuiteAnalysisGroup)
        assert self.group.__str__() == str(f"MobSuiteAnalysisGroup ({self.group.analysis_sample})")

    def test_sample_id(self):
        assert self.group.sample_id() == self.sample_id

    def test_group_id(self):
        assert self.group.group_id() == self.group_id

    def test_aggregate_report_exists(self):
        # Report should not exist
        assert self.group.aggregate_report_exists() is False

        # Populate with report
        aggregate_report = tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8')
        aggregate_report.write("FAKE_REPORT")
        aggregate_report.flush()
        self.group.mobtyper_aggregate_report = aggregate_report.name
        assert self.group.aggregate_report_exists() is True

    def test_get_aggregate_report_path(self):
        # This should raise a FileNotFoundError
        with pytest.raises(FileNotFoundError):
            assert self.group.get_aggregate_report_path()

    def test_read_aggregate_report(self):
        aggregate_report = tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8')
        aggregate_report.write("COL1\tCOL2\n1\t2")
        aggregate_report.flush()
        self.group.aggregate_report_path = aggregate_report.name
        assert type(
            self.group.read_aggregate_report(aggregate_report_path=self.group.aggregate_report_path)) == pd.DataFrame

    def test_get_plasmid_attribute(self):
        # Validate that AttributeError is raised if invalid attr passed
        with pytest.raises(AttributeError):
            assert self.group.get_plasmid_attribute(plasmid_basename="test", attribute='ATTRIBUTE_ERROR')

        # Create a fake aggregate report and read it
        aggregate_report = tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8')
        aggregate_report.write("file_id\tcol2\nplasmid_basename\ttest")
        aggregate_report.flush()
        self.group.aggregate_report_path = aggregate_report.name

        # Test valid attribute and valid report
        plasmid_attribute = self.group.get_plasmid_attribute(plasmid_basename='plasmid_basename',
                                                             attribute='file_id',
                                                             aggregate_report_path=self.group.aggregate_report_path)
        assert type(plasmid_attribute) == str
        assert plasmid_attribute == 'plasmid_basename'


class MobSuiteAnalysisPlasmidTest(TestCase):
    @staticmethod
    def test_mob_suite_analysis_plasmid_creation():
        plasmid = mommy.make(MobSuiteAnalysisPlasmid)
        assert isinstance(plasmid, MobSuiteAnalysisPlasmid)
        assert plasmid.__str__() == f"{plasmid.pk} - {plasmid.sample_id}"
