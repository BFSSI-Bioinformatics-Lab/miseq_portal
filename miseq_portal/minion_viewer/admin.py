from django.contrib import admin
from miseq_portal.minion_viewer.models import MinIONRun, MinIONRunSamplesheet, MinIONSample

# Register your models here.
admin.site.register(MinIONRun)
admin.site.register(MinIONRunSamplesheet)
admin.site.register(MinIONSample)
