from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from common.permissions import IsAdmin, IsActiveUser
from .serializers import (
    LoginSerializer, UserSerializer, UserRegistrationSerializer,
    EmailVerificationSerializer, ResendCodeSerializer,
    UserUpdateSerializer, PasswordChangeSerializer
)
from .utils import send_verification_email

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
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
                'email': user.email
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import traceback
        print(f"Registration error: {e}")
        print(traceback.format_exc())
        return Response({
            'error': 'An error occurred during registration. Please try again.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email_view(request):
    """
    POST /api/auth/verify-email
    Verify email with code.
    """
    serializer = EmailVerificationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        code = serializer.validated_data['code']
        
        if user.verify_code(code):
            # Generate JWT tokens after successful verification
            refresh = RefreshToken.for_user(user)
            user_data = UserSerializer(user).data
            
            return Response({
                'message': 'Email verified successfully',
                'user': user_data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Invalid or expired verification code'
            }, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_code_view(request):
    """
    POST /api/auth/resend-code
    Resend verification code.
    """
    serializer = ResendCodeSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        
        # Generate new code
        code = user.generate_verification_code()
        send_verification_email(user.email, code)
        
        return Response({
            'message': 'Verification code has been resent to your email.'
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    POST /api/auth/login
    Authenticate user and return JWT tokens.
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    
    user = authenticate(request, username=email, password=password)
    
    if user is not None:
        # Check if email is verified
        if not user.email_verified:
            return Response({
                'error': 'Please verify your email before logging in. Check your email for the verification code.',
                'email': user.email,
                'requires_verification': True
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if account is disabled
        if user.status == 'disabled':
            return Response({
                'error': 'Your account has been disabled. Please contact support.',
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user).data
        
        return Response({
            'user': user_data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def logout_view(request):
    """
    POST /api/auth/logout
    Logout user by blacklisting the refresh token.
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({
            'message': 'Successfully logged out'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'Invalid token or already blacklisted'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
def me_view(request):
    """
    GET /api/auth/me - Return current authenticated user information
    PUT /api/auth/me - Update user profile
    """
    # Check if user is disabled
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
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
def change_password_view(request):
    """
    POST /api/auth/change-password
    Change user password.
    """
    serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
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
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)
    except Exception as e:
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
