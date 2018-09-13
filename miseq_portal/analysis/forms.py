from django import forms
from .models import AnalysisGroup

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class AnalysisToolForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(AnalysisToolForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'id-submitAnalysisJobForm'
        self.helper.form_class = 'blueForms'
        self.helper.form_method = 'post'
        self.helper.form_action = 'tool_selection'
        self.fields['job_type'].label = 'Job Type'
        self.helper.add_input(Submit('submit', 'Submit', css_class='btn btn-success'))

    class Meta:
        model = AnalysisGroup
        fields = ['job_type']
        widgets = {
            'job_type': forms.RadioSelect,
        }

