from django import forms


class DownloadToolForm(forms.Form):
    file_choices = (
        ('Reads', 'Reads'),
        ('Assembly', 'Assembly'),
    )
    #   download_choice = forms.CharField(max_length=50, choices=file_choices, blank=False, default='Assembly')
    #    download_choice = forms.CharField(label='File Types', max_length=100)

    download_choice = forms.MultipleChoiceField(
        required=True,
        widget=forms.CheckboxSelectMultiple,
        choices=file_choices
    )

#    download_choice = forms.CharField(label='File Type to Download?', widget=forms.Select(choices=file_choices))
