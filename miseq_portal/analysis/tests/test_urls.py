import pytest
from django.urls import reverse, resolve

pytestmark = pytest.mark.django_db


def test_index():
    assert reverse("analysis:analysis_index") == "/analysis/"
    assert resolve("/analysis/").view_name == "analysis:analysis_index"


def test_tool_selection():
    assert reverse("analysis:tool_selection") == "/analysis/tool_selection/"
    assert resolve("/analysis/tool_selection/").view_name == "analysis:tool_selection"


def test_tool_selection_job_submitted():
    assert reverse("analysis:job_submitted") == "/analysis/tool_selection/job_submitted/"
    assert resolve("/analysis/tool_selection/job_submitted/").view_name == "analysis:job_submitted"


def test_my_jobs():
    assert reverse("analysis:my_jobs") == "/analysis/my_jobs/"
    assert resolve("/analysis/my_jobs/").view_name == "analysis:my_jobs"


def test_analysis_group_detail():
    pk = 1
    assert reverse("analysis:analysis_group_detail_view", kwargs={"pk": pk}) == f"/analysis/my_jobs/{pk}"
    assert resolve(f"/analysis/my_jobs/{pk}").view_name == "analysis:analysis_group_detail_view"


def test_analysis_group_delete():
    pk = 1
    assert reverse("analysis:analysis_group_delete_view", kwargs={"pk": pk}) == f"/analysis/my_jobs/{pk}/delete"
    assert resolve(f"/analysis/my_jobs/{pk}/delete").view_name == "analysis:analysis_group_delete_view"


def test_analysis_group_delete_success():
    assert reverse("analysis:analysis_group_delete_success_view") == "/analysis/analysis_group_deleted/success"
    assert resolve(
        "/analysis/analysis_group_deleted/success").view_name == "analysis:analysis_group_delete_success_view"
