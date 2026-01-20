from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
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
            test_run = serializer.save(status='pending')
            
            # Try to execute test run using Celery task
            try:
                from .tasks import execute_test_run_task
                execute_test_run_task.delay(test_run.id)  # type: ignore[attr-defined]
            except Exception as e:
                # If Celery is not available, log the error but don't fail the request
                # The test run will remain in pending status and can be manually processed
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not queue Celery task for test run {test_run.id}: {e}")
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


