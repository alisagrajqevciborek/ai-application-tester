from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'test_run', 'created_at']
    list_filter = ['created_at']
    search_fields = ['test_run__application__name', 'summary']
    readonly_fields = ['created_at']

