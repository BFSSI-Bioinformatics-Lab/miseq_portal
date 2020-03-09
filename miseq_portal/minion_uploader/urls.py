from django.urls import path
from rest_framework import routers

from miseq_portal.minion_uploader.views import (
    MinIONUploaderIndexView,
    UploadSuccessView,
    MinIONRunChunkedUploadView,
    MinIONRunChunkedUploadCompleteView
)

app_name = "minion_uploader"

# Django-rest-framework (https://django-rest-framework-datatables.readthedocs.io/en/latest/tutorial.html)
router = routers.DefaultRouter()
# router.register(r'workbooks', WorkbookViewSet, base_name='workbooks-detail')

urlpatterns = [
    path("", view=MinIONUploaderIndexView.as_view(), name="minion_uploader_index"),
    path("upload_success/", view=UploadSuccessView.as_view(), name="upload_success"),
    path("api/chunked_upload_complete/", view=MinIONRunChunkedUploadCompleteView.as_view(),
         name="api_chunked_upload_complete"),
    path("api/chunked_upload/", view=MinIONRunChunkedUploadView.as_view(), name="api_chunked_upload"),
]
