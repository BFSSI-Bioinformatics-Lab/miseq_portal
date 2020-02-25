from django.urls import path, re_path

from miseq_portal.sample_downloader.views import (
    downloader_sample_select_view,
    downloader_sample_confirm_view)

app_name = "sample_downloader"
urlpatterns = [
    # Sample selector
    path("", view=downloader_sample_select_view, name="downloader_sample_select"),

    # Page for selecting analysis tools
    path("sample_downloader/confirm/", view=downloader_sample_confirm_view, name="download_sample_confirm"),
]
