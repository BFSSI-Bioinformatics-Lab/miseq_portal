"""
Minimal assembly pipeline. Intended for prokaryotic assemblies.

1. QC on reads with bbduk.sh (adapter trimming/quality filtering)
2. Error-correction of reads with tadpole.sh
3. Assembly of reads with skesa
4. Polishing of assembly with pilon
5. Assembly metrics with quast.py
6. Coverage stats with Qualimap

"""
import logging
import os
import shutil
from pathlib import Path

import pandas as pd

from config.settings.base import MEDIA_ROOT
from miseq_portal.analysis.tools.helpers import run_subprocess, remove_fastq_and_bam_files
from miseq_portal.miseq_viewer.models import SampleAssemblyData, upload_assembly

logger = logging.getLogger('django')

MEDIA_ROOT = Path(MEDIA_ROOT)


def extract_coverage_from_qualimap_results(qualimap_result_file: Path) -> tuple:
    """
    Given a Qualimap result file, extract mean coverage and standard deviation for coverage.
    :param qualimap_result_file: Standard text output file from Qualimap
    :return: tuple(mean_coverage, std_coverage)
    """
    mean_coverage = None
    std_coverage = None
    with open(str(qualimap_result_file), 'r') as f:
        lines = f.readlines()
        for line in lines:
            if 'mean coverageData' in line:
                mean_coverage = line.split(" = ")[1].strip()
            elif 'std coverageData' in line:
                std_coverage = line.split(" = ")[1].strip()
            else:
                continue
    return mean_coverage, std_coverage


def call_qualimap(bamfile: Path, outdir: Path) -> Path:
    """
    Makes a system call to Qualimap with the provided .bam file. Finds and returns the output file (genome_results.txt)
    :param bamfile: .bam file generated via BBmap.sh
    :param outdir: output directory for Qualimap output
    :return: path to Qualimap genome_results.txt file
    """
    qualimap_dir = outdir / 'qualimap'
    cmd = f"qualimap bamqc -bam {bamfile} -outdir {qualimap_dir} --java-mem-size=32G"
    run_subprocess(cmd)
    qualimap_result_file = qualimap_dir / 'genome_results.txt'
    if not qualimap_result_file.is_file():
        logging.warning(f"ERROR: Could not find genome_results.txt in {qualimap_dir}")
        qualimap_result_file = None
    return qualimap_result_file


def assembly_pipeline(fwd_reads: Path, rev_reads: Path, outdir: Path, sample_id: str) -> (Path, Path):
    """
    Wrapper for high-level steps of the assembly pipeline.
    1. BBduk (read QC)
    2. Tadpole (read correction)
    3. SKESA (assembly)
    4. BBmap (bamfile)
    5. pilon (assembly polishing)
    :param fwd_reads: Path to forward reads (.fastq.gz)
    :param rev_reads:  Path to reverse reads (.fastq.gz)
    :param outdir: Path to output directory for sample
    :param sample_id: Sample ID (e.g. BMH-2017-000001) corresponding to miseq_viewer.models.Sample
    :return: Path to .bam from BBmap and .fasta assembly from Pilon
    """
    fwd_reads, rev_reads = call_repair(fwd_reads=fwd_reads, rev_reads=rev_reads, outdir=outdir)
    fwd_reads, rev_reads = call_bbduk(fwd_reads=fwd_reads, rev_reads=rev_reads, outdir=outdir)
    fwd_reads, rev_reads = call_tadpole(fwd_reads=fwd_reads, rev_reads=rev_reads, outdir=outdir)
    assembly = call_skesa(fwd_reads=fwd_reads, rev_reads=rev_reads, outdir=outdir, sample_id=sample_id)
    bamfile = call_bbmap(fwd_reads=fwd_reads, rev_reads=rev_reads, outdir=outdir, assembly=assembly)
    polished_assembly = call_pilon(outdir=outdir, assembly=assembly, prefix=sample_id, bamfile=bamfile)
    return bamfile, polished_assembly


