from django.urls import path, re_path, include
from rest_framework import routers

from miseq_portal.minion_viewer.views import (
    minion_viewer_index_view,
)

app_name = "minion_viewer"

# Django-rest-framework (https://django-rest-framework-datatables.readthedocs.io/en/latest/tutorial.html)
router = routers.DefaultRouter()
# router.register(r'workbooks', WorkbookViewSet, base_name='workbooks-detail')

urlpatterns = [
    path("", view=minion_viewer_index_view, name="minion_viewer_index"),
]
