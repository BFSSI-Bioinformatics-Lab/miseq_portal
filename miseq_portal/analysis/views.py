from django.shortcuts import render

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from miseq_viewer.models import Sample


class AnalysisIndexView(LoginRequiredMixin, ListView):
    template_name = 'analysis/analysis_index.html'
    model = Sample
    context_object_name = 'sample_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        # Grab selected sample list from the analysis_index.html page via AJAX
        sample_id_list = request.POST.getlist('sample_id_list[]')

        # Get corresponding Sample objects
        sample_object_list = list()
        for sample_id in sample_id_list:
            sample_object = Sample.objects.get(sample_id=sample_id)
            sample_object_list.append(sample_object)

        for sample_object in sample_object_list:
            print(sample_object)

        return render(request, self.template_name, {})


analysis_index_view = AnalysisIndexView.as_view()
