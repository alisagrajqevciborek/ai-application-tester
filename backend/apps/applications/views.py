from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db import transaction
import random
import time
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
    if request.method == 'GET':
        # Get only applications owned by the current user
        applications = Application.objects.filter(owner=request.user)
        
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
    try:
        application = Application.objects.get(pk=pk, owner=request.user)
    except Application.DoesNotExist:
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
    if request.method == 'GET':
        # Get test runs for applications owned by the user
        test_runs = TestRun.objects.filter(application__owner=request.user)
        
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
            
            # Simulate test execution in background (for demo purposes)
            # In production, this would be handled by Celery or similar
            simulate_test_execution(test_run.id)
            
            # Return the test run
            response_serializer = TestRunSerializer(test_run)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def testrun_detail(request, pk):
    """
    GET /api/test-runs/<id> - Retrieve test run details
    """
    try:
        test_run = TestRun.objects.get(pk=pk, application__owner=request.user)
    except TestRun.DoesNotExist:
        return Response({
            'error': 'Test run not found or you do not have permission to access it'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = TestRunSerializer(test_run)
    return Response(serializer.data, status=status.HTTP_200_OK)


def simulate_test_execution(test_run_id):
    """
    Simulate test execution (mock function for demo).
    In production, this would trigger actual browser automation and AI testing.
    """
    import threading
    
    def run_test():
        time.sleep(1)  # Small delay before starting
        
        try:
            test_run = TestRun.objects.get(pk=test_run_id)
            test_run.status = 'running'
            test_run.save()
            
            # Simulate test execution time (3-5 seconds)
            execution_time = random.uniform(3, 5)
            time.sleep(execution_time)
            
            # Generate random results
            pass_rate = random.randint(60, 100)
            fail_rate = 100 - pass_rate
            status = 'success' if pass_rate >= 70 else 'failed'
            
            # Update test run with results
            with transaction.atomic():
                test_run = TestRun.objects.select_for_update().get(pk=test_run_id)
                test_run.status = status
                test_run.pass_rate = pass_rate
                test_run.fail_rate = fail_rate
                test_run.completed_at = timezone.now()
                test_run.save()
        except TestRun.DoesNotExist:
            pass
        except Exception as e:
            # If something goes wrong, mark as failed
            try:
                test_run = TestRun.objects.get(pk=test_run_id)
                test_run.status = 'failed'
                test_run.completed_at = timezone.now()
                test_run.save()
            except:
                pass
    
    # Run in background thread
    thread = threading.Thread(target=run_test)
    thread.daemon = True
    thread.start()
