from django.db import models
from apps.applications.models import TestRun


class Report(models.Model):
    """Model storing test run reports with AI-generated content."""
    
    test_run = models.OneToOneField(
        TestRun,
        on_delete=models.CASCADE,
        related_name='report',
        help_text="The test run associated with this report"
    )
    summary = models.TextField(
        help_text="Brief summary of the test results"
    )
    detailed_report = models.TextField(
        help_text="Detailed report of the test execution"
    )
    issues_json = models.JSONField(
        default=list,
        blank=True,
        help_text="JSON array of issues found during testing"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the report was created"
    )
    
    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'
    
    def __str__(self):
        return f"Report for {self.test_run}"

