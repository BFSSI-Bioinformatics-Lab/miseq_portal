from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from miseq_viewer.models import Sample


class SampleSearchView(LoginRequiredMixin, ListView):
    template_name = 'sample_search/sample_search.html'
    model = Sample
    context_object_name = 'sample_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


sample_search_view = SampleSearchView.as_view()
