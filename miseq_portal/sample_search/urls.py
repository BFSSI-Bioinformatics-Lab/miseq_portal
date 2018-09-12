from django.urls import path

from miseq_portal.sample_search.views import (
    sample_search_view
)

app_name = "sample_search"
urlpatterns = [
    path("", view=sample_search_view, name="sample_search"),
]
