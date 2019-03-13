import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView, CreateView, DetailView
from rest_framework import viewsets, mixins, filters

from miseq_portal.miseq_viewer.models import Sample
from miseq_portal.sample_workbooks.forms import WorkbookForm
from miseq_portal.sample_workbooks.models import Workbook, WorkbookSample
from miseq_portal.sample_workbooks.serializers import WorkbookSerializer, WorkbookSampleSerializer
from miseq_portal.users.models import User

logger = logging.getLogger('django')


class SampleWorkbookIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'sample_workbooks/sample_workbooks_index.html'

    def get_context_data(self, **kwargs):
        context = super(SampleWorkbookIndexView, self).get_context_data(**kwargs)
        context['workbooks'] = Workbook.objects.filter(user=self.request.user)
        return context


sample_workbook_index_view = SampleWorkbookIndexView.as_view()


class CreateNewWorkbookView(LoginRequiredMixin, CreateView):
    template_name = 'sample_workbooks/create_new_workbook.html'
    model = Workbook
    form_class = WorkbookForm
    success_url = reverse_lazy('sample_workbooks:sample_workbook_index')

    def get_context_data(self, **kwargs):
        context = super(CreateNewWorkbookView, self).get_context_data(**kwargs)
        context['create_workbook_form'] = self.form_class
        return context

    def get_form_kwargs(self):
        """This method is what injects forms with keyword arguments."""
        # grab the current set of form #kwargs
        kwargs = super(CreateNewWorkbookView, self).get_form_kwargs()
        # Update the kwargs with the user_id
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = User.objects.get(username=self.request.user)
        form.instance.created_by = self.request.user
        form.save()

        # Grab samples that user selected from table and create entries in the database
        sample_id_list_raw = self.request.POST.get('sample_id_list')
        sample_id_list = sample_id_list_raw.split(",")

        # Get corresponding Sample objects from user selection
        for sample_id in sample_id_list:
            sample_object = Sample.objects.get(sample_id=sample_id)
            workbooksample_object = WorkbookSample.objects.create(sample=sample_object, workbook=form.instance)
            workbooksample_object.save()

        messages.add_message(self.request, messages.SUCCESS,
                             f'Workbook "{form.instance.workbook_title}" created successfully!')
        return super(CreateNewWorkbookView, self).form_valid(form)


create_new_workbook_view = CreateNewWorkbookView.as_view()


class WorkbookDetailView(LoginRequiredMixin, DetailView):
    model = Workbook
    context_object_name = 'workbook'
    template_name = "sample_workbooks/workbook_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


workbook_detail_view = WorkbookDetailView.as_view()


class WorkbookViewSet(viewsets.ModelViewSet, mixins.UpdateModelMixin):
    serializer_class = WorkbookSerializer
    queryset = Workbook.objects.all()


class WorkbookSampleViewset(viewsets.ModelViewSet, mixins.UpdateModelMixin):
    serializer_class = WorkbookSampleSerializer
    queryset = WorkbookSample.objects.all()
    filter_backends = (filters.SearchFilter,)
    search_fields = ('sample__sample_id', 'workbook__workbook_title',)
