from rest_framework import serializers
from .models import TestRun


class TestRunSerializer(serializers.ModelSerializer):
    """Serializer for TestRun model."""

    class Meta:
        model = TestRun
        fields = [
            "id",
            "application",
            "test_type",
            "status",
            "started_at",
            "completed_at",
        ]
        read_only_fields = ["id", "started_at"]
