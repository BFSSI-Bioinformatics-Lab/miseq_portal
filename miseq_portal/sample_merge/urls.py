from django.urls import path, re_path

from miseq_portal.sample_merge.views import (sample_merge_index_view, merge_success_view)

app_name = "sample_merge"
urlpatterns = [
    # Index
    path("", view=sample_merge_index_view, name="sample_merge_index"),
    re_path("^merge_success/", view=merge_success_view, name="merge_success_view")
]
