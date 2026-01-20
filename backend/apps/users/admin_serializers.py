from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin to view user information."""
    
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'date_joined', 'status', 'role', 'email_verified')
        read_only_fields = ('id', 'email', 'date_joined', 'email_verified')


class UserStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating user status."""
    
    status = serializers.ChoiceField(choices=['active', 'disabled'])
    
    def validate_status(self, value):
        """Validate status value."""
        if value not in ['active', 'disabled']:
            raise serializers.ValidationError("Status must be either 'active' or 'disabled'.")
        return value

