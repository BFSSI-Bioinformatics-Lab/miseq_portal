from rest_framework import serializers

from miseq_portal.analysis.models import SendsketchResult, MashResult, ConfindrResultAssembly
from miseq_portal.miseq_viewer.models import Sample, Project, Run
from miseq_portal.users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class RunSerializer(serializers.ModelSerializer):
    num_samples = serializers.ReadOnlyField()
    #sample_sheet_url = serializers.SerializerMethodField()

    class Meta:
        model = Run
        fields = ['id', 'run_id', 'sample_sheet', 'runinfoxml', 'runparametersxml', 'interop_directory_path',
                  'run_type', 'num_samples', 'created', 'modified']

    @staticmethod
    def get_sample_sheet(obj):
        return obj.sample_sheet.url


class ProjectSerializer(serializers.ModelSerializer):
    project_owner = UserSerializer()

    class Meta:
        model = Project
        fields = '__all__'


class SendsketchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SendsketchResult
        fields = '__all__'


class MashResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = MashResult
        fields = '__all__'


class ConfindrResultAssemblySerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfindrResultAssembly
        fields = '__all__'

class SampleSerializer(serializers.ModelSerializer):
    run_id = RunSerializer()
    project_id = ProjectSerializer()
    sendsketchresult = SendsketchResultSerializer()
    mashresult = MashResultSerializer()
    confindrresultassembly = ConfindrResultAssemblySerializer()

    class Meta:
        model = Sample
        fields = ['id', 'sample_id', 'sample_name', 'project_id', 'run_id',
                  'sample_type', 'fwd_reads', 'rev_reads', 'sendsketchresult', 'mashresult', 'confindrresultassembly'
                  ]
