from __future__ import annotations

from rest_framework import serializers


class ApiErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
    code = serializers.CharField()
