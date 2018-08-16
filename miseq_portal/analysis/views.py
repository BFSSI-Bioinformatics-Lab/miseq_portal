from django.shortcuts import render
from django.http import JsonResponse

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View

from miseq_viewer.models import Sample, UserProjectRelationship
from analysis.models import SampleAnalysisTemporaryGroup


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

        # Delete all rows in SampleObjectTemp table belonging to requesting user
        SampleAnalysisTemporaryGroup.objects.filter(user=request.user).delete()

        # Add objects to SampleAnalysisTemporaryGroup table
        for sample_object in sample_object_list:
            obj = SampleAnalysisTemporaryGroup(sample_id=sample_object, user=request.user)
            obj.save()

        context = {'success': True,
                   'url': 'tool_selection/'}
        return JsonResponse(context)


analysis_index_view = AnalysisIndexView.as_view()


class ToolSelectionView(LoginRequiredMixin, View):
    template_name = 'analysis/tool_selection.html'

    def get(self, request):
        # Display samples only belonging only to the requesting user
        sample_group = SampleAnalysisTemporaryGroup.objects.filter(user_id=self.request.user)

        context = {
            'sample_group': sample_group
        }
        return render(request, self.template_name, context)


tool_selection_view = ToolSelectionView.as_view()
