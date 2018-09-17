"""
Minimal assembly pipeline
"""
import os
from pathlib import Path
from subprocess import Popen
from celery import shared_task
from config.settings.base import MEDIA_ROOT

from miseq_portal.miseq_viewer.models import Sample, SampleAssemblyData

import logging

logger = logging.getLogger('raven')

MEDIA_ROOT = Path(MEDIA_ROOT)


@shared_task()
def assemble_sample_object_list(sample_object_id_list: [str]):
    for sample_object_id in sample_object_id_list:
        sample_instance = Sample.objects.get(sample_id=sample_object_id)
        outdir = MEDIA_ROOT / Path(str(sample_instance.fwd_reads)).parent / "assembly"
        os.makedirs(outdir, exist_ok=True)

        sample_assembly_instance, sa_created = SampleAssemblyData.objects.get_or_create(sample_id=sample_instance)
        if sa_created:
            logger.info(f"Running assembly pipeline on {sample_instance}...")
            polished_assembly = assembly_pipeline(
                fwd_reads=MEDIA_ROOT / Path(str(sample_instance.fwd_reads)),
                rev_reads=MEDIA_ROOT / Path(str(sample_instance.rev_reads)),
                outdir=outdir,
                sample_id=str(sample_instance.sample_id)
            )
            sample_assembly_instance.assembly = str(polished_assembly).replace(str(MEDIA_ROOT), "")

            # TODO: Populate versions of assembly dependencies within the sample_assembly_instance
            # TODO: Cleanup everything except the assembly fasta upon completion

            sample_assembly_instance.save()
        else:
            logger.info(f"Assembly for {sample_assembly_instance.sample_id} already exists. Skipping.")


def assembly_pipeline(fwd_reads: Path, rev_reads: Path, outdir: Path, sample_id: str):
    fwd_reads, rev_reads = call_bbduk(fwd_reads=fwd_reads, rev_reads=rev_reads, outdir=outdir)
    fwd_reads, rev_reads = call_tadpole(fwd_reads=fwd_reads, rev_reads=rev_reads, outdir=outdir)
    assembly = call_skesa(fwd_reads=fwd_reads, rev_reads=rev_reads, outdir=outdir, sample_id=sample_id)
    bamfile = call_bbmap(fwd_reads=fwd_reads, rev_reads=rev_reads, outdir=outdir, assembly=assembly)
    polished_assembly = call_pilon(outdir=outdir, assembly=assembly, prefix=sample_id, bamfile=bamfile)
    return polished_assembly


def cleanup_assembly_pipeline(outdir: Path):
    fastq_files = outdir.glob("*.fastq.gz")
    for fastq_file in fastq_files:
        os.remove(str(fastq_file))


def call_pilon(bamfile: Path, outdir: Path, assembly: Path, prefix: str):
    outdir = outdir / 'pilon'
    os.makedirs(str(outdir), exist_ok=True)
    cmd = f"pilon -Xmx128g --genome {assembly} --bam {bamfile} --outdir {outdir} --output {prefix} --vcf"
    p = Popen(cmd, shell=True)
    p.wait()
    return outdir


def call_skesa(fwd_reads: Path, rev_reads: Path, outdir: Path, sample_id: str):
    assembly_out = outdir / Path(sample_id + ".contigs.fa")

    if assembly_out.exists():
        return assembly_out

    cmd = f'skesa --use_paired_ends --gz --fastq "{fwd_reads},{rev_reads}" --contigs_out {assembly_out}'
    p = Popen(cmd, shell=True)
    p.wait()
    return assembly_out


def index_bamfile(bamfile: Path):
    cmd = f"samtools index {bamfile}"
    p = Popen(cmd, shell=True)
    p.wait()


def call_bbmap(fwd_reads: Path, rev_reads: Path, outdir: Path, assembly: Path):
    outbam = outdir / assembly.with_suffix(".bam").name

    if outbam.exists():
        return outbam

    cmd = f"bbmap.sh in1={fwd_reads} in2={rev_reads} ref={assembly} out={outbam} overwrite=t bamscript=bs.sh; sh bs.sh"
    p = Popen(cmd, shell=True)
    p.wait()

    sorted_bam_file = outdir / outbam.name.replace(".bam", "_sorted.bam")
    index_bamfile(sorted_bam_file)
    return sorted_bam_file


def call_tadpole(fwd_reads: Path, rev_reads: Path, outdir: Path):
    fwd_out = outdir / fwd_reads.name.replace(".filtered.", ".corrected.")
    rev_out = outdir / rev_reads.name.replace(".filtered.", ".corrected.")

    if fwd_out.exists() and rev_out.exists():
        return fwd_out, rev_out

    cmd = f"tadpole.sh in1={fwd_reads} in2={rev_reads} out1={fwd_out} out2={rev_out} mode=correct"
    p = Popen(cmd, shell=True)
    p.wait()
    return fwd_out, rev_out


def call_bbduk(fwd_reads: Path, rev_reads: Path, outdir: Path):
    fwd_out = outdir / fwd_reads.name.replace(".fastq.gz", ".filtered.fastq.gz")
    rev_out = outdir / rev_reads.name.replace(".fastq.gz", ".filtered.fastq.gz")

    if fwd_out.exists() and rev_out.exists():
        return fwd_out, rev_out

    # TODO: Store these parameters for BBDuk + other system tools in a single config file
    cmd = f"bbduk.sh in1={fwd_reads} in2={rev_reads} out1={fwd_out} out2={rev_out} " \
          f"ref=adapters maq=12 qtrim=rl tpe tbo overwrite=t"
    p = Popen(cmd, shell=True)
    p.wait()
    return fwd_out, rev_out
