import mock
import pytest
from pathlib import Path
from miseq_portal.analysis.tools import helpers

pytestmark = pytest.mark.django_db


def test_run_subprocess():
    assert helpers.run_subprocess("echo test", get_stdout=True) == "test"


def test_remove_dir_files():
    assert helpers.remove_fastq_and_bam_files(Path("/fake/directory")) is None
