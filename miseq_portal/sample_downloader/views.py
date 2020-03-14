import csv
import os
import io
import shutil

from django.shortcuts import render
import logging
import tempfile

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import View, TemplateView, DetailView, DeleteView
from django.http import FileResponse
from wsgiref.util import FileWrapper

from miseq_portal.analysis.forms import AnalysisToolForm
from miseq_portal.analysis.models import AnalysisSample, AnalysisGroup, SendsketchResult, MobSuiteAnalysisPlasmid, \
    MobSuiteAnalysisGroup, RGIResult, RGIGroupResult, ConfindrGroupResult, ConfindrResult
from miseq_portal.analysis.tasks import submit_analysis_job
from miseq_portal.miseq_viewer.models import Sample, UserProjectRelationship, SampleAssemblyData
from miseq_portal.sample_downloader.forms import DownloadToolForm

logger = logging.getLogger('django')


class DownloaderSampleSelectView(LoginRequiredMixin, TemplateView):
    template_name = "sample_downloader/downloader_sample_select.html"
    success_url = 'confirm/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['approved_users'] = UserProjectRelationship.objects.filter(user_id=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        # Grab sample list from user selection from downloader_sample_select.html page via AJAX
        sample_id_list = request.POST.getlist('sample_id_list[]')

        logger.info(f"Handling POST request for DownloaderSampleSelectView")
        logger.info(f"Samples selected: {sample_id_list}")

        # returns success_url and the sample_id_list to be saved on cookie is a Json
        context = {'success': True,
                   'url': self.success_url,
                   'sample_id_list': sample_id_list}
        return JsonResponse(context)


downloader_sample_select_view = DownloaderSampleSelectView.as_view()


class FileTypeSelectionView(LoginRequiredMixin, View):
    template_name = 'sample_downloader/downloader_sample_confirm.html'
    # model = AnalysisGroup
    form_class = DownloadToolForm
    success_url = 'receive/'

    def get(self, request, *args, **kwargs):
        logger.info(f"Loaded GET for FileTypeSelectionView")
        logger.info(request)
        logger.info(dir(request))
        logger.info(request.COOKIES)

        context = {
            'form': self.form_class
        }

        return render(request, self.template_name, context)

    # Post request, posts file choice form, redirects to success_url
    def post(self, request):
        form = self.form_class(request.POST)

        context = {'success': True,
                   'url': self.success_url}

        if form.is_valid():
            logger.info("Valid form")
            return redirect(self.success_url)
        else:
            logger.error("Form is not valid")
            # return render(request, self.template_name, {'form': form})
            return redirect(self.success_url)

    # def form_valid(self, form):
    #    form.pick_file_type()
    #    context = {'success': True,
    #               'url': self.success_url}
    #    return super().form_valid(form)


downloader_sample_confirm_view = FileTypeSelectionView.as_view()


class ReceiveFileView(LoginRequiredMixin, View):
    template_name = 'sample_downloader/downloader_sample_receive.html'
    # model = AnalysisGroup
    form_class = DownloadToolForm

    # Ajax in downloader_sample_confirm calls this get
    # returns FileResponse and prompts browser download box
    def get(self, request):
        print("PENGUINS!!!")

        gzip_example = '/home/kelsey/gzip_example.gz'
        outputFileName = 'testName.zip'

        # Get sample IDs from cookies
        sample_list = request.COOKIES['sample_id_list'].split(',')

        # Get corresponding Sample objects from database
        sample_object_list = []
        for s in sample_list:
            sample_object_list.append(SampleAssemblyData.objects.get(sample_id__sample_id=s))

        sample_assembly_paths = []
        for s in sample_object_list:
            sample_assembly_paths.append(s.get_assembly_path())

        # 1. Create a temp directory somewhere (e.g. /tmp/miseq_portal_download

        # 2. Copy all files to the temp directory (use shutil copy method to copy files)

        # 3. Figure out how to run a subprocess --> run pigz to create a single gzipped archive (save it to temp dir)
        # import subprocess   -->  Popen

        # 4. Serve the gzipped archive to user

        # 5. Delete tmp directory?

        filename = os.path.basename(gzip_example)
        response = FileResponse('/home/kelsey/gzip_example.gz', content_type='application/x-zip-compressed')
        response['Content-Disposition'] = "attachment; filename=%s" % outputFileName

        print(response)
        return response

    # return render(request, self.template_name)

    # POST requested by submit-button click in download_sample_receive.html forces file download
    # if ajax type is GET and not POST in downloader_sample_confirm.html
    # it just skips this all together and still works :)
    # if it is called, needs to return an HttpResponse
    def post(self, request, **kwargs):
        print("Post!!!")
        print(request)

        response = HttpResponse(content_type='text/plain')
        print(response)
        return response


downloader_sample_receive_view = ReceiveFileView.as_view()

# with tempfile.NamedTemporaryFile() as f:
#     f.write(b'hello')
#     f.flush()
#     print(f.name)
#     response = FileResponse(f.name)
#     response['Content-Disposition'] = 'attachment; filename=DownloadedText.pdf'
#     response['Content-Type'] = 'application/download'
#     print(response)
#     return response
