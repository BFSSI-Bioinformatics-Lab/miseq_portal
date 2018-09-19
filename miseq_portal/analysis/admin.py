from django.contrib import admin

from .models import AnalysisSample, AnalysisGroup, \
    SendsketchResult, MobSuiteAnalysisGroup, \
    MobSuiteAnalysisPlasmid

# Register your models here.
admin.site.register(AnalysisSample)
admin.site.register(AnalysisGroup)
admin.site.register(SendsketchResult)
admin.site.register(MobSuiteAnalysisGroup)
admin.site.register(MobSuiteAnalysisPlasmid)
