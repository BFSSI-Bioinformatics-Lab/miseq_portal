from django.urls import path

from miseq_portal.analysis.views import (
    analysis_index_view,
    tool_selection_view,
)

app_name = "analysis"
urlpatterns = [
    # Index
    path("", view=analysis_index_view, name="analysis_index"),
    path("tool_selection/", view=tool_selection_view, name="tool_selection"),

]
