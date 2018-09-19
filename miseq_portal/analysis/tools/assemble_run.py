"""
Minimal assembly pipeline. Intended for prokaryotic assemblies.

1. QC on reads with bbduk.sh (adapter trimming/quality filtering)
2. Error-correction of reads with tadpole.sh
3. Assembly of reads with skesa
4. Polishing of assembly with pilon
5. Assembly metrics with quast.py

"""
import os
import shutil
import pandas as pd
from pathlib import Path
from subprocess import Popen, PIPE
from celery import shared_task
from config.settings.base import MEDIA_ROOT

from miseq_portal.miseq_viewer.models import Sample, SampleAssemblyData, upload_assembly

import logging

logger = logging.getLogger('raven')

MEDIA_ROOT = Path(MEDIA_ROOT)


# TODO: Move this to ../tasks.py
@shared_task()
def assemble_sample_instance(sample_object_id: str):
    try:
        sample_instance = Sample.objects.get(sample_id=sample_object_id)
    except Sample.DoesNotExist:
        logger.error("Sample {} does not exist. Skipping assembly.")
        return

    # Setup assembly directory on NAS
    outdir = MEDIA_ROOT / Path(str(sample_instance.fwd_reads)).parent / "assembly"
    os.makedirs(outdir, exist_ok=True)

    # Get/create SampleAssemblyData instance
    sample_assembly_instance, sa_created = SampleAssemblyData.objects.get_or_create(sample_id=sample_instance)
    if sa_created or str(sample_assembly_instance.assembly) == '' or sample_assembly_instance.assembly is None:
        logger.info(f"Running assembly pipeline on {sample_instance}...")
        polished_assembly = assembly_pipeline(
            fwd_reads=MEDIA_ROOT / Path(str(sample_instance.fwd_reads)),
            rev_reads=MEDIA_ROOT / Path(str(sample_instance.rev_reads)),
            outdir=outdir,
            sample_id=str(sample_instance.sample_id)
        )
        polished_assembly = assembly_cleanup(outdir=outdir, assembly=polished_assembly)

        # Run and parse Quast
        report_file = run_quast(assembly=polished_assembly, outdir=outdir)
        quast_df = get_quast_df(report_file)

        # Push the data to the database for SampleAssemblyData
        upload_sampleassembly_data(sample_assembly_instance=sample_assembly_instance,
                                   assembly=polished_assembly,
                                   quast_df=quast_df)
    else:
        logger.info(f"Assembly for {sample_assembly_instance.sample_id} already exists. Skipping.")


def assembly_pipeline(fwd_reads: Path, rev_reads: Path, outdir: Path, sample_id: str):
    fwd_reads, rev_reads = call_bbduk(fwd_reads=fwd_reads, rev_reads=rev_reads, outdir=outdir)
    fwd_reads, rev_reads = call_tadpole(fwd_reads=fwd_reads, rev_reads=rev_reads, outdir=outdir)
    assembly = call_skesa(fwd_reads=fwd_reads, rev_reads=rev_reads, outdir=outdir, sample_id=sample_id)
    bamfile = call_bbmap(fwd_reads=fwd_reads, rev_reads=rev_reads, outdir=outdir, assembly=assembly)
    polished_assembly = call_pilon(outdir=outdir, assembly=assembly, prefix=sample_id, bamfile=bamfile)
    return polished_assembly


def upload_sampleassembly_data(sample_assembly_instance: SampleAssemblyData, assembly: Path, quast_df: pd.DataFrame):
    # Save to the DB
    sample_assembly_instance.assembly = upload_assembly(sample_assembly_instance, str(assembly.name))
    sample_assembly_instance.num_contigs = quast_df["# contigs"][0]
    sample_assembly_instance.largest_contig = quast_df["Largest contig"][0]
    sample_assembly_instance.total_length = quast_df["Total length"][0]
    sample_assembly_instance.gc_percent = quast_df["GC (%)"][0]
    sample_assembly_instance.n50 = quast_df["N50"][0]
    sample_assembly_instance.bbduk_version = get_bbduk_version()
    sample_assembly_instance.bbmap_version = get_bbmap_version()
    sample_assembly_instance.tadpole_version = get_tadpole_version()
    sample_assembly_instance.pilon_version = get_pilon_version()
    sample_assembly_instance.skesa_version = get_skesa_version()
    sample_assembly_instance.quast_version = get_quast_version()
    sample_assembly_instance.save()


def run_quast(assembly: Path, outdir: Path):
    # Min contig needs to be set low in order to accomodate very bad assemblies, otherwise quast will fail
    cmd = f"quast.py --no-plots --no-html --no-icarus --min-contig 100 -o {outdir} {assembly}"
    run_subprocess(cmd)
    transposed_report = list(outdir.glob("transposed_report.tsv"))[0]
    return transposed_report


