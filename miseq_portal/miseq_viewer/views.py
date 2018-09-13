import os
import json
from pathlib import Path
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import DetailView, ListView, View
from django.http import HttpResponse, Http404

from config.settings.base import MEDIA_ROOT

from miseq_portal.miseq_viewer.models import Project, Run, Sample, UserProjectRelationship
from miseq_portal.miseq_uploader import parse_samplesheet
from miseq_portal.miseq_uploader.parse_interop import get_qscore_json

import logging
logger = logging.getLogger('raven')


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    context_object_name = 'project_list'
    template_name = "miseq_viewer/project_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        context['user'] = self.request.user
        context['approved_users'] = UserProjectRelationship.objects.filter(user_id=self.request.user)
        context['overview_json'] = self.get_overview_data()
        return context

    @staticmethod
    def get_overview_data():
        overview_dict = dict()
        overview_dict['number_of_projects'] = len(Project.objects.all().values())
        overview_dict['number_of_samples'] = len(Sample.objects.all().values())
        overview_dict['number_of_runs'] = len(Run.objects.all().values())
        return json.dumps(overview_dict)


project_list_view = ProjectListView.as_view()


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    context_object_name = 'project'
    template_name = "miseq_viewer/project_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['run_list'] = Run.objects.all()
        context['sample_list'] = Sample.objects.filter(project_id=context['project'])
        return context


project_detail_view = ProjectDetailView.as_view()


class RunDetailView(LoginRequiredMixin, DetailView):
    model = Run
    context_object_name = 'run'
    template_name = "miseq_viewer/run_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get run folder to feed to the interop parser
        interop_folder = context['run'].interop_directory_path
        logger.info(f'InterOp folder: {interop_folder}')

        if context['run'].interop_directory_path is not None:
            interop_folder = Path(interop_folder)
        else:
            logger.info("WARNING: The InterOp directory for this run is not stored in the database")
            context['interop_data_avaiable'] = False

        # Grab Samplesheet path
        samplesheet = Path(MEDIA_ROOT) / str(context['run'].sample_sheet)

        # Try to receive InterOp data, if it's not available then display an alert on miseq_viewer/run_detail.html
        try:
            context['qscore_json'] = get_qscore_json(Path(MEDIA_ROOT) / interop_folder.parent)
            context['interop_data_avaiable'] = True
        except Exception as e:
            logger.info(f"Could not parse InterOp files for {context['run']}")
            logging.error(f'TRACEBACK: {e}')
            context['interop_data_avaiable'] = False

        logger.info(f"interop_data_available: {context['interop_data_avaiable']}")
        context['project_list'] = Project.objects.all()
        context['sample_list'] = Sample.objects.all()
        context['samplesheet_df'] = parse_samplesheet.read_samplesheet_to_html(sample_sheet=samplesheet)
        return context


run_detail_view = RunDetailView.as_view()


class SampleDetailView(LoginRequiredMixin, DetailView):
    model = Sample
    context_object_name = 'sample'
    template_name = "miseq_viewer/sample_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


sample_detail_view = SampleDetailView.as_view()

#
# class DownloadReadView(LoginRequiredMixin, View):
#     model = Sample
#     context_object_name = 'sample'
#     template_name = "miseq_viewer/sample_download.html"
#
#     def get(self, request):
#         response = HttpResponse(content_type="image/jpeg")
#         file_path = os.path.join(MEDIA_ROOT, ['sample'])
#         response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#
#     def download(self, request, path):
#         file_path = os.path.join(MEDIA_ROOT, path)
#         if os.path.exists(file_path):
#             with open(file_path, 'rb') as fh:
#                 response = HttpResponse(fh.read(), content_type="application/gzip")
#                 response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
#                 return response
#         raise Http404
#
#
# read_download_view = DownloadReadView.as_view()
