from django.db import models
from django.utils.translation import gettext_lazy as _


class Report(models.Model):
    """Model storing test run reports with AI-generated content."""

    test_run = models.OneToOneField(
        "test_runs.TestRun",
        on_delete=models.CASCADE,
        related_name="report",
        help_text=_("The test run associated with this report"),
    )
    summary = models.TextField(
        help_text=_("Brief summary of the test results"),
    )
    detailed_report = models.TextField(
        help_text=_("Detailed report of the test execution"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp when the report was created"),
    )

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report for {self.test_run}"