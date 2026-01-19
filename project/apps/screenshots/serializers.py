from rest_framework import serializers
from .models import Screenshot


class ScreenshotSerializer(serializers.ModelSerializer):
    """Serializer for Screenshot model."""

    class Meta:
        model = Screenshot
        fields = [
            "id",
            "test_run",
            "image_url",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