def upload_sampleassembly_data(sample_assembly_instance: SampleAssemblyData, assembly: Path, quast_df: pd.DataFrame,
                               mean_coverage: str, std_coverage: str, num_predicted_genes: int) -> SampleAssemblyData:
    """
    Given an assembly, quast and qualimap results, uploads everything to miseq_viewer.models.SampleAssemblyInstance
    :param sample_assembly_instance: Model instance to update
    :param assembly: Path to assembly fasta file
    :param quast_df: Pandas dataframe of the quast output file (generated via assemble_run.get_quast_df())
    :param mean_coverage: Mean coverage value from Qualimap outputfile
    :param std_coverage: Standard deviation coverage value from Qualimap output file
    :param num_predicted_genes: Total # of predicted genes detected by Prodigal
    """
    # Save to the DB
    sample_assembly_instance.assembly = upload_assembly(sample_assembly_instance, str(assembly.name))
    sample_assembly_instance.num_contigs = quast_df["# contigs"][0]
    sample_assembly_instance.largest_contig = quast_df["Largest contig"][0]
    sample_assembly_instance.total_length = quast_df["Total length"][0]
    sample_assembly_instance.gc_percent = quast_df["GC (%)"][0]
    sample_assembly_instance.n50 = quast_df["N50"][0]
    sample_assembly_instance.num_predicted_genes = num_predicted_genes
    sample_assembly_instance.mean_coverage = mean_coverage
    sample_assembly_instance.std_coverage = std_coverage
    sample_assembly_instance.bbduk_version = get_bbduk_version()
    sample_assembly_instance.bbmap_version = get_bbmap_version()
    sample_assembly_instance.tadpole_version = get_tadpole_version()
    sample_assembly_instance.pilon_version = get_pilon_version()
    sample_assembly_instance.skesa_version = get_skesa_version()
    sample_assembly_instance.quast_version = get_quast_version()
    return sample_assembly_instance


def run_prodigal(assembly: Path, outdir: Path) -> Path:
    """
    Makes a system call to Prodigal on a given assembly
    :param assembly: Path object to FASTA assembly
    :param outdir: Path object to desired output directory
    :return: Path to output file generated by Prodigal
    """
    outfile = outdir / assembly.with_suffix(".prodigal.genes").name
    cmd = f"prodigal -i {assembly} -o {outfile}"
    run_subprocess(cmd)
    return outfile


def count_prodigal_genes(prodigal_gene_file: Path) -> int:
    """
    System call to grep to count the number of genes predicted by Prodigal
    :param prodigal_gene_file: Path object to file generated by run_prodigal() method
    :return: Integer indicating the total number of predicted genes
    """
    cmd = f"grep -c 'CDS' {prodigal_gene_file}"
    num_genes = run_subprocess(cmd, get_stdout=True)
    return int(num_genes)


def prodigal_pipeline(assembly: Path, outdir: Path) -> int:
    """
    System call to Prodigal, then parses the output file to determine the total # of predicted genes
    :param assembly: Path object to FASTA assembly
    :param outdir: Path object to desired output directory
    :return: Integer indicating the total number of predicted genes
    """
    prodigal_gene_file = run_prodigal(assembly=assembly, outdir=outdir)
    gene_count = count_prodigal_genes(prodigal_gene_file=prodigal_gene_file)
    return gene_count


def run_quast(assembly: Path, outdir: Path) -> Path:
    """
    Makes a system call to quast.py with a given assembly.
    Note that the license for GeneMarkS might expire, breaking the --gene-finding function and potentially effecting
    downstream functionality built around this (e.g. the sample detail .html template)
    :param assembly: Path to assembly for a particular sample_id
    :param outdir: Path to directory to store quast.py output
    :return: Output file from quast.py (transposed_report.tsv)
    """
    # Min contig needs to be set low in order to accomodate very bad assemblies, otherwise quast will fail
    cmd = f"quast.py --no-plots --no-html --no-icarus --min-contig 100 -o {outdir} {assembly}"
    run_subprocess(cmd)
    transposed_report = list(outdir.glob("transposed_report.tsv"))[0]
    return transposed_report


def get_quast_df(report: Path) -> pd.DataFrame:
    """
    Reads in transposed_report.tsv generated by quast.py
    :param report: Path to transposed_report.tsv
    :return: Pandas dataframe of transposed_report.tsv
    """
    df = pd.read_csv(report, sep="\t")
    df = df.fillna(value="")
    return df


def assembly_cleanup(assembly_dir: Path, assembly: Path) -> Path:
    """
    Removes extraneous files after assembly is complete, moves the pilon assembly to the root folder for Sample
    :param assembly_dir: Directory containing assembly output for a given Sample
    :param assembly: Path to the polished assembly .fasta file
    :return: New path to polished assembly
    """

    # Delete everything except for the polished assembly
    remove_fastq_and_bam_files(target_directory=assembly_dir)
    # Move the polished assembly to the root
    shutil.move(str(assembly),
                str(assembly_dir / assembly.name))
    assembly = assembly_dir / assembly.name
    # Delete the pilon folder
    shutil.rmtree(str(assembly_dir / "pilon"))
    return assembly


