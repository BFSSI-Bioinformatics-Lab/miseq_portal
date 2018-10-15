import tempfile
import pytest
from pathlib import Path, PosixPath
from miseq_portal.analysis.tools import assemble_run

pytestmark = pytest.mark.django_db


def test_get_quast_df():
    tsv_file = tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8')
    tsv_file.write("col1\tcol2\n1\t2")
    tsv_file.flush()
    df = assemble_run.get_quast_df(Path(tsv_file.name))
    assert len(df) == 1


def test_run_quast():
    assembly = tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8')
    assembly.write(">TEST\n")
    assembly.write("ATCG" * 1000)
    assembly.flush()
    outdir = tempfile.TemporaryDirectory()
    assert type(assemble_run.run_quast(assembly=Path(assembly.name), outdir=Path(outdir.name))) == PosixPath
    outdir.cleanup()


def test_get_quast_version():
    quast_version = assemble_run.get_quast_version()
    assert 'quast' in quast_version.lower()


def test_get_skesa_version():
    skesa_version = assemble_run.get_skesa_version()
    assert 'skesa' in skesa_version.lower()


def test_get_tadpole_version():
    tadpole_version = assemble_run.get_tadpole_version()
    assert 'tadpole' in tadpole_version.lower()


def test_get_bbduk_version():
    bbduk_version = assemble_run.get_bbduk_version()
    assert 'bbduk' in bbduk_version.lower()


def test_get_pilon_version():
    pilon_version = assemble_run.get_pilon_version()
    assert 'pilon' in pilon_version.lower()
