import tempfile
from pathlib import PosixPath

import pytest
from django.test import TestCase
from mock import Mock
from model_mommy import mommy

from miseq_portal.miseq_viewer.models import *

pytestmark = pytest.mark.django_db


def test_validate_sample_id():
    assert validate_sample_id('BMH-2017-000001') is True
    with pytest.raises(ValidationError):
        assert validate_sample_id('VALIDATION_ERROR')
    with pytest.raises(ValidationError):
        assert validate_sample_id('AAAA-2017-000001')
    with pytest.raises(ValidationError):
        assert validate_sample_id('BMH-TEST-000001')
    with pytest.raises(ValidationError):
        assert validate_sample_id('BMH-2017-AAAAAA')


def test_upload_run_file():
    run = Mock(spec=Run)
    run.id = 1
    run.run_id = "MOCK_RUN_01"
    run.run_type = 'BMH'
    filename = 'test_file'
    assert upload_run_file(run, filename) == f'uploads/runs/{run.run_id}/{filename}'


def test_upload_interop_file():
    run = Mock(spec=Run)
    run.id = 1
    run.run_id = "MOCK_RUN_01"
    run.run_type = "BMH"

    runinterop = Mock(spec=RunInterOpData)
    runinterop.id = 1
    runinterop.run_id = run
    filename = 'test_file'

    assert upload_interop_file(runinterop, filename) == f'uploads/runs/{runinterop.run_id}/InterOp/{filename}'


def test_upload_interop_dir():
    run = Mock(spec=Run)
    run.id = 1
    run.run_id = "MOCK_RUN_01"
    run.run_type = "BMH"
    assert upload_interop_dir(run) == f'uploads/runs/{run.run_id}/InterOp/'


def test_upload_reads():
    # Run mock
    run = Mock(spec=Run)
    run.id = 1
    run.run_id = "MOCK_RUN_01"

    filename = "test_file"

    # BMH sample mock
    sample1 = Mock(spec=Sample)
    sample1.id = 1
    sample1.run_id = run
    sample1.sample_type = 'BMH'
    sample1.sample_id = "BMH-2017-000001"

    # MER sample mock
    sample2 = Mock(spec=Sample)
    sample2.id = 2
    sample2.sample_type = 'MER'
    sample2.sample_id = "MER-2017-000001"

    assert upload_reads(sample1, filename) == f'uploads/runs/{sample1.run_id}/{sample1.sample_id}/{filename}'
    assert upload_reads(sample2, filename) == f'merged_samples/{sample2.sample_id}/{filename}'


def test_upload_assembly():
    filename = "test_file"

    # Run mock
    run = Mock(spec=Run)
    run.id = 1
    run.run_id = "MOCK_RUN_01"

    # BMH sample mock
    sample1 = Mock(spec=Sample)
    sample1.id = 1
    sample1.run_id = run
    sample1.sample_type = 'BMH'
    sample1.sample_id = "BMH-2017-000001"

    # MER sample mock
    sample2 = Mock(spec=Sample)
    sample2.id = 2
    sample2.sample_type = 'MER'
    sample2.sample_id = "MER-2017-000001"

    # Mock SampleAssemblyData
    assembly1 = Mock(spec=SampleAssemblyData)
    assembly1.sample_id = sample1

    assembly2 = Mock(spec=SampleAssemblyData)
    assembly2.sample_id = sample2

    assert upload_assembly(assembly1,
                           filename) == f'uploads/runs/{assembly1.sample_id.run_id}/{assembly1.sample_id}/assembly/{filename}'
    assert upload_assembly(assembly2, filename) == f'merged_samples/{assembly2.sample_id}/assembly/{filename}'


class ProjectTest(TestCase):
    @staticmethod
    def test_project_creation():
        proj = mommy.make(Project)
        assert isinstance(proj, Project)
        assert proj.__str__() == proj.project_id


class UserProjectRelationshipTest(TestCase):
    @staticmethod
    def test_user_project_relationship_creation():
        rel = mommy.make(UserProjectRelationship)
        assert isinstance(rel, UserProjectRelationship)
        assert rel.__str__() == str(rel.project_id) + ':' + str(rel.user_id)


