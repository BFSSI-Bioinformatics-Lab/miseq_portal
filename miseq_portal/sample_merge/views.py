from django.http import JsonResponse

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from miseq_portal.miseq_viewer.models import Sample, UserProjectRelationship, MergedSampleComponentGroup, MergedSampleComponent

import logging

logger = logging.getLogger('raven')


class SampleMergeIndexView(LoginRequiredMixin, ListView):
    template_name = 'sample_merge/sample_merge_index.html'
    success_url = 'merge_confirmation/'
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
        merge_group = MergedSampleComponentGroup(user=request.user)
        merge_group.save()

        # Add objects to SampleAnalysisTemporaryGroup table
        for sample_object in sample_object_list:
            obj = MergedSampleComponent(component_id=sample_object, user=request.user, group_id=merge_group)
            obj.save()
        logger.info(f'Saved {sample_object_list} to {merge_group} for user "{request.user}"')

        context = {'success': True,
                   'url': self.success_url}
        return JsonResponse(context)


sample_merge_index_view = SampleMergeIndexView.as_view()
