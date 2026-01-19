from django.contrib import admin
from .models import Application


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
