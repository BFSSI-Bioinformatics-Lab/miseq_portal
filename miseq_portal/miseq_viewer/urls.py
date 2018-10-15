from django.urls import path, re_path

from miseq_portal.miseq_viewer.views import (
    project_list_view,
    project_detail_view,
    run_detail_view,
    sample_detail_view
)

app_name = "miseq_viewer"
urlpatterns = [
    path("", view=project_list_view, name="miseq_viewer_projects"),
    re_path("^project/(?P<pk>\d+)$", view=project_detail_view, name="miseq_viewer_project_detail"),
    re_path("^run/(?P<pk>\d+)$", view=run_detail_view, name="miseq_viewer_run_detail"),
    re_path("^sample/(?P<pk>\d+)$", view=sample_detail_view,
            name="miseq_viewer_sample_detail")
]
