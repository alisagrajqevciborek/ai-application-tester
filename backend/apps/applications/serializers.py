from rest_framework import serializers
from .models import Application


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
