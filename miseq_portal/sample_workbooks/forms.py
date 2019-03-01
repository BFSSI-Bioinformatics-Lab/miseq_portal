from django import forms

from miseq_portal.sample_workbooks.models import Workbook


class WorkbookForm(forms.ModelForm):
    class Meta:
        model = Workbook
        exclude = ('user',)
        # fields = "__all__"

    def __init__(self, *args, **kwargs):
        # Automatically grab user and set as attribute of form
        self.user = kwargs.pop('user', False)
        super(WorkbookForm, self).__init__(*args, **kwargs)
