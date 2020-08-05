from django.urls import path, re_path, include
from rest_framework import routers

from miseq_portal.sample_workbooks.views import (
    sample_workbook_index_view,
    create_new_workbook_view,
    workbook_detail_view,
    workbook_delete_view,
    workbook_delete_success_view,
    WorkbookViewSet, WorkbookSampleViewset
)

app_name = "sample_workbooks"

# Django-rest-framework (https://django-rest-framework-datatables.readthedocs.io/en/latest/tutorial.html)
router = routers.DefaultRouter()
router.register(r'workbooks', WorkbookViewSet, basename='workbooks-detail')
router.register(r'workbooksamples', WorkbookSampleViewset, basename='workbook-samples-detail')

urlpatterns = [
    path("", view=sample_workbook_index_view, name="sample_workbook_index"),
    path("create/", view=create_new_workbook_view, name="create_new_workbook"),
    re_path("^detail/(?P<pk>\d+)$", view=workbook_detail_view, name="workbook_detail"),
    re_path("^api/", include(router.urls), name="workbook_api"),

    # Deleting Workbook views
    re_path("^detail/(?P<pk>\d+)/delete$", view=workbook_delete_view, name="workbook_delete_view"),
    re_path("^delete_success/$", view=workbook_delete_success_view, name="workbook_delete_success_view")
]
