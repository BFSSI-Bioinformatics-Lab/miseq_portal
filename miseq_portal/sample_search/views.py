import json
import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.core import serializers
from django.shortcuts import HttpResponse
from django.db.models import Q
from django.http import JsonResponse

from miseq_portal.miseq_viewer.models import Sample, UserProjectRelationship


class SampleSearchViewAsJSON(LoginRequiredMixin, View):
    def get(self, request):
        queryset = Sample.objects.all()
        updated_object_list = []
        for obj in queryset:
            # Try to get project ID
            try:
                project = obj.project_id.project_id
            except AttributeError:
                project = ''

            # Try to get run ID
            try:
                run = obj.run_id.run_id
            except AttributeError:
                run = ''

            # Create new dict
            updated_object_list.append({
                'project_id': project,
                'run_id': run
            })

        # Dump to JSON
        # object_list_json = json.dumps(updated_object_list)

        # serialized_json = serializers.serialize('json', object_list_json)
        # return HttpResponse(serialized_json, content_type='application/json')
        response = JsonResponse(updated_object_list, safe=False)
        return response


sample_search_view_json = SampleSearchViewAsJSON.as_view()


class SampleSearchView(LoginRequiredMixin, ListView):
    """
    """
    model = Sample
    # paginate_by = 20
    template_name = 'sample_search/sample_search.html'
    context_object_name = 'sample_list'

    def get_queryset(self):
        search_term = self.request.GET.get('search_term')
        sample_list = self.model.objects.filter(
            Q(sample_id__icontains=search_term) |
            Q(project_id__project_id__icontains=search_term) |
            Q(sample_name__icontains=search_term) |
            Q(run_id__run_id__icontains=search_term)
        )
        return sample_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['approved_users'] = UserProjectRelationship.objects.filter(user_id=self.request.user).order_by('id')
        return context


sample_search_view = SampleSearchView.as_view()
