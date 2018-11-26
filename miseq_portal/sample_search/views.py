from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from miseq_portal.miseq_viewer.models import Sample, UserProjectRelationship


class SampleSearchView(LoginRequiredMixin, ListView):
    """
    TODO: This desperately needs to be refactored to load data on the fly rather than in one huge chunk
    """
    template_name = 'sample_search/sample_search.html'
    model = Sample
    context_object_name = 'sample_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['approved_users'] = UserProjectRelationship.objects.filter(user_id=self.request.user).order_by('id')
        return context


sample_search_view = SampleSearchView.as_view()
