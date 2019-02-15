from rest_framework import serializers

from miseq_portal.miseq_viewer.models import Sample


class SampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sample
        # fields = '__all__'
        fields = ['id', 'sample_id', 'sample_name', 'project_id', 'run_id', 'sample_type', 'fwd_reads', 'rev_reads']

