from django.db import models
from django.conf import settings


class Application(models.Model):
    """Model representing a web application to be tested."""
    
    name = models.CharField(max_length=255, help_text="Name of the application")
    url = models.URLField(max_length=500, help_text="URL of the application to test")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications',
        help_text="User who owns this application"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'applications'
        ordering = ['-created_at']
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'
    
    def __str__(self):
        return f"{self.name} ({self.url})"


# Placeholder for future test-related models
# TODO: Add TestRun model when test execution is implemented
# TODO: Add TestReport model when AI report generation is implemented
# TODO: Add Screenshot model when browser automation is added
