from django.urls import path

from miseq_portal.sample_workbooks.views import (
    sample_workbook_index_view
)

app_name = "sample_workbooks"
urlpatterns = [
    path("", view=sample_workbook_index_view, name="sample_workbook_index"),

]
