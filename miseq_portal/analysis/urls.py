from django.urls import path, re_path

from miseq_portal.analysis.views import (
    analysis_index_view,
    tool_selection_view,
    my_jobs_view,
    job_submitted_view,
    analysis_group_detail_view,
    analysis_group_delete_view,
    analysis_group_delete_success_view
)

app_name = "analysis"
urlpatterns = [
    # Index
    path("", view=analysis_index_view, name="analysis_index"),
    path("tool_selection/", view=tool_selection_view, name="tool_selection"),
    path("tool_selection/job_submitted/", view=job_submitted_view, name="job_submitted"),
    path("my_jobs/", view=my_jobs_view, name="my_jobs"),
    re_path("^my_jobs/(?P<pk>\d+)$", view=analysis_group_detail_view, name="analysis_group_detail_view"),
    re_path("^my_jobs/(?P<pk>\d+)/delete$", view=analysis_group_delete_view, name="analysis_group_delete_view"),
    path("analysis_group_deleted/success", view=analysis_group_delete_success_view,
         name="analysis_group_delete_success_view")
]
