from django.urls import path

from miseq_uploader.views import (
    run_form_view,
    run_submitted_view
)

app_name = "miseq_uploader"
urlpatterns = [
    path("", view=run_form_view, name="miseq_uploader"),
    path("run_submitted.html", view=run_submitted_view, name="run_submitted"),
]
