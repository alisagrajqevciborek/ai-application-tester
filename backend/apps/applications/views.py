from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from typing import Any, Dict, cast
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg
from .models import Application, TestRun, GeneratedTestCase
from .serializers import (
    ApplicationSerializer, ApplicationCreateSerializer,
    TestRunSerializer, TestRunCreateSerializer,
    GeneratedTestCaseSerializer, GeneratedTestCaseCreateSerializer, TestCaseRefineSerializer
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
        # Use select_related for FK and prefetch_related for reverse FK to avoid N+1 queries
        # Defer heavy JSON fields for better performance
        test_runs = (
            TestRun.objects  # type: ignore[attr-defined]
            .filter(application__owner=request.user)
            .select_related('application')
            .prefetch_related('step_results')
        )
        
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
        test_run = (
            TestRun.objects  # type: ignore[attr-defined]
            .select_related('application')
            .prefetch_related('step_results')
            .get(pk=pk, application__owner=request.user)
        )
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
    
    # Auto-cleanup stalled tests (e.g., stuck in 'running' for > 1 hour)
    timeout = timezone.now() - timedelta(hours=1)
    stalled_tests = test_runs.filter(status__in=['running', 'pending'], started_at__lt=timeout)
    if stalled_tests.exists():
        stalled_tests.update(status='failed', pass_rate=0, fail_rate=100, completed_at=timezone.now())
    
    total = test_runs.count()
    success = test_runs.filter(status='success').count()
    failed = test_runs.filter(status='failed').count()
    running = test_runs.filter(status='running').count()
    pending = test_runs.filter(status='pending').count()
    
    completed_tests = test_runs.filter(status__in=['success', 'failed'])
    if completed_tests.exists():
        avg_pass_rate = round(completed_tests.aggregate(avg=Avg('pass_rate'))['avg'] or 0)
        avg_fail_rate = 100 - avg_pass_rate
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


@api_view(['GET'])
def testrun_active(request):
    """
    GET /api/applications/test-runs/active/
    Return only running or pending test runs (optimized for polling).
    """
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Only fetch necessary fields and limit results
    test_runs = (
        TestRun.objects  # type: ignore[attr-defined]
        .filter(
            application__owner=request.user,
            status__in=['running', 'pending']
        )
        .only(
            'id', 'application', 'test_type', 'status', 
            'started_at', 'pass_rate', 'fail_rate', 'check_broken_links', 'check_auth'
        )
        .select_related('application')
        .order_by('-started_at')[:20]  # Limit to 20 most recent active tests
    )
    
    serializer = TestRunSerializer(test_runs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def testrun_status(request, pk):
    """
    GET /api/applications/test-runs/<id>/status/
    Lightweight status endpoint for polling (no heavy JSON fields).
    """
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        test_run = (
            TestRun.objects  # type: ignore[attr-defined]
            .only(
                'id', 'status', 'started_at', 'completed_at',
                'pass_rate', 'fail_rate'
            )
            .get(pk=pk, application__owner=request.user)
        )
        
        # Fetch step progress without heavy details_json field
        step_results_manager = getattr(test_run, 'step_results', None)
        if step_results_manager is not None:
            steps = step_results_manager.only(
                'step_key', 'step_label', 'status'
            ).values('step_key', 'step_label', 'status')
        else:
            steps = []

        test_run_id = getattr(test_run, 'id', None) or getattr(test_run, 'pk', None)
        
        return Response({
            'id': test_run_id,
            'status': test_run.status,
            'started_at': test_run.started_at,
            'completed_at': test_run.completed_at,
            'pass_rate': test_run.pass_rate,
            'fail_rate': test_run.fail_rate,
            'steps': list(steps),
        }, status=status.HTTP_200_OK)
        
    except TestRun.DoesNotExist:  # type: ignore[attr-defined]
        return Response({'error': 'Test not found'}, status=status.HTTP_404_NOT_FOUND)


# Test Case Generator Views

@api_view(['POST'])
def generate_test_case(request):
    """
    POST /api/applications/test-cases/generate
    Generate a test case from natural language using AI.
    """
    # Check if user is disabled
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = GeneratedTestCaseCreateSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated_data = cast(Dict[str, Any], serializer.validated_data)
    prompt = str(validated_data.get('prompt', ''))
    application_id = validated_data.get('application_id')
    test_type = str(validated_data.get('test_type', 'functional'))

    if not isinstance(application_id, int):
        return Response({'error': 'Invalid application_id'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        application = Application.objects.get(pk=application_id, owner=request.user)  # type: ignore[attr-defined]
    except Application.DoesNotExist:  # type: ignore[attr-defined]
        return Response({
            'error': 'Application not found or you do not have permission to access it'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Generate test case using AI
    from common.test_case_generator import generate_test_case_from_prompt
    
    test_case_data = generate_test_case_from_prompt(
        user_prompt=prompt,
        application_url=application.url,
        test_type=test_type,
        application_name=application.name
    )
    
    # Add fallback flag for frontend
    test_case_data['fallback'] = test_case_data.get('fallback', False)
    
    # Return the generated test case (not saved yet)
    return Response(test_case_data, status=status.HTTP_200_OK)


@api_view(['POST'])
def refine_test_case(request):
    """
    POST /api/applications/test-cases/refine
    Refine an existing test case based on user feedback.
    """
    # Check if user is disabled
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = TestCaseRefineSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated_data = cast(Dict[str, Any], serializer.validated_data)
    test_case = validated_data.get('test_case', {})
    refinement_prompt = str(validated_data.get('refinement_prompt', ''))
    
    # Refine test case using AI
    from common.test_case_generator import refine_test_case as refine_test_case_func
    
    refined_test_case = refine_test_case_func(
        existing_test_case=test_case,
        refinement_prompt=refinement_prompt
    )
    
    return Response(refined_test_case, status=status.HTTP_200_OK)


@api_view(['POST'])
def save_test_case(request):
    """
    POST /api/applications/test-cases/save
    Save a generated test case to the database.
    """
    # Check if user is disabled
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    application_id = request.data.get('application_id')
    test_case_data = request.data.get('test_case')
    
    if not application_id or not test_case_data:
        return Response({
            'error': 'application_id and test_case are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        application = Application.objects.get(pk=application_id, owner=request.user)  # type: ignore[attr-defined]
    except Application.DoesNotExist:  # type: ignore[attr-defined]
        return Response({
            'error': 'Application not found or you do not have permission to access it'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Create the test case
    generated_test_case = GeneratedTestCase.objects.create(  # type: ignore[attr-defined]
        application=application,
        name=test_case_data.get('name', 'Untitled Test Case'),
        description=test_case_data.get('description', ''),
        test_type=test_case_data.get('test_type', 'functional'),
        steps_json=test_case_data.get('steps', []),
        expected_results=test_case_data.get('expected_results', ''),
        tags=test_case_data.get('tags', []),
        estimated_duration=test_case_data.get('estimated_duration', '5 minutes'),
        is_ai_generated=not test_case_data.get('fallback', False)
    )
    
    serializer = GeneratedTestCaseSerializer(generated_test_case)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def list_test_cases(request, application_id):
    """
    GET /api/applications/<id>/test-cases
    List all saved test cases for an application.
    """
    # Check if user is disabled
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        application = Application.objects.get(pk=application_id, owner=request.user)  # type: ignore[attr-defined]
    except Application.DoesNotExist:  # type: ignore[attr-defined]
        return Response({
            'error': 'Application not found or you do not have permission to access it'
        }, status=status.HTTP_404_NOT_FOUND)
    
    test_cases = GeneratedTestCase.objects.filter(application=application)  # type: ignore[attr-defined]
    serializer = GeneratedTestCaseSerializer(test_cases, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
def delete_test_case(request, pk):
    """
    DELETE /api/applications/test-cases/<id>
    Delete a saved test case.
    """
    # Check if user is disabled
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        test_case = GeneratedTestCase.objects.get(pk=pk, application__owner=request.user)  # type: ignore[attr-defined]
    except GeneratedTestCase.DoesNotExist:  # type: ignore[attr-defined]
        return Response({
            'error': 'Test case not found or you do not have permission to access it'
        }, status=status.HTTP_404_NOT_FOUND)
    
    test_case.delete()
    return Response({
        'message': 'Test case deleted successfully'
    }, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def run_generated_test_case(request, pk):
    """
    POST /api/applications/test-cases/<id>/run
    Run a saved generated test case.
    """
    # Check if user is disabled
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        test_case = GeneratedTestCase.objects.get(pk=pk, application__owner=request.user)  # type: ignore[attr-defined]
    except GeneratedTestCase.DoesNotExist:  # type: ignore[attr-defined]
        return Response({
            'error': 'Test case not found or you do not have permission to access it'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Create a test run for this test case
    test_run = TestRun.objects.create(  # type: ignore[attr-defined]
        application=test_case.application,
        test_type=test_case.test_type,
        status='pending'
    )
    
    # Execute the test run with the generated test case steps
    try:
        from .tasks import execute_generated_test_case_task
        test_run_id = getattr(test_run, "id", None) or getattr(test_run, "pk", None)
        if not isinstance(test_run_id, int):
            raise ValueError(f"Could not determine test run id (got {test_run_id!r})")
        execute_generated_test_case_task.delay(test_run_id, test_case.steps_json)  # type: ignore[attr-defined]
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        test_run_id = getattr(test_run, "id", None) or getattr(test_run, "pk", None)
        logger.warning(f"Could not queue Celery task for test run {test_run_id}: {e}")
        logger.warning("Celery may not be running. Test execution will be delayed.")
    
    # Return the test run
    response_serializer = TestRunSerializer(test_run)
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)