def get_quast_version() -> str:
    """
    Grabs text output from --version system call to quast.py
    :return: String containing stdout from quast.py --version
    """
    cmd = f"quast.py --version"
    version = run_subprocess(cmd, get_stdout=True)
    return version


def get_skesa_version() -> str:
    """
    Grabs text output from --version system call to skesa
    :return: String containing stdout from skesa --version
    """
    cmd = f"skesa --version"
    version = run_subprocess(cmd, get_stdout=True)
    return version


def get_tadpole_version() -> str:
    """
    Grabs text output from --version system call to tadpole.sh
    :return: String containing stdout from tadpole.sh --version
    """
    cmd = f"tadpole.sh --version"
    version = run_subprocess(cmd, get_stdout=True)
    version = extract_bbtool_version_line(version)
    return version


def extract_bbtool_version_line(version: str) -> str:
    # Extract version line
    elements = version.split("\n")
    for e in elements:
        if 'version' in e.lower():
            version = e
    return version


def get_bbmap_version() -> str:
    """
    Grabs text output from --version system call to bbmap.sh
    :return: String containing stdout from bbmap.sh --version
    """
    cmd = f"bbmap.sh --version"
    version = run_subprocess(cmd, get_stdout=True)

    # Extract version line
    version = extract_bbtool_version_line(version)

    return version


def get_bbduk_version() -> str:
    """
    Grabs text output from --version system call to bbduk.sh
    :return: String containing stdout from bbduk.sh --version
    """
    cmd = f"bbduk.sh --version"
    version = run_subprocess(cmd, get_stdout=True)

    # Extract version line
    version = extract_bbtool_version_line(version)

    return version


def get_pilon_version() -> str:
    """
    Grabs text output from --version system call to pilon
    :return: String containing stdout from pilon --version
    """
    cmd = f"pilon --version"
    version = run_subprocess(cmd, get_stdout=True)
    return version


def call_pilon(bamfile: Path, outdir: Path, assembly: Path, prefix: str, memory: str = '128g') -> Path:
    """
    Polishes an assembly with a system call to Pilon
    :param bamfile: Path .bam file for sample (--bam in pilon)
    :param outdir: Path to output directory (--outdir in pilon)
    :param assembly: Path to assembly (--genome in pilon)
    :param prefix: String to feed to --output param of pilon
    :param memory: String with memory to allocate to pilon i.e. 128g.
    :return: Path to polished assembly
    """
    outdir = outdir / 'pilon'
    os.makedirs(str(outdir), exist_ok=True)
    cmd = f"pilon -Xmx{memory} --genome {assembly} --bam {bamfile} --outdir {outdir} --output {prefix}"
    run_subprocess(cmd)
    try:
        polished_assembly = list(outdir.glob("*.fasta"))[0]
    except IndexError:
        logger.debug(f"Pilon call failed - using original assembly {assembly}")
        return assembly
    return polished_assembly


def call_fastqc():
    # TODO: Implement!
    pass


def call_skesa(fwd_reads: Path, rev_reads: Path, outdir: Path, sample_id: str) -> Path:
    """
    System call to skesa to complete an assembly
    :param fwd_reads: Path to forward reads for a sample
    :param rev_reads: Path to reverse reads for a sample
    :param outdir: Output directory for skesa
    :param sample_id: String of sample ID of sample
    :return: Path to completed assembly
    """
    assembly_out = outdir / Path(sample_id + ".contigs.fa")

    if assembly_out.exists():
        return assembly_out

    cmd = f'skesa --use_paired_ends --fastq "{fwd_reads},{rev_reads}" --contigs_out {assembly_out}'
    logger.info(cmd)
    run_subprocess(cmd)
    return assembly_out


def index_bamfile(bamfile: Path):
    """
    System call to samtools index on a given .bam file
    :param bamfile: Path to .bam file
    """
    cmd = f"samtools index {bamfile}"
    run_subprocess(cmd)


def call_bbmap(fwd_reads: Path, rev_reads: Path, outdir: Path, assembly: Path) -> Path:
    """
    System call to bbmap.sh to align reads against a given assembly
    :param fwd_reads: Path to forward reads (.fastq.gz)
    :param rev_reads: Path to reverse reads (.fastq.gz)
    :param outdir: Path to desired output directory
    :param assembly: Path to existing assembly (.fasta)
    :return: Path to sorted .bam file
    """
    outbam = outdir / assembly.with_suffix(".bam").name

    # If the output .bam file was already generated for some reason, quit early
    if outbam.exists():
        return outbam

    """
    NOTE: Added deterministic=t averagepairdist=50 and pigz=t on May 6th, 2019.
    This ensures calls to bbmap.sh on a pair of reads will always result in the exact same output; this was not the
    case previously.
    """
    cmd = f"bbmap.sh in1={fwd_reads} in2={rev_reads} ref={assembly} out={outbam} overwrite=t " \
          f"pigz=t deterministic=t unbgzip=f averagepairdist=50"
    logger.info(cmd)
    run_subprocess(cmd, cwd=outdir)

    # Sort .bam produced by bbmap.sh
    sorted_bam_file = sort_bamfile(bamfile=outbam, outdir=outdir)

    # Index .bam with samtools index
    index_bamfile(sorted_bam_file)

    return sorted_bam_file