class RunTest(TestCase):
    def setUp(self):
        self.run = mommy.make(Run)
        self.test_path = '/test/path'
        self.run.interop_directory_path = self.test_path

    def test_project_creation(self):
        assert isinstance(self.run, Run)
        assert self.run.__str__() == self.run.run_id

    def test_get_interop_directory(self):
        assert type(self.run.get_interop_directory()) is PosixPath
        assert str(self.run.get_interop_directory()) == self.test_path


class RunInterOpDataTest(TestCase):
    @staticmethod
    def test_run_inter_op_data_creation():
        data = mommy.make(RunInterOpData)
        assert isinstance(data, RunInterOpData)
        assert data.__str__() == str(data.run_id) + '_InterOp'


class MergedSampleComponentGroupTest(TestCase):
    @staticmethod
    def test_merged_sample_component_group_creation():
        component_group = mommy.make(MergedSampleComponentGroup)
        assert isinstance(component_group, MergedSampleComponentGroup)
        assert component_group.__str__() == f"MergedSampleComponentGroup ({str(component_group.pk)})"


class SampleTest(TestCase):
    def setUp(self):
        self.bmh_sample = mommy.make(Sample)
        self.bmh_sample.sample_id = 'BMH-2017-000001'
        self.bmh_sample.sample_name = 'test_sample_name'
        self.bmh_sample.sample_type = 'BMH'

        self.mer_sample = mommy.make(Sample)
        self.mer_sample.sample_name = 'test_sample_name'
        self.mer_sample.sample_type = 'MER'
        self.mer_sample.sample_id = self.mer_sample.generate_sample_id()

    def test_sample_creation(self):
        assert isinstance(self.bmh_sample, Sample)
        assert self.bmh_sample.__str__() == self.bmh_sample.sample_id

    def test_sample_year(self):
        assert self.bmh_sample.sample_year == str(self.bmh_sample.created.year)

    def test_generate_sample_id(self):
        assert self.mer_sample.sample_id == \
               f'{self.mer_sample.sample_type}-{self.mer_sample.sample_year}-{self.mer_sample.pk:06}'


class MergedSampleComponentTest(TestCase):
    @staticmethod
    def test_merged_sample_component_creation():
        component = mommy.make(MergedSampleComponent)
        assert isinstance(component, MergedSampleComponent)
        assert component.__str__() == f"{component.component_id} ({component.group_id})"


class SampleLogDataTest(TestCase):
    def setUp(self):
        self.sample_log_data = mommy.make(SampleLogData)
        self.sample_log_data.sample_yield = 1000000

    def test_sample_log_data_creation(self):
        assert isinstance(self.sample_log_data, SampleLogData)
        assert self.sample_log_data.__str__() == str(self.sample_log_data.sample_id)

    def test_sample_yield_mbp(self):
        assert self.sample_log_data.sample_yield_mbp == float(self.sample_log_data.sample_yield / 1000000)


class SampleAssemblyDataTest(TestCase):
    def setUp(self):
        self.sample_assembly_data = mommy.make(SampleAssemblyData)

    def test_sample_assembly_data_creation(self):
        assert isinstance(self.sample_assembly_data, SampleAssemblyData)
        assert self.sample_assembly_data.__str__() == str(self.sample_assembly_data.sample_id)

    def test_get_assembly_path(self):
        assembly = tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8')
        assembly.write(">TEST\nATCG")
        assembly.flush()
        self.sample_assembly_data.assembly = str(assembly.name)
        assert type(self.sample_assembly_data.get_assembly_path()) == PosixPath

    def test_assembly_exists(self):
        assert self.sample_assembly_data.assembly_exists() is False

        # Create assembly then check if fn returns True
        assembly = tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8')
        assembly.write(">TEST\nATCG")
        assembly.flush()
        self.sample_assembly_data.assembly = str(assembly.name)
        assert self.sample_assembly_data.assembly_exists() is True
