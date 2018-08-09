from django.urls import path

from miseq_uploader.views import (
    sample_form_view,
    create_project_view,
    project_created_view,
    miseq_uploader_view,
    run_form_view,
    run_submitted_view
)

app_name = "miseq_uploader"
urlpatterns = [
    # Index
    path("", view=miseq_uploader_view, name="miseq_uploader"),

    # Projects
    path("create_project", view=create_project_view, name="create_project"),
    path("project_created/", view=project_created_view, name="project_created"),

    # Runs
    path("run_uploader", view=run_form_view, name="run_uploader"),
    path("run_submitted/", view=run_submitted_view, name="run_submitted"),

    # Samples
    path("sample_uploader", view=sample_form_view, name="sample_uploader"),

]
