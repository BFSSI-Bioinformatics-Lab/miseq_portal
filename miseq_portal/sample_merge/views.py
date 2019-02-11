import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import ListView, TemplateView, DeleteView

from miseq_portal.miseq_viewer.models import Sample, UserProjectRelationship, MergedSampleComponentGroup, \
    MergedSampleComponent
from miseq_portal.sample_merge.tasks import merge_reads

logger = logging.getLogger(__name__)


@method_decorator(staff_member_required, name='dispatch')
class SampleMergeIndexView(LoginRequiredMixin, ListView):
    template_name = 'sample_merge/sample_merge_index.html'
    success_url = 'merge_success/'
    model = Sample
    context_object_name = 'sample_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['approved_users'] = UserProjectRelationship.objects.filter(user_id=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        # Grab sample list from user selection from the sample_merge_index.html page via AJAX
        sample_id_list = request.POST.getlist('sample_id_list[]')

        # Get corresponding Sample objects from user selection
        sample_object_list = list()
        for sample_id in sample_id_list:
            sample_object = Sample.objects.get(sample_id=sample_id)
            sample_object_list.append(sample_object)

        # Create new MergedSampleComponentGroup
        component_group = MergedSampleComponentGroup(user=request.user)
        component_group.save()

        # Add objects to MergedSampleComponentGroup table
        for sample_object in sample_object_list:
            obj = MergedSampleComponent(component_id=sample_object, group_id=component_group)
            obj.save()
        logger.info(f'Saved {sample_object_list} to {component_group} for user "{request.user}"')

        # Create new merged sample
        merged_sample = Sample.objects.create(component_group=component_group, sample_type='MER')
        merged_sample.sample_id = merged_sample.generate_sample_id()
        merged_sample.save()

        # Queue up job for concatenation with sample_object_list
        sample_object_id_list = [sample_object.id for sample_object in sample_object_list]
        merge_reads.apply_async(args=[],
                                kwargs={'sample_object_id_list': sample_object_id_list,
                                        'merged_sample_id': merged_sample.id},
                                queue='assembly_queue')

        self.success_url += f"?group_id={component_group.id}&merged_sample_id={merged_sample.id}"

        context = {'success': True,
                   'url': self.success_url}
        return JsonResponse(context)


sample_merge_index_view = SampleMergeIndexView.as_view()


@method_decorator(staff_member_required, name='dispatch')
class MergeSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'sample_merge/merge_success.html'

    def get_context_data(self, **kwargs):
        group_id = self.request.GET.get('group_id')
        merged_sample_id = self.request.GET.get('merged_sample_id')
        group = MergedSampleComponentGroup.objects.get(pk=group_id)
        group_samples = MergedSampleComponent.objects.filter(group_id=group)
        merged_sample = Sample.objects.get(pk=merged_sample_id)

        context = {
            'group_id': self.request.GET.get('group_id'),
            'group_samples': group_samples,
            'merged_sample': merged_sample
        }
        return context


merge_success_view = MergeSuccessView.as_view()


class SampleDeleteView(LoginRequiredMixin, DeleteView):
    model = Sample
    template_name = 'sample_merge/sample_confirm_delete.html'
    success_url = reverse_lazy('sample_merge:sample_delete_success_view')


sample_delete_view = SampleDeleteView.as_view()


class SampleDeleteSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'sample_merge/sample_delete_success.html'


sample_delete_success_view = SampleDeleteSuccessView.as_view()
