from django.contrib import admin

from .models import Project, Run, RunInterOpData, Sample, UserProjectRelationship, SampleLogData, SampleAssemblyData


# Register your models here.
admin.site.register(Project)
admin.site.register(Run)
admin.site.register(RunInterOpData)
admin.site.register(Sample)
admin.site.register(UserProjectRelationship)
admin.site.register(SampleLogData)
admin.site.register(SampleAssemblyData)
