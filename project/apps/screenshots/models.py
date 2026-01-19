from django.db import models
from django.utils.translation import gettext_lazy as _


class Screenshot(models.Model):
    """Model storing screenshot URLs from automated tests."""

    test_run = models.ForeignKey(
        "test_runs.TestRun",
        on_delete=models.CASCADE,
        related_name="screenshots",
        help_text=_("The test run this screenshot belongs to"),
    )
    image_url = models.URLField(
        help_text=_("URL to the screenshot image"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp when the screenshot was captured"),
    )

    class Meta:
        verbose_name = _("Screenshot")
        verbose_name_plural = _("Screenshots")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["test_run", "-created_at"]),
        ]

    def __str__(self):
        return f"Screenshot from {self.test_run} at {self.created_at}"