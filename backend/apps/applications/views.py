from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from typing import cast
from django.db.models import Avg
from .models import Application, TestRun
from .serializers import (
    ApplicationSerializer, ApplicationCreateSerializer,
    TestRunSerializer, TestRunCreateSerializer
)


class ApplicationPagination(PageNumberPagination):
    """Pagination for application list."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET', 'POST'])
def application_list_create(request):
    """
    GET /api/applications - List all applications owned by the current user
    POST /api/applications - Create a new application
    """
    # Check if user is disabled
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'GET':
        # Get only applications owned by the current user
        applications = Application.objects.filter(owner=request.user)  # type: ignore[attr-defined]
        
        # Apply pagination
        paginator = ApplicationPagination()
        page = paginator.paginate_queryset(applications, request)
        
        if page is not None:
            serializer = ApplicationSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = ApplicationCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Save with the current user as owner
            application = serializer.save(owner=request.user)
            # Return full application data
            response_serializer = ApplicationSerializer(application)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def application_detail(request, pk):
    """
    GET /api/applications/<id> - Retrieve application details
    PUT /api/applications/<id> - Update application
    DELETE /api/applications/<id> - Delete application
    """
    # Check if user is disabled
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        application = Application.objects.get(pk=pk, owner=request.user)  # type: ignore[attr-defined]
    except Application.DoesNotExist:  # type: ignore[attr-defined]
        return Response({
            'error': 'Application not found or you do not have permission to access it'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = ApplicationSerializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        serializer = ApplicationCreateSerializer(application, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response_serializer = ApplicationSerializer(application)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        application.delete()
        return Response({
            'message': 'Application deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


# Test Run Views

class TestRunPagination(PageNumberPagination):
    """Pagination for test run list."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET', 'POST'])
def testrun_list_create(request):
    """
    GET /api/test-runs - List all test runs for user's applications
    POST /api/test-runs - Create and start a new test run
    """
    # Check if user is disabled
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'GET':
        # Get test runs for applications owned by the user
        test_runs = TestRun.objects.filter(application__owner=request.user)  # type: ignore[attr-defined]
        
        # Apply pagination
        paginator = TestRunPagination()
        page = paginator.paginate_queryset(test_runs, request)
        
        if page is not None:
            serializer = TestRunSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = TestRunSerializer(test_runs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = TestRunCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Create test run with pending status
            test_run = cast(TestRun, serializer.save(status='pending'))
            
            # Try to execute test run using Celery task
            try:
                from .tasks import execute_test_run_task
                # Avoid direct .id access (Django typing gap under pyright)
                test_run_id = getattr(test_run, "id", None) or getattr(test_run, "pk", None)
                if not isinstance(test_run_id, int):
                    raise ValueError(f"Could not determine test run id (got {test_run_id!r})")
                execute_test_run_task.delay(test_run_id)  # type: ignore[attr-defined]
            except Exception as e:
                # If Celery is not available, log the error but don't fail the request
                # The test run will remain in pending status and can be manually processed
                import logging
                logger = logging.getLogger(__name__)
                test_run_id = getattr(test_run, "id", None) or getattr(test_run, "pk", None)
                logger.warning(f"Could not queue Celery task for test run {test_run_id}: {e}")
                logger.warning("Celery may not be running. Test execution will be delayed.")
            
            # Return the test run
            response_serializer = TestRunSerializer(test_run)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'DELETE'])
def testrun_detail(request, pk):
    """
    GET /api/test-runs/<id> - Retrieve test run details
    DELETE /api/test-runs/<id> - Delete test run
    """
    # Check if user is disabled
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        test_run = TestRun.objects.get(pk=pk, application__owner=request.user)  # type: ignore[attr-defined]
    except TestRun.DoesNotExist:  # type: ignore[attr-defined]
        return Response({
            'error': 'Test run not found or you do not have permission to access it'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = TestRunSerializer(test_run)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'DELETE':
        test_run.delete()
        return Response({
            'message': 'Test run deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def testrun_stats(request):
    """
    GET /api/applications/test-runs/stats/
    Returns aggregated statistics for test runs owned by the user.
    """
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    test_runs = TestRun.objects.filter(application__owner=request.user)  # type: ignore[attr-defined]
    
    total = test_runs.count()
    success = test_runs.filter(status='success').count()
    failed = test_runs.filter(status='failed').count()
    running = test_runs.filter(status='running').count()
    pending = test_runs.filter(status='pending').count()
    
    completed_tests = test_runs.filter(status__in=['success', 'failed'])
    if completed_tests.exists():
        avg_pass_rate = round(completed_tests.aggregate(avg=Avg('pass_rate'))['avg'] or 0)
        avg_fail_rate = round(completed_tests.aggregate(avg=Avg('fail_rate'))['avg'] or 0)
    else:
        avg_pass_rate = 0
        avg_fail_rate = 0
    
    stats = {
        'total': total,
        'success': success,
        'failed': failed,
        'running': running,
        'pending': pending,
        'average_pass_rate': avg_pass_rate,
        'average_fail_rate': avg_fail_rate,
    }
    
    return Response(stats, status=status.HTTP_200_OK)

