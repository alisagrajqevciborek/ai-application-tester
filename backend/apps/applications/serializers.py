from rest_framework import serializers
from .models import Application, TestRun, Screenshot, TestArtifact


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
    
    class Meta:
        model = TestRun
        fields = (
            'id', 'application', 'application_name', 'application_url',
            'test_type', 'status', 'pass_rate', 'fail_rate',
            'check_broken_links', 'check_auth',
            'started_at', 'completed_at', 'version', 'version_name'
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
