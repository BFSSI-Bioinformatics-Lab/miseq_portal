from django import forms
from django.forms import ModelForm

from miseq_viewer.models import Run, Project


# RUN
class RunModelForm(ModelForm):
    # Retrieve unique Project IDs and display in dropdown
    iquery = Project.objects.values_list('project_id', flat=True).distinct()
    iquery_choices = [(id, id) for id in iquery]
    project_id = forms.ChoiceField(choices=iquery_choices, required=True, widget=forms.Select())

    # Run ID
    run_id = forms.CharField(label="Run ID", required=True)

    # SampleSheet.csv
    sample_sheet = forms.FileField(widget=forms.FileInput(attrs={'class': 'form-control'}),
                                   label='Sample Sheet',
                                   required=True)

    def clean_project_id(self):
        data = self.cleaned_data['project_id']
        project = Project.objects.get(project_id=data)
        return project

    def clean_run_id(self):
        data = self.cleaned_data['run_id']
        return data

    def clean_sample_sheet(self):
        data = self.cleaned_data['sample_sheet']
        if 'csv' not in str(data):
            raise forms.ValidationError("Provided SampleSheet does not end in .csv")

    class Meta:
        model = Run
        fields = ['run_id', 'project_id', 'sample_sheet']

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
