from django import forms


class RunForm(forms.Form):
    samplesheet = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': False}),
                                  label="Select SampleSheet.csv",
                                  required=True)

    def send_email(self):
        # send email using the self.cleaned_data dictionary
        pass
