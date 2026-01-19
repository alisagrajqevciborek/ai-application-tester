from django.db import models
from django.utils.translation import gettext_lazy as _


class Application(models.Model):
    """Model representing an application to be tested."""

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("Name of the application"),
    )
    url = models.URLField(
        help_text=_("URL of the application"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp when the application was added"),
    )

    class Meta:
        verbose_name = _("Application")
        verbose_name_plural = _("Applications")
        ordering = ["name"]

    def __str__(self):
        return self.name
