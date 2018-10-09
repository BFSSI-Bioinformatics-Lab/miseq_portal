from django.urls import path, re_path

from miseq_portal.sample_merge.views import (sample_merge_index_view)

app_name = "sample_merge"
urlpatterns = [
    # Index
    path("", view=sample_merge_index_view, name="sample_merge_index"),
    # re_path("^my_jobs/(?P<pk>\d+)$", view=analysis_group_detail_view, name="analysis_group_detail_view")
]
