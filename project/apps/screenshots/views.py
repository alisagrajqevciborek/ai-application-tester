from rest_framework import generics
from rest_framework.filters import OrderingFilter
from .models import Screenshot
from .serializers import ScreenshotSerializer


class ScreenshotListView(generics.ListAPIView):
    """
    API view for retrieving all screenshots associated with a specific TestRun.
    
    GET /api/screenshots/{test_run_id}/
    - Returns all screenshots for the given TestRun
    - Ordered by creation time (newest first)
    - Returns empty list if no screenshots exist
    """

    serializer_class = ScreenshotSerializer
    filter_backends = [OrderingFilter]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Filter screenshots by test_run_id from URL parameter."""
        test_run_id = self.kwargs.get("test_run_id")
        return Screenshot.objects.filter(test_run_id=test_run_id).order_by("-created_at")
