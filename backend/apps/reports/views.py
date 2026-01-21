from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.applications.models import TestRun
from .models import Report
from .serializers import ReportSerializer


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

