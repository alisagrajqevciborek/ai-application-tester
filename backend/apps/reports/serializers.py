from rest_framework import serializers
from .models import Report
from apps.applications.models import TestArtifact


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for Report model."""
    
    test_run_id = serializers.IntegerField(source='test_run.id', read_only=True)
    application_name = serializers.CharField(source='test_run.application.name', read_only=True)
    application_url = serializers.CharField(source='test_run.application.url', read_only=True)
    test_type = serializers.CharField(source='test_run.test_type', read_only=True)
    status = serializers.CharField(source='test_run.status', read_only=True)
    pass_rate = serializers.IntegerField(source='test_run.pass_rate', read_only=True)
    fail_rate = serializers.IntegerField(source='test_run.fail_rate', read_only=True)
    started_at = serializers.DateTimeField(source='test_run.started_at', read_only=True)
    completed_at = serializers.DateTimeField(source='test_run.completed_at', read_only=True)
    screenshots = serializers.SerializerMethodField()
    artifacts = serializers.SerializerMethodField()

    def get_screenshots(self, obj):
        """Return screenshot URLs for this report's test run."""
        urls = []
        for s in obj.test_run.screenshots.all().order_by('created_at'):
            if getattr(s, 'cloudinary_url', None):
                urls.append(s.cloudinary_url)
                continue
            image = getattr(s, 'image', None)
            if image and getattr(image, 'url', None):
                urls.append(image.url)
        return urls

    def get_artifacts(self, obj):
        """Return artifacts (videos, traces) for this report's test run."""
        artifacts = []
        for a in obj.test_run.artifacts.all().order_by('created_at'):
            artifacts.append({
                'id': a.id,
                'kind': a.kind,
                'url': a.url,
                'step_name': a.step_name,
                'created_at': a.created_at.isoformat() if a.created_at else None,
            })
        return artifacts
    
    class Meta:
        model = Report
        fields = [
            'id',
            'test_run_id',
            'application_name',
            'application_url',
            'test_type',
            'status',
            'pass_rate',
            'fail_rate',
            'started_at',
            'completed_at',
            'summary',
            'detailed_report',
            'issues_json',
            'console_logs_json',
            'screenshots',
            'artifacts',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

