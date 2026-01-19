from django.db import models
from django.utils.translation import gettext_lazy as _


class TestRun(models.Model):
    """Model representing a test execution run."""

    class TestType(models.TextChoices):
        FULL = "FULL", _("Full")
        UI_UX = "UI_UX", _("UI/UX")
        FUNCTIONAL = "FUNCTIONAL", _("Functional")
        CUSTOM = "CUSTOM", _("Custom")

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        RUNNING = "RUNNING", _("Running")
        COMPLETED = "COMPLETED", _("Completed")
        FAILED = "FAILED", _("Failed")

    application = models.ForeignKey(
        "applications.Application",
        on_delete=models.CASCADE,
        related_name="test_runs",
        help_text=_("The application being tested"),
    )
    test_type = models.CharField(
        max_length=20,
        choices=TestType.choices,
        default=TestType.FULL,
        help_text=_("Type of test to run"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text=_("Current status of the test run"),
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp when the test run started"),
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when the test run completed"),
    )

    class Meta:
        verbose_name = _("Test Run")
        verbose_name_plural = _("Test Runs")
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["application", "-started_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.application} - {self.get_test_type_display()} ({self.get_status_display()})"
