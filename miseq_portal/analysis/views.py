import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import View, TemplateView, DetailView, DeleteView

from miseq_portal.analysis.forms import AnalysisToolForm
from miseq_portal.analysis.models import AnalysisSample, AnalysisGroup, SendsketchResult, MobSuiteAnalysisPlasmid, \
    MobSuiteAnalysisGroup, RGIResult, RGIGroupResult, ConfindrGroupResult, ConfindrResult
from miseq_portal.analysis.tasks import submit_analysis_job
from miseq_portal.miseq_viewer.models import Sample, UserProjectRelationship

logger = logging.getLogger('django')


class SampleSelectView(LoginRequiredMixin, TemplateView):
    template_name = "analysis/sample_select.html"
    success_url = 'tools/'

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


sample_select_view = SampleSelectView.as_view()


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
            logger.info(f"Queued job for {analysis_group}")

            # Submit analysis to queue. Note that the ID must be submitted because a straight object is not serializable
            submit_analysis_job.apply_async(args=[],
                                            kwargs={'analysis_group': analysis_group.id},
                                            queue='analysis_queue')

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

        # Sendketch
        if context['analysis_group'].job_type == 'SendSketch':
            context['sendsketch_results'] = SendsketchResult.objects.filter(
                sample_id__analysissample__group_id=context['analysis_group']).order_by('-sample_id')
        # Mob Suite
        elif context['analysis_group'].job_type == 'MobRecon':
            context['mob_suite_analysis_samples'] = MobSuiteAnalysisGroup.objects.filter(
                analysis_sample__group_id=context['analysis_group']).order_by('-analysis_sample__sample_id')
            context['mob_suite_analysis_plasmids'] = MobSuiteAnalysisPlasmid.objects.filter(
                sample_id__analysissample__group_id=context['analysis_group']).order_by('-analysis_sample__sample_id')
        # RGI
        elif context['analysis_group'].job_type == 'RGI':
            context['rgi_results'] = RGIResult.objects.filter(
                analysis_sample__group_id=context['analysis_group']).order_by('-analysis_sample__sample_id')
            context['rgi_group_result'] = RGIGroupResult.objects.get(analysis_group=context['analysis_group'])
        # Confindr
        elif context['analysis_group'].job_type == 'Confindr':
            context['confindr_group_result'] = ConfindrGroupResult.objects.get(analysis_group=context['analysis_group'])
            context['confindr_results'] = ConfindrResult.objects.filter(
                analysis_sample__group_id=context['analysis_group']).order_by('-analysis_sample__sample_id')
        else:
            return context
        return context


analysis_group_detail_view = AnalysisGroupDetailView.as_view()


class JobSubmittedView(LoginRequiredMixin, TemplateView):
    template_name = 'analysis/job_submitted.html'


job_submitted_view = JobSubmittedView.as_view()


class AnalysisGroupDeleteView(LoginRequiredMixin, DeleteView):
    model = AnalysisGroup
    success_url = reverse_lazy('analysis:analysis_group_delete_success_view')


analysis_group_delete_view = AnalysisGroupDeleteView.as_view()


class AnalysisGroupDeleteSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'analysis/analysisgroup_delete_success.html'


analysis_group_delete_success_view = AnalysisGroupDeleteSuccessView.as_view()
