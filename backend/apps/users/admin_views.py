from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from common.permissions import IsAdmin
from .admin_serializers import AdminUserSerializer, UserStatusUpdateSerializer

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
    return Response({
        'users': serializer.data,
        'count': users.count()
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
    if user.id == request.user.id:
        return Response({
            'error': 'You cannot disable your own account'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = UserStatusUpdateSerializer(data=request.data)
    if serializer.is_valid():
        new_status = serializer.validated_data['status']
        user.status = new_status
        user.save()
        
        return Response({
            'message': f'User status updated to {new_status}',
            'user': AdminUserSerializer(user).data
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

