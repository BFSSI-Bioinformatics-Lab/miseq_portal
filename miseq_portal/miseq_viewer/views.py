import json
import logging
from pathlib import Path

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import DetailView, ListView
from rest_framework import viewsets

from config.settings.base import MEDIA_ROOT
from miseq_portal.analysis.models import AnalysisSample
from miseq_portal.miseq_uploader import parse_samplesheet
from miseq_portal.miseq_uploader.parse_interop import get_qscore_json
from miseq_portal.miseq_viewer.models import Project, Run, Sample, UserProjectRelationship, SampleAssemblyData, \
    MergedSampleComponent, SampleLogData, RunSamplesheet
from miseq_portal.miseq_viewer.serializers import SampleSerializer, RunSerializer, ProjectSerializer

logger = logging.getLogger('django')


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    context_object_name = 'project_list'
    template_name = "miseq_viewer/project_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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

    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = Project.objects.all().order_by('project_id')
        else:
            valid_projects = UserProjectRelationship.objects.filter(user_id=self.request.user)
            valid_projects = [p.project_id for p in valid_projects]
            queryset = Project.objects.filter(Q(project_id__in=valid_projects)).order_by('project_id')
        return queryset


project_list_view = ProjectListView.as_view()


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    context_object_name = 'project'
    template_name = "miseq_viewer/project_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['run_list'] = Run.objects.all()
        context['sample_list'] = Sample.objects.filter(project_id=context['project'], hide_flag=False)
        # Filter out samples that are missing data for the project_detail.html template
        context['has_sample_log_data'] = context['sample_list'].filter(samplelogdata__isnull=False)
        context['has_mash_result'] = context['sample_list'].filter(mashresult__isnull=False)
        return context


project_detail_view = ProjectDetailView.as_view()


class RunListView(LoginRequiredMixin, ListView):
    model = Run
    context_object_name = 'run_list'
    template_name = "miseq_viewer/run_list.html"


run_list_view = RunListView.as_view()


class RunDetailView(LoginRequiredMixin, DetailView):
    model = Run
    context_object_name = 'run'
    template_name = "miseq_viewer/run_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['interop_data_avaiable'] = True

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
        except Exception as e:
            # logging.debug(f'TRACEBACK: {e}')
            context['interop_data_avaiable'] = False

        # logger.debug(f"interop_data_available: {context['interop_data_avaiable']}")
        context['sample_list'] = Sample.objects.filter(run_id=context['run'], hide_flag=False)
        context['samplesheet_headers'] = RunSamplesheet.objects.get(run_id=context['run'])
        context['samplesheet_df'] = parse_samplesheet.read_samplesheet_to_html(sample_sheet=samplesheet)

        return context


run_detail_view = RunDetailView.as_view()


class SampleDetailView(LoginRequiredMixin, DetailView):
    model = Sample
    context_object_name = 'sample'
    template_name = "miseq_viewer/sample_detail.html"

    def get_queryset(self):
        """ This ensures hidden samples do not appear """
        qs = super(SampleDetailView, self).get_queryset()
        return qs.filter(hide_flag=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sample_object = context['sample']

        # Query the AnalysisSample model to see if there are any analyses associated with this sample for this user
        analysis_samples = AnalysisSample.objects.filter(sample_id=context['sample'], user_id=self.request.user)

        # Get assembly data if it exists
        try:
            context['assembly_data'] = SampleAssemblyData.objects.get(sample_id=context['sample'])
        except SampleAssemblyData.DoesNotExist:
            context['assembly_data'] = None

        # Get Mash hit if it exists
        try:
            context['top_refseq_hit'] = sample_object.mashresult.top_hit
        except:
            # Get top Sendsketch hit if it exists
            try:
                context['top_refseq_hit'] = SampleAssemblyData.objects.get(
                    sample_id=context['sample']).sample_id.sendsketchresult.top_taxName
            except:
                context['top_refseq_hit'] = None

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
            merged_number_reads = 0
            merged_sample_yield = 0
            components = MergedSampleComponent.objects.filter(group_id=context['sample'].component_group)
            sample_components = []

            # Get corresponding Sample objects
            merged_sample_yield_broken_flag = False
            merged_number_reads_broken_flag = False
            for component in components:
                sample_component = Sample.objects.get(sample_id=component.component_id)
                sample_components.append(sample_component)

                # If one of the components is missing data, display N/A for merged value on page
                if sample_component.samplelogdata.number_reads is None:
                    merged_number_reads_broken_flag = True
                if sample_component.samplelogdata.sample_yield is None:
                    merged_sample_yield_broken_flag = True

                if merged_sample_yield_broken_flag or merged_number_reads_broken_flag:
                    continue
                else:
                    # Sum up total number of reads across each sample_component if none of them have N/A values
                    merged_number_reads += sample_component.samplelogdata.number_reads
                    merged_sample_yield += sample_component.samplelogdata.sample_yield / 1000000

            context['sample_components'] = sample_components

            # TODO: Refactor this logic into a property for a Sample object in models.py?
            # The summed values for each component for number_reads and sample_yield, respectively
            if merged_number_reads_broken_flag:
                context['merged_number_reads'] = "N/A"
            else:
                context['merged_number_reads'] = merged_number_reads
            if merged_sample_yield_broken_flag:
                context['merged_sample_yield'] = "N/A"
            else:
                context['merged_sample_yield'] = merged_sample_yield

        # Check if sample is part of a MER sample
        merged_sample_references = []
        if context['sample'].sample_type == 'BMH':
            component_query = MergedSampleComponent.objects.filter(component_id=context['sample'])
            if len(component_query) > 0:
                for component in component_query:
                    try:
                        merged_sample_reference = Sample.objects.get(component_group=component.group_id)
                        merged_sample_references.append(merged_sample_reference)
                    except Sample.DoesNotExist:
                        pass
        context['merged_sample_references'] = merged_sample_references

        # Check if sample has a related samplelogdata object
        try:
            SampleLogData.objects.get(sample_id=context['sample'])
            context['has_sample_log_data'] = True
        except SampleLogData.DoesNotExist:
            context['has_sample_log_data'] = False

        # Get user's browser details to determine whether or not to show the disclaimer RE: downloading .fastq.gz
        if "firefox" in self.request.META['HTTP_USER_AGENT'].lower():
            context['browser_flag'] = True
        else:
            context['browser_flag'] = False

        return context


sample_detail_view = SampleDetailView.as_view()


# django-rest-framework
class SampleViewSet(viewsets.ModelViewSet):
    serializer_class = SampleSerializer

    def get_queryset(self):
        # Staff get the full queryset, otherwise only show samples that are in projects user has rights to
        if self.request.user.is_staff:
            queryset = Sample.objects.all().order_by('sample_id')
        else:
            valid_projects = UserProjectRelationship.objects.filter(user_id=self.request.user)
            valid_projects = [p.project_id for p in valid_projects]
            queryset = Sample.objects.filter(Q(hide_flag=False) &
                                             Q(project_id__in=valid_projects)
                                             ).order_by('sample_id')
        return queryset


class RunViewSet(viewsets.ModelViewSet):
    queryset = Run.objects.all().order_by('run_id')
    serializer_class = RunSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = Project.objects.all().order_by('project_id')
        else:
            valid_projects = UserProjectRelationship.objects.filter(user_id=self.request.user)
            valid_projects = [p.project_id for p in valid_projects]
            queryset = Project.objects.filter(Q(project_id__in=valid_projects)).order_by('project_id')
        return queryset
