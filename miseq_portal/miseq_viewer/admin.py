from django.contrib import admin

from .models import Project, Run, RunInterOpData, Sample, UserProjectRelationship, SampleLogData, SampleAssemblyData, \
    MergedSampleComponentGroup, MergedSampleComponent


class SampleAdmin(admin.ModelAdmin):
    search_fields = ['sample_id']


class SampleAssemblyDataAdmin(admin.ModelAdmin):
    search_fields = ['sample_id__sample_id']


# Register your models here.
admin.site.register(Project)
admin.site.register(Run)
admin.site.register(RunInterOpData)
admin.site.register(Sample, SampleAdmin)
admin.site.register(UserProjectRelationship)
admin.site.register(SampleLogData)
admin.site.register(SampleAssemblyData, SampleAssemblyDataAdmin)
admin.site.register(MergedSampleComponent)
admin.site.register(MergedSampleComponentGroup)
