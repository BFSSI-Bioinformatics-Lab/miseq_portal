from django.urls import path, re_path, include
from rest_framework import routers

from miseq_portal.minion_viewer.views import (
    minion_viewer_index_view,
    minion_run_list_view,
    minion_sample_detail_view,
    minion_run_detail_view,
    MinIONRunViewSet,
    MinIONRunSamplesheetViewSet,
    MinIONSampleViewSet,
)

app_name = "minion_viewer"

# Django-rest-framework (https://django-rest-framework-datatables.readthedocs.io/en/latest/tutorial.html)
router = routers.DefaultRouter()
router.register(r'minion_runs', MinIONRunViewSet, basename='minion-run')
router.register(r'minion_samples', MinIONSampleViewSet, basename='minion-sample')
router.register(r'minion_samplesheets', MinIONRunSamplesheetViewSet, basename='minion-samplesheet')

urlpatterns = [
    path("", view=minion_viewer_index_view, name="minion_viewer_index"),
    re_path("^api/", include(router.urls), name="minion_viewer_api"),
    path("runs/", view=minion_run_list_view, name="minion_viewer_runs"),
    re_path("^run/(?P<pk>\d+)$", view=minion_run_detail_view, name="minion_run_detail"),
    re_path("^sample/(?P<pk>\d+)$", view=minion_sample_detail_view,
            name="minion_sample_detail")
]
