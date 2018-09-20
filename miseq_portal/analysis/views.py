from django.shortcuts import render, redirect
from django.http import JsonResponse

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View, TemplateView, DetailView

from miseq_portal.miseq_viewer.models import Sample, UserProjectRelationship
from miseq_portal.analysis.models import AnalysisSample, AnalysisGroup, SendsketchResult, MobSuiteAnalysisPlasmid, \
    MobSuiteAnalysisGroup
from miseq_portal.analysis.forms import AnalysisToolForm
from miseq_portal.analysis.tasks import submit_analysis_job

import logging

logger = logging.getLogger('raven')


class AnalysisIndexView(LoginRequiredMixin, ListView):
    template_name = 'analysis/analysis_index.html'
    success_url = 'tool_selection/'
    model = Sample
    context_object_name = 'sample_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['approved_users'] = UserProjectRelationship.objects.filter(user_id=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        # Grab sample list from user selection from the analysis_index.html page via AJAX
        sample_id_list = request.POST.getlist('sample_id_list[]')

        # Get corresponding Sample objects from user selection
        sample_object_list = list()
        for sample_id in sample_id_list:
            sample_object = Sample.objects.get(sample_id=sample_id)
            sample_object_list.append(sample_object)

        # Create new AnalysisGroup
        analysis_group = AnalysisGroup(user=request.user)
        analysis_group.save()

        # Add objects to SampleAnalysisTemporaryGroup table
        for sample_object in sample_object_list:
            obj = AnalysisSample(sample_id=sample_object, user=request.user, group_id=analysis_group)
            obj.save()
        logger.info(f'Saved {sample_object_list} to {analysis_group} for user "{request.user}"')

        context = {'success': True,
                   'url': self.success_url}
        return JsonResponse(context)


analysis_index_view = AnalysisIndexView.as_view()


class ToolSelectionView(LoginRequiredMixin, View):
    template_name = 'analysis/tool_selection.html'
    model = AnalysisGroup
    form_class = AnalysisToolForm
    success_url = 'job_submitted/'

    def get(self, request, *args, **kwargs):
        # Get the most recent Analysis Group belonging to user
        analysis_group = AnalysisGroup.objects.filter(user_id=self.request.user).order_by('-id')[0]
        analysis_samples = AnalysisSample.objects.filter(group_id=analysis_group)

        context = {
            'analysis_group': analysis_group,
            'analysis_samples': analysis_samples,
            'form': self.form_class
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            logger.info("Valid form")

            # Set job type for analysis_group
            analysis_group = AnalysisGroup.objects.filter(user_id=self.request.user).order_by('-id')[0]
            analysis_group.job_type = form.cleaned_data['job_type']
            analysis_group.save()
            logger.info(f"Set job_type for {analysis_group} to {form.cleaned_data['job_type']}")

            # Submit analysis to queue. Note that the ID must be submitted because a straight object is not serializable
            submit_analysis_job.delay(analysis_group_id=analysis_group.id)

            return redirect(self.success_url)
        else:
            logger.error("Form is not valid")
            return render(request, self.template_name, {'form': form})


tool_selection_view = ToolSelectionView.as_view()


class MyJobsView(LoginRequiredMixin, View):
    template_name = 'analysis/my_jobs.html'

    def get(self, request):
        # Display samples only belonging only to the requesting user
        analysis_group = AnalysisGroup.objects.filter(user_id=self.request.user)
        context = {
            'analysis_group': analysis_group
        }
        return render(request, self.template_name, context)


my_jobs_view = MyJobsView.as_view()


class AnalysisGroupDetailView(LoginRequiredMixin, DetailView):
    model = AnalysisGroup
    context_object_name = 'analysis_group'
    template_name = "analysis/analysis_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['analysis_samples'] = AnalysisSample.objects.filter(group_id=context['analysis_group'])
        context['sendsketch_results'] = SendsketchResult.objects.filter(
            sample_id__analysissample__group_id=context['analysis_group'])
        mob_suite_group = MobSuiteAnalysisGroup.objects.get(analysis_group=context['analysis_group'])
        context['mob_recon_results'] = MobSuiteAnalysisPlasmid.objects.filter(group_id=mob_suite_group)
        return context


analysis_group_detail_view = AnalysisGroupDetailView.as_view()


class JobSubmittedView(LoginRequiredMixin, TemplateView):
    template_name = 'analysis/job_submitted.html'


job_submitted_view = JobSubmittedView.as_view()
