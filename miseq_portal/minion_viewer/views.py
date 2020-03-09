from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from miseq_portal.minion_viewer.models import MinIONRun, MinIONRunSamplesheet, MinIONSample
from django.views.generic import DetailView, ListView
from rest_framework import viewsets
from miseq_portal.minion_viewer.serializers import MinIONRunSerializer, MinIONRunSamplesheetSerializer, \
    MinIONSampleSerializer


# Create your views here.
class MinIONViewerIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'minion_viewer/minion_viewer_index.html'

    def get_context_data(self, **kwargs):
        context = super(MinIONViewerIndexView, self).get_context_data(**kwargs)
        return context


minion_viewer_index_view = MinIONViewerIndexView.as_view()


class MinIONRunDetailView(LoginRequiredMixin, DetailView):
    model = MinIONRun
    context_object_name = 'run'
    template_name = "minion_viewer/minion_run_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['samplesheet'] = MinIONRunSamplesheet.objects.get(run_id=context['run']).sample_sheet
        context['sample_list'] = MinIONSample.objects.filter(run_id=context['run'])
        print(context)

        return context


minion_run_detail_view = MinIONRunDetailView.as_view()


class MinIONSampleDetailView(LoginRequiredMixin, DetailView):
    model = MinIONSample
    context_object_name = 'sample'
    template_name = 'minion_viewer/minion_sample_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


minion_sample_detail_view = MinIONSampleDetailView.as_view()


class MinIONRunSamplesheetListView(LoginRequiredMixin, ListView):
    queryset = MinIONRunSamplesheet.objects.all().order_by('-created')
    context_object_name = 'run_list'
    template_name = "minion_viewer/minion_run_list.html"


minion_run_list_view = MinIONRunSamplesheetListView.as_view()


class MinIONRunViewSet(viewsets.ModelViewSet):
    queryset = MinIONRun.objects.all().order_by('run_id')
    serializer_class = MinIONRunSerializer


class MinIONRunSamplesheetViewSet(viewsets.ModelViewSet):
    queryset = MinIONRunSamplesheet.objects.all().order_by('run_id__run_id')
    serializer_class = MinIONRunSamplesheetSerializer


class MinIONSampleViewSet(viewsets.ModelViewSet):
    queryset = MinIONSample.objects.all().order_by('sample_name')
    serializer_class = MinIONSampleSerializer
