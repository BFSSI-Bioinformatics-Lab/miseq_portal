from django.views.generic import View
from django.shortcuts import render, redirect, get_object_or_404

from .forms import RunModelForm
from miseq_viewer.models import Project


class RunFormView(View):
    form_class = RunModelForm
    template_name = 'miseq_uploader/miseq_uploader.html'
    success_url = 'miseq_uploader/run_submitted.html'

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        # Get copy of POST
        post = request.POST.copy()

        # Update project_id field
        project_id = post.get('project_id')
        print(f"project_id: {project_id}")
        # project = get_object_or_404(Project.objects, project_id=project_id)
        project = Project.objects.get(project_id=project_id)
        print(f"project: {project}")

        post['project_id'] = project

        # Reset POST
        request.POST = post

        form = self.form_class(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return redirect(self.success_url)
        else:
            print('something bad happened')
            return render(request, self.template_name, {'form': form})

    # def post(self, request):
    #     form = self.form_class(request.POST, request.FILES)
    #     if form.is_valid():
    #         form.save()
    #         return redirect(self.success_url)
    #     else:
    #         return render(request, self.template_name, {'form': form})


run_form_view = RunFormView.as_view()


class RunSubmittedView(View):
    # form_class = RunModelForm
    template_name = 'miseq_uploader/run_submitted.html'

    # def post(self, request):
    #     print('yep we posting')
    #     form = self.form_class(request.POST, request.FILES)
    #     if form.is_valid():
    #         form.save()
    #         return redirect(self.template_name)
    #     else:
    #         print('something bad happened')
    #         return render(request, self.template_name, {'form': form})


run_submitted_view = RunSubmittedView.as_view()