def get_quast_df(report: Path):
    df = pd.read_csv(report, sep="\t")
    return df


def assembly_cleanup(outdir: Path, assembly: Path):
    # Delete everything except for the polished assembly
    remove_dir_files(outdir=outdir)
    # Move the polished assembly to the root
    shutil.move(str(assembly),
                str(outdir / assembly.name))
    assembly = outdir / assembly.name
    # Delete the pilon folder
    shutil.rmtree(str(outdir / "pilon"))
    return assembly


def remove_dir_files(outdir: Path):
    to_delete = list(outdir.glob("*.*"))
    for f in to_delete:
        os.remove(str(f))


def get_quast_version():
    cmd = f"quast.py --version"
    version = run_subprocess(cmd, get_stdout=True)
    return version


def get_skesa_version():
    cmd = f"skesa --version"
    version = run_subprocess(cmd, get_stdout=True)
    return version


def get_tadpole_version():
    cmd = f"tadpole.sh --version"
    version = run_subprocess(cmd, get_stdout=True)
    return version


def get_bbmap_version():
    cmd = f"bbmap.sh --version"
    version = run_subprocess(cmd, get_stdout=True)
    return version


def get_bbduk_version():
    cmd = f"bbduk.sh --version"
    version = run_subprocess(cmd, get_stdout=True)
    return version


def get_pilon_version():
    cmd = f"pilon --version"
    version = run_subprocess(cmd, get_stdout=True)
    return version


def run_subprocess(cmd: str, get_stdout=False):
    if get_stdout:
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        out = out.decode().strip()
        err = err.decode().strip()
        if out != "":
            return out
        elif err != "":
            return err
        else:
            return ""
    else:
        p = Popen(cmd, shell=True)
        p.wait()


def call_pilon(bamfile: Path, outdir: Path, assembly: Path, prefix: str):
    outdir = outdir / 'pilon'
    os.makedirs(str(outdir), exist_ok=True)
    cmd = f"pilon -Xmx128g --genome {assembly} --bam {bamfile} --outdir {outdir} --output {prefix}"
    run_subprocess(cmd)
    polished_assembly = list(outdir.glob("*.fasta"))[0]
    return polished_assembly


def call_skesa(fwd_reads: Path, rev_reads: Path, outdir: Path, sample_id: str):
    assembly_out = outdir / Path(sample_id + ".contigs.fa")

    if assembly_out.exists():
        return assembly_out

    cmd = f'skesa --use_paired_ends --gz --fastq "{fwd_reads},{rev_reads}" --contigs_out {assembly_out}'
    run_subprocess(cmd)
    return assembly_out


def index_bamfile(bamfile: Path):
    cmd = f"samtools index {bamfile}"
    run_subprocess(cmd)


def call_bbmap(fwd_reads: Path, rev_reads: Path, outdir: Path, assembly: Path):
    outbam = outdir / assembly.with_suffix(".bam").name

    if outbam.exists():
        return outbam

    cmd = f"bbmap.sh in1={fwd_reads} in2={rev_reads} ref={assembly} out={outbam} overwrite=t bamscript=bs.sh; sh bs.sh"
    run_subprocess(cmd)

    sorted_bam_file = outdir / outbam.name.replace(".bam", "_sorted.bam")
    index_bamfile(sorted_bam_file)
    return sorted_bam_file


def call_tadpole(fwd_reads: Path, rev_reads: Path, outdir: Path):
    fwd_out = outdir / fwd_reads.name.replace(".filtered.", ".corrected.")
    rev_out = outdir / rev_reads.name.replace(".filtered.", ".corrected.")

    if fwd_out.exists() and rev_out.exists():
        return fwd_out, rev_out

    cmd = f"tadpole.sh in1={fwd_reads} in2={rev_reads} out1={fwd_out} out2={rev_out} mode=correct"
    run_subprocess(cmd)
    return fwd_out, rev_out


def call_bbduk(fwd_reads: Path, rev_reads: Path, outdir: Path):
    fwd_out = outdir / fwd_reads.name.replace(".fastq.gz", ".filtered.fastq.gz")
    rev_out = outdir / rev_reads.name.replace(".fastq.gz", ".filtered.fastq.gz")

    if fwd_out.exists() and rev_out.exists():
        return fwd_out, rev_out

    # TODO: Store these parameters for BBDuk + other system tools in a single config file
    cmd = f"bbduk.sh in1={fwd_reads} in2={rev_reads} out1={fwd_out} out2={rev_out} " \
          f"ref=adapters maq=12 qtrim=rl tpe tbo overwrite=t"
    run_subprocess(cmd)
    return fwd_out, rev_out
