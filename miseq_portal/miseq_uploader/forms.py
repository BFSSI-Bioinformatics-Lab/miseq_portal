from django import forms
from django.forms import ModelForm

from miseq_viewer.models import Run, Project


# RUN
class RunModelForm(ModelForm):
    # project_id = forms.ModelChoiceField(queryset=Project.objects.all().values_list('project_id', flat=True).distinct(),
    #                                     label='Project ID')
    # project_id = forms.ModelChoiceField(queryset=Run.objects.all().values('project_id').distinct())
    iquery = Project.objects.values_list('project_id', flat=True).distinct()
    iquery_choices = [(id, id) for id in iquery]
    project_id = forms.ChoiceField(choices=iquery_choices, required=True, widget=forms.Select())

    run_id = forms.CharField(label="Run ID")
    sample_sheet = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': False}),
                                   label='Sample Sheet',
                                   required=True)

    class Meta:
        model = Run
        fields = ['project_id', 'run_id', 'sample_sheet']

# # SAMPLE
# class SampleForm(forms.Form):
#     fwd_reads = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': False}),
#                                 label="*_R1*.fastq.gz",
#                                 required=True)
#     rev_reads = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': False}),
#                                 label="*_R2*.fastq.gz",
#                                 required=True)
#
#
# class SampleModelForm(ModelForm):
#     class Meta:
#         model = Run
#         fields = ['fwd_reads', 'rev_reads']
