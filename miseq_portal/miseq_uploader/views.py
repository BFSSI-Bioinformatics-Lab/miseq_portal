from django.views.generic.edit import FormView
from django.views.generic import View
from django.shortcuts import render, redirect

from .forms import RunModelForm


class RunFormView(View):
    form_class = RunModelForm
    template_name = 'miseq_uploader/miseq_uploader.html'
    success_url = 'miseq_uploader/run_submitted.html'

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect(self.success_url)
        else:
            return render(request, self.template_name, {'form': form})


run_form_view = RunFormView.as_view()


class RunSubmittedView(View):
    template_name = 'miseq_uploader/run_submitted.html'

    def post(self, request):
        return render(request, self.template_name, {})


run_submitted_view = RunSubmittedView.as_view()
