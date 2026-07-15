import logging
import pandas as pd
from pathlib import Path
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from chunked_upload.views import ChunkedUploadView, ChunkedUploadCompleteView
from miseq_portal.minion_uploader.models import ZippedMinIONRunUpload
from subprocess import Popen, PIPE
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.core.files.storage import default_storage
import shutil
from miseq_portal.minion_viewer.models import MinIONSample, MinIONRun, MinIONRunSamplesheet
from miseq_portal.miseq_viewer.models import Project
from miseq_portal.users.models import User
from django.conf import settings
from django.http import HttpResponse

logger = logging.getLogger('django')


def extract_7z_archive(f: Path, outdir: Path):
    cmd = f'7z x {f} -o{outdir}'
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    out, err = p.communicate()


def get_run_id(f: Path):
    df = pd.read_excel(f, index_col=None)
    run_id = df['Run_ID'][0].strip()
    return run_id


def validate_minion_7zip(uploaded_file):
    """
    Look at the contents of the zip file with 7zip, then confirm our expected files are inside.
    Further validation is needed after this point, this is just a quick check.
    """
    cmd = f"7z l {default_storage.open(uploaded_file)} -ba"
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    expected_file_check = {
        'SampleSheet.xlsx': False,
        'qcat_demultiplexing': False  # Directory
    }

    out, err = p.communicate()
    lines = str(out).strip().split('\n')
    for line in lines:
        archived_file = line.rstrip().split(None, 5)[-1]    # .strip("/")
        if archived_file in expected_file_check.keys():
            expected_file_check[archived_file] = True
    if False in expected_file_check.values():
        logger.warning(f'ERROR in expected files:\n{expected_file_check}')
        return False
    return True


@method_decorator(staff_member_required, name='dispatch')
class UploadSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'minion_uploader/upload_success.html'


# Create your views here.
@method_decorator(staff_member_required, name='dispatch')
class MinIONUploaderIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'minion_uploader/minion_uploader_index.html'


@method_decorator(staff_member_required, name='dispatch')
class MinIONRunChunkedUploadView(ChunkedUploadView):
    model = ZippedMinIONRunUpload
    field_name = 'the_file'


@method_decorator(staff_member_required, name='dispatch')
class MinIONRunChunkedUploadCompleteView(ChunkedUploadCompleteView):
    model = ZippedMinIONRunUpload

    def on_completion(self, uploaded_file, request):
        # Do something with the uploaded file. E.g.:
        # * Store the uploaded file on another model:
        # SomeModel.objects.create(user=request.user, file=uploaded_file)
        # * Pass it as an argument to a function:
        # function_that_process_file(uploaded_file)

        logger.info(f"File size: {uploaded_file.size / 1000}kb")
        logger.info(f"File name: {uploaded_file.name}")

        file_name = default_storage.save(f'minion_runs/compressed_archives/{uploaded_file.name}', uploaded_file)
        contents_valid = validate_minion_7zip(uploaded_file=file_name)

        # This will return the full string path to the file
        complete_upload_path = default_storage.open(file_name)

        # This stores the path that should be saved to the DB (I think)
        media_path = default_storage.url(file_name)

        # If the contents are not valid, delete the file
        if not contents_valid:
            Path(str(complete_upload_path)).unlink()
            logger.info(f"Contents of file {complete_upload_path} are NOT VALID. Deleted!!!")
            return
        else:
            logger.info(f"Contents of file are valid! Saved to {complete_upload_path}")
            logger.info(f'Media URL: {media_path}')

        # Actual processing; unzipping, loading into database

        archive_name = Path(str(complete_upload_path)).with_suffix("").name
        outdir_tmp = Path(settings.MEDIA_ROOT) / 'minion_runs' / 'temp' / archive_name

        # Unzip to
        extract_7z_archive(f=Path(str(complete_upload_path)), outdir=outdir_tmp)
        sample_sheet = outdir_tmp / 'SampleSheet.xlsx'
        assert sample_sheet.exists()
        logger.info(f'Saved samplesheet to {str(complete_upload_path)}')

        # Get the actual Run ID from the samplesheet
        run_id = get_run_id(sample_sheet)

        # Copy the extracted files to the new, proper destination
        outdir = Path(settings.MEDIA_ROOT) / 'uploads' / 'minion_runs' / run_id
        if outdir.exists():
            logger.info(f'{outdir} already exists, deleting previous!')
            shutil.rmtree(outdir)
        shutil.copytree(src=outdir_tmp, dst=outdir)
        sample_sheet = outdir / 'SampleSheet.xlsx'

        # Delete the old tmp directory
        shutil.rmtree(outdir_tmp)

        # Create run with run_id value
        run_object, created = MinIONRun.objects.get_or_create(run_id=run_id)
        logger.info(f'Created run {run_object}')
        run_object.save()

        # Create samplesheet object
        samplesheet_object, created = MinIONRunSamplesheet.objects.get_or_create(
            sample_sheet=str(sample_sheet).replace(f"{settings.MEDIA_ROOT}/", ""),
            run_id=run_object)
        samplesheet_object.save()

        # Create samples from samplesheet
        df = pd.read_excel(sample_sheet, index_col=None)
        if len(df) < 1:
            logger.error(f'Empty samplesheet for {sample_sheet}! Quitting!')
            samplesheet_object.delete()
            run_object.delete()
            return

        for i, row in df.iterrows():
            long_reads = outdir / 'qcat_demultiplexing' / f'{row["Barcode"]}.fastq.gz'
            assert long_reads.exists()

            project_object, created = Project.objects.get_or_create(project_id=row['Project_ID'], defaults={
                # Default to admin ownership
                'project_owner': User.objects.get(
                    username="admin")
            })
            if created:
                # Create admin relationship to project immediately
            #    UserProjectRelationship.objects.create(project_id=project_object,
            #                                           user_id=User.objects.get(username="admin"))
                logger.info(f'Created new Project "{project_object.project_id}"')

            project_object.save() # I think this will make last_updated work better

            sample = MinIONSample.objects.create(
                sample_id=row['Sample_ID'],
                sample_name=row['Sample_Name'],
                long_reads=str(long_reads).replace(f"{settings.MEDIA_ROOT}/", ""),
                run_id=run_object,
                run_protocol=row['Run_Protocol'],
                instrument_id=row['Instrument_ID'],
                sequencing_kit=row['Sequencing_Kit'],
                flowcell_type=row['Flowcell_Type'],
                project_id=project_object,
                read_type=row['Read_Type'],
                user=row['User']
            )
            sample.save()
            logger.info(f'Created {sample.sample_id}!')

    def get_response_data(self, chunked_upload, request):
        return f"You successfully uploaded '{chunked_upload.filename}' ({chunked_upload.offset / 1000} kb)! "
