from django.contrib import admin
from .models import Application, TestRun, Screenshot, TestArtifact


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


@admin.register(Screenshot)
class ScreenshotAdmin(admin.ModelAdmin):
    """Admin interface for Screenshot model."""
    
    list_display = ('test_run', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('test_run__application__name',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(TestArtifact)
class TestArtifactAdmin(admin.ModelAdmin):
    """Admin interface for TestArtifact model."""
    
    list_display = ('test_run', 'kind', 'step_name', 'created_at')
    list_filter = ('kind', 'created_at')
    search_fields = ('test_run__application__name', 'step_name')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
