from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count, Q
from .models import TestRun
from .serializers import TestRunSerializer


class TestRunListCreateView(generics.ListCreateAPIView):
    """
    API view for listing and creating TestRun instances.
    
    GET: Returns a list of all test runs ordered by newest first.
    POST: Creates a new TestRun with default status RUNNING.
    """

    queryset = TestRun.objects.all().order_by("-started_at")
    serializer_class = TestRunSerializer

    def perform_create(self, serializer):
        """Override to set default status to RUNNING on creation."""
        serializer.save(status=TestRun.Status.RUNNING)


class TestRunDetailView(generics.RetrieveAPIView):
    """
    API view for retrieving a single TestRun instance by ID.
    
    GET: Returns details for the specified test run.
    """

    queryset = TestRun.objects.all()
    serializer_class = TestRunSerializer


@api_view(["GET"])
def test_run_stats(request):
    """
    API view for retrieving aggregated test run statistics.
    
    GET /api/test-runs/stats/
    Returns counts of test runs grouped by status for dashboard visualization.
    
    Response format:
    {
        "completed": number,
        "failed": number,
        "running": number
    }
    """
    stats = {
        "completed": TestRun.objects.filter(status=TestRun.Status.COMPLETED).count(),
        "failed": TestRun.objects.filter(status=TestRun.Status.FAILED).count(),
        "running": TestRun.objects.filter(status=TestRun.Status.RUNNING).count(),
    }
    return Response(stats, status=status.HTTP_200_OK)
