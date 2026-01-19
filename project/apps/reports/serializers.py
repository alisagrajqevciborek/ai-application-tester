from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for Report model."""

    class Meta:
        model = Report
        fields = [
            "id",
            "test_run",
            "summary",
            "detailed_report",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
