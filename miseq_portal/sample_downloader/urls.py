from django.urls import path, re_path

from miseq_portal.sample_downloader.views import (
    downloader_sample_select_view,
    downloader_sample_confirm_view, downloader_sample_receive_view)

app_name = "sample_downloader"
urlpatterns = [
    # Sample selector
    path("", view=downloader_sample_select_view, name="downloader_sample_select"),

    # Page for selecting file type
    path("confirm/", view=downloader_sample_confirm_view, name="download_sample_confirm"),

    # Page for receiving downloaded file
    path("receive/", view=downloader_sample_receive_view, name="download_sample_receive"),
]
