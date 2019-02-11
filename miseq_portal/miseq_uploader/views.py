import logging
from pathlib import Path

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.generic import View, TemplateView

from miseq_portal.miseq_uploader.forms import UploadMiSeqDirectoryForm
from miseq_portal.miseq_uploader.upload_to_db import receive_miseq_run_dir

# logger = logging.getLogger('raven')
logger = logging.getLogger(__name__)


@method_decorator(staff_member_required, name='dispatch')
class MiseqUploaderView(LoginRequiredMixin, TemplateView):
    template_name = 'miseq_uploader/miseq_uploader.html'


miseq_uploader_view = MiseqUploaderView.as_view()


@method_decorator(staff_member_required, name='dispatch')
class SampleFormView(LoginRequiredMixin, View):
    template_name = 'miseq_uploader/sample_uploader.html'

    def get(self, request):
        return render(request, self.template_name, {})


sample_form_view = SampleFormView.as_view()


@method_decorator(staff_member_required, name='dispatch')
class MiSeqFormView(LoginRequiredMixin, UserPassesTestMixin, View):
    form_class = UploadMiSeqDirectoryForm
    template_name = 'miseq_uploader/upload_miseq_directory.html'

    # success_url = 'miseq_directory_uploaded/'  # TODO: actually make this page
    success_url = 'run_submitted/'

    # Only staff can access this page
    def test_func(self):
        if self.request.user.is_staff:
            return True
        else:
            raise Http404("You are not authenticated to view this page.")

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)

        if form.is_valid():
            receive_miseq_run_dir(Path(request.POST['miseq_directory']))
            return redirect(self.success_url)
        else:
            logging.warning("Could not submit form!")
            return render(request, self.template_name, {'form': form})


miseq_form_view = MiSeqFormView.as_view()
