from django.contrib import admin

from .models import AnalysisSample, AnalysisGroup, \
    SendsketchResult, MobSuiteAnalysisGroup, \
    MobSuiteAnalysisPlasmid, RGIResult, RGIGroupResult, MashResult, \
    ConfindrGroupResult, ConfindrResult, ConfindrResultAssembly, \
    rMLSTResult, StxGroupResult, StxSampleResult, StxGeneResult

# Register your models here.
admin.site.register(AnalysisSample)
admin.site.register(AnalysisGroup)
admin.site.register(SendsketchResult)
admin.site.register(MashResult)
admin.site.register(MobSuiteAnalysisGroup)
admin.site.register(MobSuiteAnalysisPlasmid)
admin.site.register(RGIResult)
admin.site.register(RGIGroupResult)
admin.site.register(ConfindrResult)
admin.site.register(ConfindrGroupResult)
admin.site.register(ConfindrResultAssembly)
admin.site.register(rMLSTResult)
admin.site.register(StxGroupResult)
admin.site.register(StxSampleResult)
admin.site.register(StxGeneResult)

