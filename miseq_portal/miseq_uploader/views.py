from django.views.generic import View, TemplateView
from django.shortcuts import render, redirect

from .forms import RunModelForm
from miseq_viewer.models import Project


class RunFormView(View):
    form_class = RunModelForm
    template_name = 'miseq_uploader/miseq_uploader.html'
    success_url = 'run_submitted.html'

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
            print(f'Could not retrieve the following project: {project_id}')
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
            print('Form not valid')
            return render(request, self.template_name, {'form': form})


run_form_view = RunFormView.as_view()


class RunSubmittedView(TemplateView):
    template_name = 'miseq_uploader/run_submitted.html'


run_submitted_view = RunSubmittedView.as_view()
