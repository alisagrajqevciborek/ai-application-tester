from rest_framework import serializers
from .models import Application, TestRun


class ApplicationSerializer(serializers.ModelSerializer):
    """Serializer for Application model."""
    
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    
    class Meta:
        model = Application
        fields = ('id', 'name', 'url', 'owner', 'owner_email', 'created_at', 'updated_at')
        read_only_fields = ('id', 'owner', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        """Create application with the current user as owner."""
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating applications."""
    
    class Meta:
        model = Application
        fields = ('name', 'url')
    
    def validate_url(self, value):
        """Validate that the URL is properly formatted."""
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("URL must start with http:// or https://")
        return value


class TestRunSerializer(serializers.ModelSerializer):
    """Serializer for TestRun model."""
    
    application_name = serializers.CharField(source='application.name', read_only=True)
    application_url = serializers.URLField(source='application.url', read_only=True)
    
    class Meta:
        model = TestRun
        fields = (
            'id', 'application', 'application_name', 'application_url',
            'test_type', 'status', 'pass_rate', 'fail_rate',
            'started_at', 'completed_at'
        )
        read_only_fields = ('id', 'status', 'pass_rate', 'fail_rate', 'started_at', 'completed_at')
    
    def validate_application(self, value):
        """Ensure user owns the application."""
        if value.owner != self.context['request'].user:
            raise serializers.ValidationError("You don't have permission to run tests on this application.")
        return value


class TestRunCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating test runs."""
    
    class Meta:
        model = TestRun
        fields = ('application', 'test_type')
    
    def validate_application(self, value):
        """Ensure user owns the application."""
        if value.owner != self.context['request'].user:
            raise serializers.ValidationError("You don't have permission to run tests on this application.")
        return value
