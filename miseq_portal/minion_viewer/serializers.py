from rest_framework import serializers

from miseq_portal.miseq_viewer.serializers import ProjectSerializer
from miseq_portal.minion_viewer.models import MinIONRun, MinIONRunSamplesheet, MinIONSample
from miseq_portal.users.models import User


class MinIONRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = MinIONRun
        fields = '__all__'


class MinIONRunSamplesheetSerializer(serializers.ModelSerializer):
    run_id = MinIONRunSerializer()

    class Meta:
        model = MinIONRunSamplesheet
        fields = [
            'id',
            'created',
            'modified',
            'sample_sheet',
            'run_id'
        ]


class MinIONSampleSerializer(serializers.ModelSerializer):
    project_id = serializers.CharField()
    run_id = MinIONRunSerializer()

    class Meta:
        model = MinIONSample
        fields = '__all__'
