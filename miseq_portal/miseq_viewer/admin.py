from django.contrib import admin

from .models import Project, Run, Sample, UserProjectRelationship, SampleLogData


# Register your models here.
admin.site.register(Project)
admin.site.register(Run)
admin.site.register(Sample)
admin.site.register(UserProjectRelationship)
admin.site.register(SampleLogData)
