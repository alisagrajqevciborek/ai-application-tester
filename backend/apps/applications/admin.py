from django.contrib import admin
from .models import Application, TestRun


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """Admin interface for Application model."""
    
    list_display = ('name', 'url', 'owner', 'created_at')
    list_filter = ('created_at', 'owner')
    search_fields = ('name', 'url', 'owner__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Application Info', {
            'fields': ('name', 'url', 'owner')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(TestRun)
class TestRunAdmin(admin.ModelAdmin):
    """Admin interface for TestRun model."""
    
    list_display = ('application', 'test_type', 'status', 'pass_rate', 'fail_rate', 'started_at', 'completed_at')
    list_filter = ('status', 'test_type', 'started_at')
    search_fields = ('application__name', 'application__url')
    readonly_fields = ('started_at', 'completed_at')
    ordering = ('-started_at',)
    
    fieldsets = (
        ('Test Info', {
            'fields': ('application', 'test_type', 'status')
        }),
        ('Results', {
            'fields': ('pass_rate', 'fail_rate')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at')
        }),
    )
