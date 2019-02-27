from django.urls import path, re_path

from miseq_portal.analysis.views import (
    tool_selection_view,
    my_jobs_view,
    job_submitted_view,
    analysis_group_detail_view,
    analysis_group_delete_view,
    analysis_group_delete_success_view,
    sample_select_view
)

app_name = "analysis"
urlpatterns = [
    # Sample selector
    path("sample_select/", view=sample_select_view, name="sample_select"),

    # Page for selecting analysis tools
    path("sample_select/tools/", view=tool_selection_view, name="tool_selection"),

    # Successful job submission page
    path("sample_select/tools/job_submitted/", view=job_submitted_view, name="job_submitted"),

    # Analysis jobs pages
    path("my_jobs/", view=my_jobs_view, name="my_jobs"),
    re_path("^my_jobs/(?P<pk>\d+)$", view=analysis_group_detail_view, name="analysis_group_detail_view"),
    re_path("^my_jobs/(?P<pk>\d+)/delete$", view=analysis_group_delete_view, name="analysis_group_delete_view"),

    # Analysis deleted success page
    path("analysis_group_deleted/success", view=analysis_group_delete_success_view,
         name="analysis_group_delete_success_view")
]
