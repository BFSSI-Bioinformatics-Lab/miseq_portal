from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import View, TemplateView
from django.shortcuts import render, redirect
from django.http import Http404

from pathlib import Path

from .forms import RunModelForm, CreateProjectForm, UploadMiSeqDirectoryForm
from miseq_viewer.models import Project
from miseq_uploader.upload_to_db import receive_miseq_run_dir

import logging
logger = logging.getLogger('raven')


class MiseqUploaderView(LoginRequiredMixin, TemplateView):
    template_name = 'miseq_uploader/miseq_uploader.html'


miseq_uploader_view = MiseqUploaderView.as_view()


class SampleFormView(LoginRequiredMixin, View):
    template_name = 'miseq_uploader/sample_uploader.html'

    def get(self, request):
        return render(request, self.template_name, {})


sample_form_view = SampleFormView.as_view()


class CreateProjectView(LoginRequiredMixin, View):
    form_class = CreateProjectForm
    template_name = 'miseq_uploader/create_project.html'
    success_url = 'project_created/'

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)

        if form.is_valid():
            obj = form.save(commit=False)
            obj.project_id = request.POST['project_id']
            obj.save()
            return redirect(self.success_url)
        else:
            logger.info('Form not valid')
            return render(request, self.template_name, {'form': form})


create_project_view = CreateProjectView.as_view()


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
            logger.info('something bad happened??')
            return render(request, self.template_name, {'form': form})


miseq_form_view = MiSeqFormView.as_view()


class RunFormView(LoginRequiredMixin, View):
    form_class = RunModelForm
    template_name = 'miseq_uploader/run_uploader.html'
    success_url = 'run_submitted/'

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        # Get copy of POST
        post = request.POST.copy()

        # Update project_id field
        project_id = post.get('project_id')
        try:
            project = Project.objects.get(project_id=project_id)
        except Project.DoesNotExist:
            logger.info(f'Could not retrieve the following project: {project_id}')
            return
        post['project_id'] = project
        post['project_id_id'] = project.pk

        # Reset POST
        request.POST = post

        form = self.form_class(request.POST, request.FILES)

        if form.is_valid():
            obj = form.save(commit=False)
            obj.run_id = post['run_id']
            obj.project_id_id = post['project_id_id']  # Have to manually save the pk of the project in this column
            obj.sample_sheet = request.FILES['sample_sheet']
            obj.save()
            return redirect(self.success_url)
        else:
            # TODO: Make this better
            logger.info('Form not valid')
            return render(request, self.template_name, {'form': form})


run_form_view = RunFormView.as_view()


class RunSubmittedView(LoginRequiredMixin, TemplateView):
    template_name = 'miseq_uploader/run_submitted.html'


run_submitted_view = RunSubmittedView.as_view()


class ProjectCreatedView(LoginRequiredMixin, TemplateView):
    template_name = 'miseq_uploader/project_created.html'


project_created_view = ProjectCreatedView.as_view()
