from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


# Create your views here.
class MinIONViewerIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'minion_viewer/minion_viewer_index.html'

    def get_context_data(self, **kwargs):
        context = super(MinIONViewerIndexView, self).get_context_data(**kwargs)
        return context


minion_viewer_index_view = MinIONViewerIndexView.as_view()
