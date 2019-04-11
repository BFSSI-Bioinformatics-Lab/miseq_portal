from django.urls import path, re_path

from miseq_portal.sample_merge.views import (
    sample_merge_index_view,
    sample_merge_queue_view,
    merge_success_view,
    sample_delete_view,
    sample_delete_success_view
)

app_name = "sample_merge"
urlpatterns = [
    # Index
    path("manual/", view=sample_merge_index_view, name="sample_merge_index"),
    path("queue/", view=sample_merge_queue_view, name="sample_merge_queue"),
    path("sample_delete/success", view=sample_delete_success_view, name="sample_delete_success_view"),
    re_path("^delete/(?P<pk>\d+)$", view=sample_delete_view, name="sample_delete_view"),
    re_path("^success/", view=merge_success_view, name="merge_success_view")
]
