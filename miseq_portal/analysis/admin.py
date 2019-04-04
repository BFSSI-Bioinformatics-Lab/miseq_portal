from django.contrib import admin

from .models import AnalysisSample, AnalysisGroup, \
    SendsketchResult, MobSuiteAnalysisGroup, \
    MobSuiteAnalysisPlasmid, RGIResult, RGIGroupResult, MashResult

# Register your models here.
admin.site.register(AnalysisSample)
admin.site.register(AnalysisGroup)
admin.site.register(SendsketchResult)
admin.site.register(MashResult)
admin.site.register(MobSuiteAnalysisGroup)
admin.site.register(MobSuiteAnalysisPlasmid)
admin.site.register(RGIResult)
admin.site.register(RGIGroupResult)
