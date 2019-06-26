from django.contrib import admin

from miseq_portal.miseq_viewer.models import Project, Run, RunInterOpData, Sample, UserProjectRelationship, \
    SampleLogData, SampleAssemblyData, MergedSampleComponentGroup, MergedSampleComponent, RunSamplesheet, \
    SampleSheetSampleData


class SampleAdmin(admin.ModelAdmin):
    search_fields = ['sample_id']


class SampleOneToOneAdmin(admin.ModelAdmin):
    search_fields = ['sample_id__sample_id']


# Register your models here.
admin.site.register(Project)
admin.site.register(Run)
admin.site.register(RunSamplesheet)
admin.site.register(RunInterOpData)
admin.site.register(Sample, SampleAdmin)
admin.site.register(SampleSheetSampleData, SampleOneToOneAdmin)
admin.site.register(UserProjectRelationship)
admin.site.register(SampleLogData, SampleOneToOneAdmin)
admin.site.register(SampleAssemblyData, SampleOneToOneAdmin)
admin.site.register(MergedSampleComponent)
admin.site.register(MergedSampleComponentGroup)
