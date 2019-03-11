from django.urls import path, re_path, include
from rest_framework import routers

from miseq_portal.sample_workbooks.views import (
    sample_workbook_index_view,
    create_new_workbook_view,
    workbook_detail_view,
    WorkbookViewSet, WorkbookSampleViewset
)

app_name = "sample_workbooks"

# Django-rest-framework (https://django-rest-framework-datatables.readthedocs.io/en/latest/tutorial.html)
router = routers.DefaultRouter()
router.register(r'workbooks', WorkbookViewSet, base_name='workbooks-detail')
router.register(r'workbooksamples', WorkbookSampleViewset, base_name='workbook-samples-detail')

urlpatterns = [
    path("", view=sample_workbook_index_view, name="sample_workbook_index"),
    path("create/", view=create_new_workbook_view, name="create_new_workbook"),
    re_path("^detail/(?P<pk>\d+)$", view=workbook_detail_view, name="workbook_detail"),
    re_path("^api/", include(router.urls), name="workbook_api"),
]
