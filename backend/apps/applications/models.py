from django.db import models
from django.conf import settings
from .fields import EncryptedCharField, EncryptedURLField


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
    
    # Testing credentials and URLs (encrypted at rest)
    test_username = EncryptedCharField(max_length=255, null=True, blank=True, help_text="Username for automated testing")
    test_password = EncryptedCharField(max_length=255, null=True, blank=True, help_text="Password for automated testing")
    login_url = EncryptedURLField(max_length=500, null=True, blank=True, help_text="Login URL for auth testing")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'applications'
        ordering = ['-created_at']
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'
    
    def __str__(self):
        return f"{self.name} ({self.url})"


class TestRun(models.Model):
    """Model representing a test run for an application."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    
    TEST_TYPE_CHOICES = [
        ('general', 'General (Full Suite)'),
        ('functional', 'Functional'),
        ('regression', 'Regression'),
        ('performance', 'Performance'),
        ('accessibility', 'Accessibility'),
        ('broken_links', 'Broken Links'),
        ('authentication', 'Authentication Flow'),
    ]
    
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='test_runs',
        help_text="Application being tested"
    )
    test_type = models.CharField(max_length=20, choices=TEST_TYPE_CHOICES, help_text="Type of test")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', help_text="Test status")
    pass_rate = models.IntegerField(default=0, help_text="Percentage of tests that passed")  # type: ignore[arg-type]
    fail_rate = models.IntegerField(default=0, help_text="Percentage of tests that failed")  # type: ignore[arg-type]
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Enhanced testing options
    check_broken_links = models.BooleanField(default=False, help_text="Whether to check for broken links")
    check_auth = models.BooleanField(default=False, help_text="Whether to test login functionality")
    
    # Cancellation fields
    cancel_requested = models.BooleanField(default=False, help_text="Whether cancellation was requested")
    cancel_requested_at = models.DateTimeField(null=True, blank=True, help_text="When cancellation was requested")
    canceled_at = models.DateTimeField(null=True, blank=True, help_text="When test was canceled")
    cancel_reason = models.CharField(max_length=255, null=True, blank=True, help_text="Reason for cancellation")
    
    class Meta:
        db_table = 'test_runs'
        ordering = ['-started_at']
        verbose_name = 'Test Run'
        verbose_name_plural = 'Test Runs'
        indexes = [
            models.Index(fields=['application', 'status']),
            models.Index(fields=['application', '-started_at']),
            models.Index(fields=['status', '-started_at']),
        ]
    
    def get_version_number(self) -> int:
        """Calculate version number based on test runs for the same application, ordered by creation date."""
        # Count how many test runs exist for this application that were created before or at the same time
        # This gives us the version number (1-indexed)
        version = TestRun.objects.filter(  # type: ignore[attr-defined]
            application=self.application,
            started_at__lte=self.started_at
        ).count()
        return version
    
    def get_version_name(self) -> str:
        """Get versioned name like 'app-v1', 'app-v2', etc."""
        version = self.get_version_number()
        return f"{self.application.name}-v{version}"
    
    def __str__(self):
        return f"{self.application.name} - {self.test_type} ({self.status})"


class TestRunStepResult(models.Model):
    """Per-step execution status for parallel test runs."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    test_run = models.ForeignKey(
        TestRun,
        on_delete=models.CASCADE,
        related_name='step_results',
        help_text="Parent test run for this step result",
    )
    step_key = models.CharField(max_length=50, help_text="Stable identifier for the step")
    step_label = models.CharField(max_length=100, help_text="Human-readable step label")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    pass_rate = models.IntegerField(default=0)  # type: ignore[arg-type]
    fail_rate = models.IntegerField(default=0)  # type: ignore[arg-type]
    error_message = models.TextField(blank=True, default='')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    details_json = models.JSONField(default=dict, help_text="Raw details for this step")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'test_run_step_results'
        ordering = ['created_at']
        verbose_name = 'Test Run Step Result'
        verbose_name_plural = 'Test Run Step Results'
        unique_together = ('test_run', 'step_key')

    def __str__(self):
        return f"{self.test_run_id}:{self.step_key} ({self.status})"


class Screenshot(models.Model):
    """Model storing screenshots from test runs."""
    
    test_run = models.ForeignKey(
        TestRun,
        on_delete=models.CASCADE,
        related_name='screenshots',
        help_text="Test run this screenshot belongs to"
    )
    image = models.ImageField(
        upload_to='screenshots/',
        help_text="Screenshot image file",
        null=True,
        blank=True
    )
    cloudinary_url = models.URLField(
        max_length=500,
        help_text="Cloudinary URL of the screenshot",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'screenshots'
        ordering = ['-created_at']
        verbose_name = 'Screenshot'
        verbose_name_plural = 'Screenshots'
    
    def __str__(self):
        return f"Screenshot for {self.test_run} at {self.created_at}"


class TestArtifact(models.Model):
    """Model storing test artifacts (videos, traces, before/after screenshots)."""
    
    ARTIFACT_KIND_CHOICES = [
        ('playwright_trace', 'Playwright Trace'),
        ('playwright_video', 'Playwright Video'),
        ('before_step', 'Before Step Screenshot'),
        ('after_step', 'After Step Screenshot'),
    ]
    
    test_run = models.ForeignKey(
        TestRun,
        on_delete=models.CASCADE,
        related_name='artifacts',
        help_text="Test run this artifact belongs to"
    )
    kind = models.CharField(
        max_length=50,
        choices=ARTIFACT_KIND_CHOICES,
        help_text="Type of artifact"
    )
    url = models.URLField(
        max_length=500,
        help_text="Cloudinary URL or local path to the artifact"
    )
    step_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Optional step name (e.g., 'login', 'submit_form')"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'test_artifacts'
        ordering = ['-created_at']
        verbose_name = 'Test Artifact'
        verbose_name_plural = 'Test Artifacts'
    
    def __str__(self):
        return f"{self.kind} for {self.test_run} at {self.created_at}"


class GeneratedTestCase(models.Model):
    """Model storing AI-generated test cases."""
    
    TEST_TYPE_CHOICES = [
        ('functional', 'Functional'),
        ('regression', 'Regression'),
        ('performance', 'Performance'),
        ('accessibility', 'Accessibility'),
        ('broken_links', 'Broken Links'),
        ('authentication', 'Authentication Flow'),
    ]
    
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='generated_test_cases',
        help_text="Application this test case belongs to"
    )
    name = models.CharField(max_length=255, help_text="Name of the test case")
    description = models.TextField(help_text="Description of what this test verifies")
    test_type = models.CharField(max_length=20, choices=TEST_TYPE_CHOICES, help_text="Type of test")
    steps_json = models.JSONField(default=list, help_text="JSON array of test steps")
    expected_results = models.TextField(help_text="Overall expected outcome")
    tags = models.JSONField(default=list, help_text="Tags for categorization")
    estimated_duration = models.CharField(max_length=50, default="5 minutes", help_text="Estimated test duration")
    is_ai_generated = models.BooleanField(default=True, help_text="Whether this was AI-generated")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'generated_test_cases'
        ordering = ['-created_at']
        verbose_name = 'Generated Test Case'
        verbose_name_plural = 'Generated Test Cases'
    
    def __str__(self):
        return f"{self.name} ({self.application.name})"