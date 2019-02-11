from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.forms import Form


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
