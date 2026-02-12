from rest_framework import serializers
from .models import Application, TestRun, Screenshot, TestArtifact, GeneratedTestCase, TestRunStepResult


class ApplicationSerializer(serializers.ModelSerializer):
    """Serializer for Application model."""
    
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    
    class Meta:
        model = Application
        fields = (
            'id', 'name', 'url', 'owner', 'owner_email', 
            'test_username', 'test_password', 'login_url',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'owner', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        """Create application with the current user as owner."""
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating applications."""
    
    class Meta:
        model = Application
        fields = ('name', 'url', 'test_username', 'test_password', 'login_url')
    
    def validate_url(self, value):
        """Validate that the URL is properly formatted."""
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("URL must start with http:// or https://")
        return value


class TestRunSerializer(serializers.ModelSerializer):
    """Serializer for TestRun model."""
    
    application_name = serializers.CharField(source='application.name', read_only=True)
    application_url = serializers.URLField(source='application.url', read_only=True)
    version = serializers.SerializerMethodField()
    version_name = serializers.SerializerMethodField()
    step_results = serializers.SerializerMethodField()
    
    class Meta:
        model = TestRun
        fields = (
            'id', 'application', 'application_name', 'application_url',
            'test_type', 'status', 'pass_rate', 'fail_rate',
            'check_broken_links', 'check_auth',
            'started_at', 'completed_at', 'version', 'version_name', 'step_results'
        )
        read_only_fields = ('id', 'status', 'pass_rate', 'fail_rate', 'started_at', 'completed_at', 'version', 'version_name')
    
    def get_version(self, obj) -> int:
        """Get version number for this test run."""
        return obj.get_version_number()
    
    def get_version_name(self, obj) -> str:
        """Get versioned name like 'app-v1', 'app-v2', etc."""
        return obj.get_version_name()
    
    def validate_application(self, value):
        """Ensure user owns the application."""
        if value.owner != self.context['request'].user:
            raise serializers.ValidationError("You don't have permission to run tests on this application.")
        return value

    def get_step_results(self, obj):
        step_results = obj.step_results.all().order_by('created_at')  # type: ignore[attr-defined]
        return TestRunStepResultSerializer(step_results, many=True).data


class TestRunCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating test runs."""
    
    class Meta:
        model = TestRun
        fields = ('application', 'test_type', 'check_broken_links', 'check_auth')
    
    def validate_application(self, value):
        """Ensure user owns the application."""
        if value.owner != self.context['request'].user:
            raise serializers.ValidationError("You don't have permission to run tests on this application.")
        return value


class TestArtifactSerializer(serializers.ModelSerializer):
    """Serializer for TestArtifact model."""
    
    class Meta:
        model = TestArtifact
        fields = ('id', 'kind', 'url', 'step_name', 'created_at')
        read_only_fields = ('id', 'created_at')


class TestRunStepResultSerializer(serializers.ModelSerializer):
    """Serializer for per-step test execution results."""

    class Meta:
        model = TestRunStepResult
        fields = (
            'id',
            'step_key',
            'step_label',
            'status',
            'pass_rate',
            'fail_rate',
            'error_message',
            'started_at',
            'completed_at',
            'details_json',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class GeneratedTestCaseSerializer(serializers.ModelSerializer):
    """Serializer for GeneratedTestCase model."""
    
    application_name = serializers.CharField(source='application.name', read_only=True)
    application_url = serializers.URLField(source='application.url', read_only=True)
    steps = serializers.JSONField(source='steps_json')
    
    class Meta:
        model = GeneratedTestCase
        fields = (
            'id', 'application', 'application_name', 'application_url',
            'name', 'description', 'test_type', 'steps',
            'expected_results', 'tags', 'estimated_duration',
            'is_ai_generated', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def validate_application(self, value):
        """Ensure user owns the application."""
        request = self.context.get('request')
        if request and value.owner != request.user:
            raise serializers.ValidationError("You don't have permission to access this application.")
        return value


class GeneratedTestCaseCreateSerializer(serializers.Serializer):
    """Serializer for creating a test case via AI generation."""
    
    prompt = serializers.CharField(help_text="Natural language description of what to test")
    application_id = serializers.IntegerField(help_text="ID of the application to test")
    test_type = serializers.ChoiceField(
        choices=['functional', 'regression', 'performance', 'accessibility', 'broken_links', 'authentication'],
        default='functional'
    )
    
    def validate_application_id(self, value):
        """Ensure application exists and user owns it."""
        request = self.context.get('request')
        try:
            application = Application.objects.get(pk=value)  # type: ignore[attr-defined]
            if request and application.owner != request.user:
                raise serializers.ValidationError("You don't have permission to access this application.")
            return value
        except Application.DoesNotExist:  # type: ignore[attr-defined]
            raise serializers.ValidationError("Application not found.")


class TestCaseRefineSerializer(serializers.Serializer):
    """Serializer for refining an existing test case."""
    
    test_case = serializers.JSONField(help_text="Existing test case to refine")
    refinement_prompt = serializers.CharField(help_text="Refinement request")
