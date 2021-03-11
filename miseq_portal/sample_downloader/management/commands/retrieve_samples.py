from pathlib import Path
from django.core.management.base import BaseCommand
from miseq_portal.miseq_viewer.models import Sample
from miseq_portal.minion_viewer.models import MinIONSample


class Command(BaseCommand):
    help = 'This script will read a text file with sample IDs each on a new line and create symlinks for the requested ' \
           'data into a destination folder'

    def add_arguments(self, parser):
        parser.add_argument('--samples', type=str, help='Path to input product JSON directory')
        parser.add_argument('--outdir', type=str, help='Path to input product JSON directory')
        parser.add_argument('--assemblies', action='store_true',
                            help='Retrieve assemblies')
        parser.add_argument('--reads', action='store_true',
                            help='Retrieve reads')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f''))

        if not options['assemblies'] and not options['reads']:
            self.stdout.write(self.style.ERROR(f'Please set the --assemblies and/or --reads flag.'))
            quit()

        sample_file = Path(options['samples'])
        assert sample_file.exists()

        outdir = Path(options['outdir'])
        outdir.mkdir(exist_ok=True)

        with open(sample_file, 'r') as f:
            samples = [s.strip() for s in f.readlines()]

        sample_objects = []
        minion_sample_objects = []
        for s in samples:
            try:
                if s.startswith("MIN-"):
                    minion_sample_objects.append(MinIONSample.objects.get(sample_id=s))
                else:
                    sample_objects.append(Sample.objects.get(sample_id=s))
            except BaseException as e:
                self.stdout.write(self.style.ERROR(f'Could not retrieve {s}'))
                print(e)
                quit()

        for s in sample_objects:
            if options['assemblies']:
                assembly_src = s.sampleassemblydata.get_assembly_path()
                assembly_dst = outdir / f'{s}.fasta'
                assembly_dst.symlink_to(assembly_src)

            if options['reads']:
                fwd_reads_src = s.fwd_reads.path
                rev_reads_src = s.rev_reads.path
                fwd_reads_dst = outdir / f'{s}_R1.fastq.gz'
                rev_reads_dst = outdir / f'{s}_R2.fastq.gz'
                fwd_reads_dst.symlink_to(fwd_reads_src)
                rev_reads_dst.symlink_to(rev_reads_src)

        for s in minion_sample_objects:
            if options['reads']:
                reads = s.long_reads.path
                reads_dst = outdir / f'{s}.fastq.gz'
                reads_dst.symlink_to(reads)

        self.stdout.write(self.style.SUCCESS(f'DONE! Successfully wrote data to {outdir}'))
