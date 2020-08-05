"""
Tools to work with plasmids.

General overview:
1. Attempt to reconstruct plasmid(s) with MOB-suite mob_recon https://github.com/phac-nml/mob-suite
2a. Conduct AMR profiling on extracted plasmid(s) with ABRicate https://github.com/tseemann/abricate
2b. Maybe use https://github.com/phac-nml/staramr instead? Investigate


"""

from pathlib import Path

from dataclasses import dataclass

from django.conf import settings
from miseq_portal.analysis.tools.helpers import run_subprocess

MOB_RECON = settings.MOB_RECON_EXE


@dataclass
class MobSuiteDataObject:
    original_contigs: Path
    contig_report: Path
    mobtyper_aggregate_report: Path
    plasmid_fasta_list: [Path]


def call_mob_recon(assembly: Path, outdir: Path) -> MobSuiteDataObject:
    cmd = f'{MOB_RECON} --infile {assembly} --outdir {outdir} --run_typer'
    run_subprocess(cmd)
    contig_report = list(outdir.glob("contig_report.txt"))[0]
    mobtyper_aggregate_report = list(outdir.glob("mobtyper_aggregate_report.txt"))[0]
    plasmid_fasta_list = list(outdir.glob("plasmid_*.fasta"))
    mob_recon_data = MobSuiteDataObject(original_contigs=assembly,
                                        contig_report=contig_report,
                                        mobtyper_aggregate_report=mobtyper_aggregate_report,
                                        plasmid_fasta_list=plasmid_fasta_list)
    return mob_recon_data


@dataclass
class AbricateDataObject:
    pass


def call_abricate(contigs: Path, outdir: Path) -> AbricateDataObject:
    pass


@dataclass
class StaramrDataObject:
    pass


def call_staramr(contigs: Path, outdir: Path) -> StaramrDataObject:
    pass
