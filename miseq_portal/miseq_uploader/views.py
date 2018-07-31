from django.views.generic.edit import FormView
from django.views.generic import TemplateView
from .forms import RunForm


class RunFormView(FormView):
    form_class = RunForm
    template_name = 'miseq_uploader/miseq_uploader.html'
    success_url = 'miseq_uploader/run_submitted.html'


run_form_view = RunFormView.as_view()


# class RunSubmittedView(FormView):
#     template_name = 'miseq_uploader/run_submitted.html'
#
#
# run_submitted_view = RunSubmittedView.as_view()
