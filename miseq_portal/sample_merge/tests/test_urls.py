import pytest
from django.urls import reverse, resolve

pytestmark = pytest.mark.django_db


def test_index():
    assert reverse("sample_merge:sample_merge_index") == "/sample_merge/"
    assert resolve("/sample_merge/").view_name == "sample_merge:sample_merge_index"


def test_sample_delete():
    pk = 1
    assert reverse("sample_merge:sample_delete_view", kwargs={"pk": pk}) == f"/sample_merge/sample_delete/{pk}"
    assert resolve(f"/sample_merge/sample_delete/{pk}").view_name == "sample_merge:sample_delete_view"


def test_sample_delete_success():
    assert reverse("sample_merge:sample_delete_success_view") == "/sample_merge/sample_delete/success"
    assert resolve("/sample_merge/sample_delete/success").view_name == "sample_merge:sample_delete_success_view"


def test_merge_success():
    assert reverse("sample_merge:merge_success_view") == "/sample_merge/merge_success/"
    assert resolve("/sample_merge/merge_success/").view_name == "sample_merge:merge_success_view"
