# Register your models here.
from django.contrib import admin

from miseq_portal.sample_workbooks.models import Workbook, WorkbookSample


class WorkbookAdmin(admin.ModelAdmin):
    search_fields = ['workbook_title']


class WorkbookSampleAdmin(admin.ModelAdmin):
    search_fields = ['sample']


# Register your models here.
admin.site.register(Workbook)
admin.site.register(WorkbookSample)
