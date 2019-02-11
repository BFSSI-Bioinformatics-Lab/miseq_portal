from django.urls import path

from miseq_portal.miseq_uploader.views import (
    miseq_form_view,
    miseq_uploader_view
)

app_name = "miseq_uploader"
urlpatterns = [
    # Index
    path("", view=miseq_uploader_view, name="miseq_uploader"),

    # MiSeq Directory Upload
    path("miseq_directory_uploader", view=miseq_form_view, name="miseq_form"),
]
