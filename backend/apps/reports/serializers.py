from rest_framework import serializers
from .models import Report


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
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

