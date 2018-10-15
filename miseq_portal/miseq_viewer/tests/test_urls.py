import pytest
from django.urls import reverse, resolve

pytestmark = pytest.mark.django_db


def test_index():
    assert reverse("miseq_viewer:miseq_viewer_projects") == "/miseq_viewer/"
    assert resolve("/miseq_viewer/").view_name == "miseq_viewer:miseq_viewer_projects"


def test_project_detail():
    pk = 1
    assert reverse("miseq_viewer:miseq_viewer_project_detail", kwargs={"pk": pk}) == f"/miseq_viewer/project/{pk}"
    assert resolve(f"/miseq_viewer/project/{pk}").view_name == "miseq_viewer:miseq_viewer_project_detail"


def test_run_detail():
    pk = 1
    assert reverse("miseq_viewer:miseq_viewer_run_detail", kwargs={"pk": pk}) == f"/miseq_viewer/run/{pk}"
    assert resolve(f"/miseq_viewer/run/{pk}").view_name == "miseq_viewer:miseq_viewer_run_detail"


def test_sample_detail():
    pk = 1
    assert reverse("miseq_viewer:miseq_viewer_sample_detail", kwargs={"pk": pk}) == f"/miseq_viewer/sample/{pk}"
    assert resolve(f"/miseq_viewer/sample/{pk}").view_name == "miseq_viewer:miseq_viewer_sample_detail"
