import json
import logging
from pathlib import Path

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import DetailView, ListView
from rest_framework import viewsets, mixins

from config.settings.base import MEDIA_ROOT
from miseq_portal.analysis.models import AnalysisSample
from miseq_portal.miseq_uploader import parse_samplesheet
from miseq_portal.miseq_uploader.parse_interop import get_qscore_json
from miseq_portal.miseq_viewer.models import Project, Run, Sample, UserProjectRelationship, SampleAssemblyData, \
    MergedSampleComponent
from miseq_portal.miseq_viewer.serializers import SampleSerializer

logger = logging.getLogger(__name__)


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
        context['sample_count_dict'] = {project.project_id: len(Sample.objects.filter(project_id_id=project)) for
                                        project in Project.objects.all()}
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
            logging.debug(f'TRACEBACK: {e}')
            context['interop_data_avaiable'] = False

        logger.debug(f"interop_data_available: {context['interop_data_avaiable']}")
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

        # Query the AnalysisSample model to see if there are any analyses associated with this sample for this user
        analysis_samples = AnalysisSample.objects.filter(sample_id=context['sample'], user_id=self.request.user)

        # Get assembly data if it exists
        try:
            context['assembly_data'] = SampleAssemblyData.objects.get(sample_id=context['sample'])
        except SampleAssemblyData.DoesNotExist:
            context['assembly_data'] = None

        # Get top Sendsketch hit if it exists
        try:
            context['sendsketch'] = SampleAssemblyData.objects.get(
                sample_id=context['sample']).sample_id.sendsketchresult
        except:
            context['sendsketch'] = None

        # Set to None if the FileField for the assembly is empty
        try:
            if str(context['assembly_data'].assembly) == '':
                context['assembly_data'] = None
        except AttributeError:
            context['assembly_data'] = None

        if len(analysis_samples) > 0:
            context['analysis_samples'] = analysis_samples
        else:
            context['analysis_samples'] = None

        # Get associated samples if sample type is MER
        if context['sample'].sample_type == 'MER':
            components = MergedSampleComponent.objects.filter(group_id=context['sample'].component_group)
            sample_components = []
            # Get corresponding Sample objects
            for component in components:
                sample_component = Sample.objects.get(sample_id=component.component_id)
                sample_components.append(sample_component)
            context['sample_components'] = sample_components

        # Check if sample is part of a MER sample
        if context['sample'].sample_type == 'BMH':
            component_query = MergedSampleComponent.objects.filter(component_id=context['sample'])
            if len(component_query) > 0:
                merged_sample_references = []
                for component in component_query:
                    try:
                        merged_sample_reference = Sample.objects.get(component_group=component.group_id)
                        merged_sample_references.append(merged_sample_reference)
                    except Sample.DoesNotExist:
                        pass
                context['merged_sample_references'] = merged_sample_references

        # Get user's browser details to determine whether or not to show the disclaimer RE: downloading .fastq.gz
        if "firefox" in self.request.META['HTTP_USER_AGENT'].lower():
            context['browser_flag'] = True
        else:
            context['browser_flag'] = False

        return context


sample_detail_view = SampleDetailView.as_view()


class SampleViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Sample.objects.all()
    serializer_class = SampleSerializer


samples_api_view = SampleViewSet.as_view({'get': 'list'})
