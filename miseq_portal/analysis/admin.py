from django.contrib import admin

from .models import AnalysisSample, AnalysisGroup

# Register your models here.
admin.site.register(AnalysisSample)
admin.site.register(AnalysisGroup)
