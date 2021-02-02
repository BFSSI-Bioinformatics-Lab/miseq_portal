from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.views.generic import ListView, View

from miseq_portal.miseq_viewer.models import Sample, UserProjectRelationship
from miseq_portal.minion_viewer.models import MinIONSample


class SampleSearchViewAsJSON(LoginRequiredMixin, View):
    def get(self, request):
        queryset = Sample.objects.filter(hide_flag=False)
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


# TODO: Refactor to utilize the API + django-rest-framework-datatables
class SampleSearchView(LoginRequiredMixin, ListView):
    model = Sample
    template_name = 'sample_search/sample_search.html'
    context_object_name = 'sample_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_term = self.request.GET.get('search_term')

        # Queries various fields from Sample as well as the top_hit from MashResult
        # prefetch_related joins Sample and MashResult on the OneToOne field sample_id
        sample_list = self.model.objects.prefetch_related('mashresult').filter(
            Q(sample_id__icontains=search_term) |
            Q(project_id__project_id__icontains=search_term) |
            Q(sample_name__icontains=search_term) |
            Q(run_id__run_id__icontains=search_term) |
            Q(mashresult__top_hit__icontains=search_term)
        )

        minion_sample_list = MinIONSample.objects.filter(
            Q(sample_id__icontains=search_term) |
            Q(project_id__project_id__icontains=search_term) |
            Q(sample_name__icontains=search_term) |
            Q(run_id__run_id__icontains=search_term)
        )

        # Filter out hidden samples
        sample_list = sample_list.filter(hide_flag=False)

        context['search_term'] = search_term
        context['sample_list'] = sample_list
        context['minion_sample_list'] = minion_sample_list
        context['approved_users'] = UserProjectRelationship.objects.filter(user_id=self.request.user).order_by('id')
        return context


sample_search_view = SampleSearchView.as_view()
