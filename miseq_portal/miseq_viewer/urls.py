from django.urls import path, re_path, include
from rest_framework import routers

from miseq_portal.miseq_viewer.views import (
    project_list_view,
    project_detail_view,
    run_list_view,
    run_detail_view,
    sample_detail_view,
    SampleViewSet, RunViewSet, ProjectViewSet
    # samples_api_view
)

app_name = "miseq_viewer"

# Django-rest-framework (https://django-rest-framework-datatables.readthedocs.io/en/latest/tutorial.html)
router = routers.DefaultRouter()
router.register(r'samples', SampleViewSet, basename='samples-detail')
router.register(r'runs', RunViewSet, basename='runs-detail')
router.register(r'projects', ProjectViewSet, basename='projects-detail')

urlpatterns = [
    path("projects/", view=project_list_view, name="miseq_viewer_projects"),
    path("runs/", view=run_list_view, name="miseq_viewer_runs"),
    # path("samples_api/", view=samples_api_view, name="miseq_viewer_samples_api"),
    re_path("^api/", include(router.urls), name="miseq_viewer_api"),
    re_path("^project/(?P<pk>\d+)$", view=project_detail_view, name="miseq_viewer_project_detail"),
    re_path("^run/(?P<pk>\d+)$", view=run_detail_view, name="miseq_viewer_run_detail"),
    re_path("^sample/(?P<pk>\d+)$", view=sample_detail_view,
            name="miseq_viewer_sample_detail")
]
