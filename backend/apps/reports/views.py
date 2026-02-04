from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.applications.models import TestRun
from .models import Report
from .serializers import ReportSerializer
from common.jira_service import JiraService
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_detail(request, test_run_id):
    """
    GET /api/reports/{test_run_id}/
    - Returns the report for the given TestRun
    - Returns 404 if no report exists for the TestRun
    - Only accessible by the owner of the test run's application
    """
    # Check if user is disabled
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get the test run and verify ownership
    test_run = get_object_or_404(
        TestRun,
        pk=test_run_id,
        application__owner=request.user
    )
    
    # Get or create report
    report, created = Report.objects.get_or_create(
        test_run=test_run,
        defaults={
            'summary': f'Test run {test_run_id} completed with {test_run.pass_rate}% pass rate.',
            'detailed_report': f'Detailed results for test run {test_run_id}.',
            'issues_json': []
        }
    )
    
    serializer = ReportSerializer(report)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def export_to_jira(request, test_run_id):
    """
    POST /api/reports/{test_run_id}/jira-export/
    - Exports console errors and warnings to Jira as grouped tickets
    - Returns ticket keys and URLs
    - Only accessible by the owner of the test run's application
    """
    # Check if user is disabled
    if request.user.status == 'disabled':
        return Response({
            'error': 'Your account has been disabled. Please contact support.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get the test run and verify ownership
    test_run = get_object_or_404(
        TestRun,
        pk=test_run_id,
        application__owner=request.user
    )
    
    # Get the report
    report = get_object_or_404(Report, test_run=test_run)
    
    # Get console logs
    console_logs = report.console_logs_json or []
    
    # Check if there are any errors or warnings
    errors = [log for log in console_logs if log.get('type') == 'error']
    warnings = [log for log in console_logs if log.get('type') == 'warning']
    
    if not errors and not warnings:
        return Response({
            'error': 'No console errors or warnings found in this test run.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Initialize Jira service
        jira_service = JiraService()
        
        # Format test date
        test_date = test_run.started_at.strftime('%Y-%m-%d %H:%M:%S UTC') if test_run.started_at else 'N/A'
        
        # Export to Jira (screenshots are optional and will be included if available in console logs)
        result = jira_service.export_console_logs_to_jira(
            application_name=test_run.application.name,
            application_url=test_run.application.url,
            test_run_id=test_run_id,
            test_type=test_run.test_type,
            test_date=test_date,
            console_logs=console_logs,
            screenshot_urls=None  # Screenshots are optional and extracted from console logs if available
        )
        
        # Build response
        response_data = {
            'message': 'Successfully exported to Jira',
            'error_ticket': result.get('error_ticket'),
            'warning_ticket': result.get('warning_ticket')
        }
        
        # Add summary
        if result.get('error_ticket'):
            response_data['errors_exported'] = len(errors)
        if result.get('warning_ticket'):
            response_data['warnings_exported'] = len(warnings)
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    except ValueError as e:
        # Missing configuration
        logger.error(f"Jira configuration error: {e}")
        return Response({
            'error': str(e) + ' Please configure Jira settings in your environment variables.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except ImportError as e:
        # Jira library not installed
        logger.error(f"Jira library import error: {e}")
        return Response({
            'error': 'Jira library not installed. Please install it with: pip install jira'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        # Other errors
        logger.error(f"Failed to export to Jira: {e}", exc_info=True)
        return Response({
            'error': f'Failed to export to Jira: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

