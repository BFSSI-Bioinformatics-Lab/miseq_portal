from django.urls import path

from analysis.views import (
    analysis_index_view,
)

app_name = "analysis"
urlpatterns = [
    # Index
    path("", view=analysis_index_view, name="analysis_index"),

]
