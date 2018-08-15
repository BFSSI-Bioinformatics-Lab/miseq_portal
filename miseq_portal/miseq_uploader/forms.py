from django import forms
from django.forms import ModelForm, Form

from miseq_portal.users.models import User
from miseq_viewer.models import Run, Project
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


# MISEQ DIRECTORY
class UploadMiSeqDirectoryForm(Form):
    miseq_directory = forms.CharField(widget=forms.TextInput())

    def __init__(self, *args, **kwargs):
        super(UploadMiSeqDirectoryForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'id-uploadMiSeqDirectoryForm'
        self.helper.form_class = 'blueForms'
        self.helper.form_method = 'post'
        self.helper.form_action = 'upload_miseq_directory'
        self.fields['miseq_directory'].label = 'MiSeq Directory'
        self.helper.add_input(Submit('submit', 'Submit'))


# PROJECT
class CreateProjectForm(ModelForm):
    project_id = forms.CharField(label="Project ID", required=True)
    project_owner = forms.ModelChoiceField(queryset=User.objects.all())

    def __init__(self, *args, **kwargs):
        super(CreateProjectForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'id-uploadRunForm'
        self.helper.form_class = 'blueForms'
        self.helper.form_method = 'post'
        self.helper.form_action = 'create_project'
        self.fields['project_id'].label = 'Project ID'
        self.fields['project_owner'].label = 'Project Owner'
        self.helper.add_input(Submit('submit', 'Submit'))

    class Meta:
        model = Project
        fields = ['project_id', 'project_owner']


# RUN
class RunModelForm(ModelForm):
    # Retrieve unique Project IDs and display in dropdown
    iquery = Project.objects.values_list('project_id', flat=True)
    iquery_choices = sorted([(id, id) for id in iquery])
    project_id = forms.ChoiceField(choices=iquery_choices, required=True, widget=forms.Select(), label="Project ID")

    # Run ID
    run_id = forms.CharField(label="Run ID", required=True)

    # SampleSheet.csv
    sample_sheet = forms.FileField(widget=forms.FileInput(),
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

    def __init__(self, *args, **kwargs):
        super(RunModelForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'id-uploadRunForm'
        self.helper.form_class = 'blueForms'
        self.helper.form_method = 'post'
        self.helper.form_action = 'run_submitted'

        self.helper.add_input(Submit('submit', 'Submit'))

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
