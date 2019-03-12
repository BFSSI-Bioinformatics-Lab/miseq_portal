from rest_framework import serializers

from miseq_portal.miseq_viewer.serializers import SampleSerializer
from miseq_portal.sample_workbooks.models import Workbook, WorkbookSample


class WorkbookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workbook
        fields = '__all__'


class WorkbookSampleSerializer(serializers.ModelSerializer):
    workbook = WorkbookSerializer(read_only=True)
    sample = SampleSerializer(read_only=True)

    class Meta:
        model = WorkbookSample
        fields = '__all__'
