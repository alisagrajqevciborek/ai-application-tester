from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from typing import Any, cast
import logging
from .serializers import (
    LoginSerializer, UserSerializer, UserRegistrationSerializer,
    EmailVerificationSerializer, ResendCodeSerializer,
    UserUpdateSerializer, PasswordChangeSerializer
)
from .utils import send_verification_email

User = get_user_model()
logger = logging.getLogger(__name__)


class UserOrIPRateThrottle(SimpleRateThrottle):
    """Throttle by user id when authenticated, otherwise by client IP."""

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = f"user:{request.user.pk}"
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class AuthRegisterRateThrottle(UserOrIPRateThrottle):
    scope = 'auth_register'


class AuthVerifyEmailRateThrottle(UserOrIPRateThrottle):
    scope = 'auth_verify_email'


class AuthResendCodeRateThrottle(UserOrIPRateThrottle):
    scope = 'auth_resend_code'


class AuthLoginRateThrottle(UserOrIPRateThrottle):
    scope = 'auth_login'


class AuthRefreshRateThrottle(UserOrIPRateThrottle):
    scope = 'auth_refresh'


class AuthChangePasswordRateThrottle(UserOrIPRateThrottle):
    scope = 'auth_change_password'


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthRegisterRateThrottle])
def register_view(request):
    """
    POST /api/auth/register
    Register a new user and send verification code.
    """
    try:
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Email sending is handled in the serializer's create method
            # If email fails, user is still created but we should log it
            return Response({
                'message': 'Registration successful. Please check your email for the verification code.',
                'email': user.email if hasattr(user, 'email') else ''  # type: ignore[attr-defined]
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Unhandled error during user registration")
        return Response({
            'error': 'An error occurred during registration. Please try again.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthVerifyEmailRateThrottle])
def verify_email_view(request):
    """
    POST /api/auth/verify-email
    Verify email with code.
    """
    serializer = EmailVerificationSerializer(data=request.data)
    if serializer.is_valid():
        validated_data = serializer.validated_data  # type: ignore[assignment]
        user = validated_data.get('user')  # type: ignore[union-attr]
        code = validated_data.get('code')  # type: ignore[union-attr]
        
        if not user or not code:
            return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        
        if user.verify_code(code):
            # Generate JWT tokens after successful verification
            refresh = RefreshToken.for_user(user)
            user_data = UserSerializer(user).data
            
            return Response({
                'message': 'Email verified successfully',
                'user': user_data,
                'access': str(refresh.access_token),  # type: ignore[attr-defined]
                'refresh': str(refresh),
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Invalid or expired verification code'
            }, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthResendCodeRateThrottle])
def resend_code_view(request):
    """
    POST /api/auth/resend-code
    Resend verification code.
    """
    serializer = ResendCodeSerializer(data=request.data)
    if serializer.is_valid():
        validated_data = serializer.validated_data  # type: ignore[assignment]
        email = validated_data.get('email')  # type: ignore[union-attr]
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.get(email=email)
        typed_user = cast(Any, user)
        
        # Generate new code
        code = typed_user.generate_verification_code()
        send_verification_email(typed_user.email, code)
        
        return Response({
            'message': 'Verification code has been resent to your email.'
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthLoginRateThrottle])
def login_view(request):
    """
    POST /api/auth/login
    Authenticate user and return JWT tokens.
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    validated_data = serializer.validated_data  # type: ignore[assignment]
    email = validated_data.get('email', '')  # type: ignore[union-attr]
    password = validated_data.get('password', '')  # type: ignore[union-attr]
    
    user = authenticate(request, username=email, password=password)
    
    if user is not None:
        typed_user = cast(Any, user)
        # Check if email is verified
        if not typed_user.email_verified:
            return Response({
                'error': 'Please verify your email before logging in. Check your email for the verification code.',
                'email': typed_user.email,
                'requires_verification': True
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if account is disabled
        if typed_user.status == 'disabled':
            return Response({
                'error': 'Your account has been disabled. Please contact support.',
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user).data
        
        return Response({
            'user': user_data,
            'access': str(refresh.access_token),  # type: ignore[attr-defined]
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@throttle_classes([AuthRefreshRateThrottle])
def logout_view(request):
    """
    POST /api/auth/logout
    Logout user by blacklisting the refresh token.
    Always returns 200 — logout is idempotent. A token that is already
    blacklisted (e.g. after token rotation) means the user is already
    logged out, which is the desired end state.
    """
    refresh_token = request.data.get('refresh')
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            # Token already blacklisted or invalid — user is already logged out.
            # Do not raise; just proceed so the client clears its local state.
            logger.debug("Logout called with an already-blacklisted or invalid token — ignoring.")

    return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)


@api_view(['GET', 'PUT'])
def me_view(request):
    """
    GET /api/auth/me - Return current authenticated user information
    PUT /api/auth/me - Update user profile
    """
    if request.method == 'GET':
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Return updated user data
            user_serializer = UserSerializer(request.user)
            return Response({
                'message': 'Profile updated successfully',
                'user': user_serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@throttle_classes([AuthChangePasswordRateThrottle])
def change_password_view(request):
    """
    POST /api/auth/change-password
    Change user password.
    """
    serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user
        validated_data = serializer.validated_data  # type: ignore[assignment]
        new_password = validated_data.get('new_password')  # type: ignore[union-attr]
        if not new_password:
            return Response({'error': 'New password is required'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@throttle_classes([AuthRefreshRateThrottle])
def refresh_token_view(request):
    """
    POST /api/auth/refresh
    Refresh access token using refresh token.
    """
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({
                'error': 'Refresh token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        refresh = RefreshToken(refresh_token)
        return Response({
            'access': str(refresh.access_token),  # type: ignore[attr-defined]
        }, status=status.HTTP_200_OK)
    except Exception:
        return Response({
            'error': 'Invalid or expired refresh token'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    GET /api/auth/health
    Simple health check endpoint.
    """
    return Response({'status': 'ok', 'message': 'Backend is running'}, status=status.HTTP_200_OK)
