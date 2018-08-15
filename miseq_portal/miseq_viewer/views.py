from pathlib import Path
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import DetailView, ListView

from config.settings.base import MEDIA_ROOT

from miseq_viewer.models import Project, Run, Sample, UserProjectRelationship
from miseq_uploader import parse_samplesheet


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    context_object_name = 'project_list'
    paginate_by = 50
    template_name = "miseq_viewer/project_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        context['user'] = self.request.user
        context['approved_users'] = UserProjectRelationship.objects.filter(user_id=self.request.user)
        print(context['approved_users'])
        return context


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
        context['project_list'] = Project.objects.all()
        context['sample_list'] = Sample.objects.all()
        context['samplesheet_df'] = parse_samplesheet.read_samplesheet_to_html(
            Path(MEDIA_ROOT) / str(context['run'].sample_sheet))
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
