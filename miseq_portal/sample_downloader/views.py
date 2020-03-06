from django.shortcuts import render
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
from miseq_portal.sample_downloader.forms import DownloadToolForm

logger = logging.getLogger('django')


class DownloaderSampleSelectView(LoginRequiredMixin, TemplateView):
    template_name = "sample_downloader/downloader_sample_select.html"
    success_url = 'sample_downloader/confirm/'

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


downloader_sample_select_view = DownloaderSampleSelectView.as_view()


class FileTypeSelectionView(LoginRequiredMixin, View):
    template_name = 'sample_downloader/downloader_sample_confirm.html'
    model = AnalysisGroup
    form_class = DownloadToolForm
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


downloader_sample_confirm_view = FileTypeSelectionView.as_view()
