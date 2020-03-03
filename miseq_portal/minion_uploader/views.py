from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


# Create your views here.
class MinIONUploaderIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'minion_uploader/minion_uploader_index.html'

    def get_context_data(self, **kwargs):
        context = super(MinIONUploaderIndexView, self).get_context_data(**kwargs)
        return context


minion_uploader_index_view = MinIONUploaderIndexView.as_view()
