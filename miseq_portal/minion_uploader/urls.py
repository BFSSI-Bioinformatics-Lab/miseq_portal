from django.urls import path, re_path, include
from rest_framework import routers

from miseq_portal.minion_uploader.views import (
    minion_uploader_index_view,
)

app_name = "minion_uploader"

# Django-rest-framework (https://django-rest-framework-datatables.readthedocs.io/en/latest/tutorial.html)
router = routers.DefaultRouter()
# router.register(r'workbooks', WorkbookViewSet, base_name='workbooks-detail')

urlpatterns = [
    path("", view=minion_uploader_index_view, name="minion_uploader_index"),
]
