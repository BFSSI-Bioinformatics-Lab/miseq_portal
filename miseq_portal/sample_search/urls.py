from django.urls import path, re_path

from miseq_portal.sample_search.views import (
    sample_search_view,
    sample_search_view_json
)

app_name = "sample_search"
urlpatterns = [
    path("", view=sample_search_view, name="sample_search"),
    re_path("^sample_search_view_json", view=sample_search_view_json, name="sample_search_view_json"),
]
