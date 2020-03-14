from django import forms
from django.http import HttpResponseRedirect
from django.shortcuts import render


class DownloadToolForm(forms.Form):
    file_choices = (
        ('Reads', 'Reads'),
        ('Assembly', 'Assembly'),
    )
    #   download_choice = forms.CharField(max_length=50, choices=file_choices, blank=False, default='Assembly')
    #    download_choice = forms.CharField(label='File Types', max_length=100)

# mutliple choice no submit button
#   download_choice = forms.MultipleChoiceField(
#        required=True,
#        widget=forms.CheckboxSelectMultiple,
#        choices=file_choices
#    )

  # drop down dox
  #  download_choice = forms.CharField(label='File Type to Download?', widget=forms.Select(choices=file_choices))


    download_choice = forms.ChoiceField(choices=file_choices, widget= forms.RadioSelect)


    def pick_file_type(request):
        submitted = False
        if request.method == "POST":
            form = DownloadToolForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                return HttpResponseRedirect('sample_downloader/receive/')
        return render(request, 'sample_downloader/receive/', {'form': form, 'submitted': submitted})
