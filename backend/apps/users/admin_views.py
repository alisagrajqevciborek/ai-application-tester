from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from typing import Any, Dict, cast
from common.permissions import IsAdmin
from .admin_serializers import AdminUserSerializer, UserStatusUpdateSerializer
from apps.applications.models import Application, TestRun
from apps.applications.serializers import ApplicationSerializer, TestRunSerializer

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_list_users_view(request):
    """
    GET /api/admin/users
    List all users except the current admin (admin only).
    """
    # Exclude the current admin user from the list
    users = User.objects.exclude(id=request.user.id).order_by('-date_joined')
    serializer = AdminUserSerializer(users, many=True)
    user_data = serializer.data
    return Response({
        'users': user_data,
        'count': len(user_data)  # reuse already-evaluated data — no extra COUNT(*) query
    }, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAdmin])
def admin_toggle_user_status_view(request, user_id):
    """
    PUT /api/admin/users/{user_id}/toggle-status
    Toggle user status between active and disabled (admin only).
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Prevent admin from disabling themselves (shouldn't happen since they're excluded from list, but keep as safety check)
    user_id_value = getattr(user, 'id', None)
    request_user_id = getattr(request.user, 'id', None)
    if user_id_value == request_user_id:
        return Response({
            'error': 'You cannot disable your own account'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = UserStatusUpdateSerializer(data=request.data)
    if serializer.is_valid():
        validated_data = cast(Dict[str, Any], serializer.validated_data)
        new_status = validated_data.get('status')
        if not isinstance(new_status, str):
            return Response({'error': 'Invalid status value'}, status=status.HTTP_400_BAD_REQUEST)
        setattr(user, 'status', new_status)
        user.save()
        
        return Response({
            'message': f'User status updated to {new_status}',
            'user': AdminUserSerializer(user).data
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_user_activity_view(request, user_id):
    """
    GET /api/admin/users/{user_id}/activity
    Return a summary of the user's applications and test runs (admin only).
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Applications owned by the user
    applications = Application.objects.filter(owner=user).order_by('-created_at')

    # Test runs for those applications (with application details)
    test_runs = (
        TestRun.objects
        .filter(application__owner=user)
        .select_related('application')
        .order_by('-started_at')
    )

    app_serializer = ApplicationSerializer(applications, many=True)
    # Use minimal context for serializer; admin is allowed to see these objects
    test_run_serializer = TestRunSerializer(test_runs, many=True)

    return Response({
        'user': AdminUserSerializer(user).data,
        'applications': app_serializer.data,
        'test_runs': test_run_serializer.data,
    }, status=status.HTTP_200_OK)

