from django.urls import path

from miseq_portal.analysis.views import (
    analysis_index_view,
    tool_selection_view,
    my_jobs_view,
    job_submitted_view
)

app_name = "analysis"
urlpatterns = [
    # Index
    path("", view=analysis_index_view, name="analysis_index"),
    path("tool_selection/", view=tool_selection_view, name="tool_selection"),
    path("tool_selection/job_submitted/", view=job_submitted_view, name="job_submitted"),
    path("my_jobs/", view=my_jobs_view, name="my_jobs"),

]
