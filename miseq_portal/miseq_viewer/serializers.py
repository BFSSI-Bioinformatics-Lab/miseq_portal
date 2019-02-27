from rest_framework import serializers

from miseq_portal.analysis.models import SendsketchResult
from miseq_portal.miseq_viewer.models import Sample, Project, Run
from miseq_portal.users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class RunSerializer(serializers.ModelSerializer):
    class Meta:
        model = Run
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    project_owner = UserSerializer()

    class Meta:
        model = Project
        fields = '__all__'


class SendsketchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SendsketchResult
        fields = '__all__'


class SampleSerializer(serializers.ModelSerializer):
    run_id = RunSerializer()
    project_id = ProjectSerializer()
    sendsketchresult = SendsketchResultSerializer()

    class Meta:
        model = Sample
        fields = ['id', 'sample_id', 'sample_name', 'project_id', 'run_id',
                  'sample_type', 'fwd_reads', 'rev_reads', 'sendsketchresult'
                  ]