def sort_bamfile(bamfile: Path, outdir: Path) -> Path:
    sorted_bam_file = outdir / bamfile.name.replace(".bam", "_sorted.bam")
    cmd = f"samtools sort --output-fmt BAM -o {sorted_bam_file} {bamfile}"
    logger.info(cmd)
    run_subprocess(cmd)
    return sorted_bam_file


def call_tadpole(fwd_reads: Path, rev_reads: Path, outdir: Path) -> tuple:
    """
    System call to tadpole.sh to correct reads
    :param fwd_reads: Path to forward reads (.fastq.gz)
    :param rev_reads: Path to reverse reads (.fastq.gz)
    :param outdir: Path to desired output directory
    :return: tuple(corrected forward reads, corrected reverse reads)
    """
    fwd_out = outdir / fwd_reads.name.replace(".filtered.", ".corrected.")
    rev_out = outdir / rev_reads.name.replace(".filtered.", ".corrected.")

    # Exit out of function early if the corrected reads already exist for some reason
    if fwd_out.exists() and rev_out.exists():
        return fwd_out, rev_out

    cmd = f"tadpole.sh in1={fwd_reads} in2={rev_reads} out1={fwd_out} out2={rev_out} mode=correct unbgzip=f"
    run_subprocess(cmd)
    return fwd_out, rev_out


def bbduk_trim_adapters(fwd_reads: Path, rev_reads: Path, outdir: Path) -> tuple:
    fwd_out = outdir / fwd_reads.name.replace(".fastq.gz", ".cleaned.fastq.gz")
    rev_out = outdir / rev_reads.name.replace(".fastq.gz", ".cleaned.fastq.gz")
    stats_out = outdir / 'adapter_trimming_stats.txt'
    cmd = f"bbduk.sh in1={fwd_reads} in2={rev_reads} out1={fwd_out} out2={rev_out} " \
          f"ref=adapters tpe tbo overwrite=t unbgzip=f ktrim=r k=23 mink=11 hdist=1 stats={stats_out}"
    run_subprocess(cmd)
    return fwd_out, rev_out


def bbduk_qc_filtering(fwd_reads: Path, rev_reads: Path, outdir: Path) -> tuple:
    fwd_out = outdir / fwd_reads.name.replace(".fastq.gz", ".filtered.fastq.gz")
    rev_out = outdir / rev_reads.name.replace(".fastq.gz", ".filtered.fastq.gz")
    stats_out = outdir / 'quality_filtering_stats.txt'
    cmd = f"bbduk.sh in1={fwd_reads} in2={rev_reads} out1={fwd_out} out2={rev_out} unbgzip=f qtrim=rl " \
          f"trimq=10 2> {stats_out}"
    run_subprocess(cmd)
    return fwd_out, rev_out


def call_bbduk(fwd_reads: Path, rev_reads: Path, outdir: Path) -> tuple:
    """
    System call to bbduk.sh to perform adapter trimming/quality filtering on a given read pair
    :param fwd_reads: Path to forward reads (.fastq.gz)
    :param rev_reads: Path to reverse reads (.fastq.gz)
    :param outdir: Path to desired output directory
    :return: tuple(filtered forward reads, filtered reverse reads)
    """
    fwd_reads_trimmed, rev_reads_trimmed = bbduk_trim_adapters(fwd_reads=fwd_reads, rev_reads=rev_reads, outdir=outdir)
    fwd_reads_filtered, rev_reads_filtered = bbduk_qc_filtering(fwd_reads=fwd_reads_trimmed,
                                                                rev_reads=rev_reads_trimmed, outdir=outdir)
    return fwd_reads_filtered, rev_reads_filtered


def call_repair(fwd_reads: Path, rev_reads: Path, outdir: Path) -> tuple:
    fwd_out = outdir / fwd_reads.name
    rev_out = outdir / rev_reads.name

    cmd = f"repair.sh in={fwd_reads} in2={rev_reads} out={fwd_out} out2={rev_out} overwrite=t"
    run_subprocess(cmd)
    return fwd_out, rev_out
