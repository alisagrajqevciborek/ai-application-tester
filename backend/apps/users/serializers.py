from rest_framework import serializers
from django.contrib.auth import get_user_model
from typing import Any, cast

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model."""
    
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'date_joined', 'status', 'role')
        read_only_fields = ('id', 'date_joined', 'status', 'role')


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ('email', 'password', 'password_confirm', 'first_name', 'last_name')
    
    def validate(self, attrs):
        """Validate that passwords match."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs
    
    def create(self, validated_data):
        """Create a new user with encrypted password and generate verification code."""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        # Generate verification code
        code = cast(Any, user).generate_verification_code()
        # Send verification email
        from .utils import send_verification_email
        email_sent = send_verification_email(user.email, code)
        
        if not email_sent:
            print(f"\n⚠️  WARNING: Failed to send verification email to {user.email}")
            print(f"   Verification code: {code}")
            print(f"   User can use 'resend-code' endpoint to get a new code.\n")
        
        return user


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification."""
    
    email = serializers.EmailField(required=True)
    code = serializers.CharField(max_length=6, required=True)
    
    def validate(self, attrs):
        """Validate email and code."""
        email = attrs.get('email')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})

        typed_user = cast(Any, user)

        if typed_user.email_verified:
            raise serializers.ValidationError({"email": "Email is already verified."})

        if not typed_user.verification_code:
            raise serializers.ValidationError({"code": "No verification code found. Please register again."})
        
        attrs['user'] = user
        return attrs


class ResendCodeSerializer(serializers.Serializer):
    """Serializer for resending verification code."""
    
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Validate that user exists and is not already verified."""
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")

        if cast(Any, user).email_verified:
            raise serializers.ValidationError("Email is already verified.")
        
        return value


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
    
    def validate_email(self, value):
        """Ensure email is unique if changed."""
        user = self.instance
        if user is not None and User.objects.filter(email=value).exclude(pk=getattr(user, 'pk', None)).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for changing password."""
    
    old_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        """Validate that new passwords match."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "New passwords do not match."})
        
        if len(attrs['new_password']) < 8:
            raise serializers.ValidationError({"new_password": "Password must be at least 8 characters long."})
        
        return attrs
    
    def validate_old_password(self, value):
        """Validate that old password is correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value
