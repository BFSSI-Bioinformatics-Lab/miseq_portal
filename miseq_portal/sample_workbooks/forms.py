from django import forms

from miseq_portal.sample_workbooks.models import Workbook, WorkbookSample


class WorkbookForm(forms.ModelForm):
    class Meta:
        model = Workbook
        exclude = ('user',)
        # fields = "__all__"

    def __init__(self, *args, **kwargs):
        # Automatically grab user and set as attribute of form
        self.user = kwargs.pop('user', False)
        super(WorkbookForm, self).__init__(*args, **kwargs)


class WorkbookSampleForm(forms.ModelForm):
    class Meta:
        model = WorkbookSample
        fields = ('sample_notes',)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', False)
        super(WorkbookSampleForm, self).__init__(*args, **kwargs)
