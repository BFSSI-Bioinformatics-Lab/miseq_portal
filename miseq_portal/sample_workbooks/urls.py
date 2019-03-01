from django.urls import path, re_path

from miseq_portal.sample_workbooks.views import (
    sample_workbook_index_view,
    create_new_workbook_view,
    workbook_detail_view
)

app_name = "sample_workbooks"
urlpatterns = [
    path("", view=sample_workbook_index_view, name="sample_workbook_index"),
    path("create/", view=create_new_workbook_view, name="create_new_workbook"),
    re_path("^detail/(?P<pk>\d+)$", view=workbook_detail_view, name="workbook_detail"),
]
