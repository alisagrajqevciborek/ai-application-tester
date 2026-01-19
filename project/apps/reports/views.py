from rest_framework import generics
from .models import Report
from .serializers import ReportSerializer


class ReportDetailView(generics.RetrieveAPIView):
    """
    API view for retrieving a Report linked to a specific TestRun.
    
    GET /api/reports/{test_run_id}/
    - Returns the report for the given TestRun
    - Returns 404 if no report exists for the TestRun
    """

    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    lookup_field = "test_run_id"
    lookup_url_kwarg = "test_run_id"
