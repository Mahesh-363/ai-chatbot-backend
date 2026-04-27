from rest_framework import serializers
from .models import DailyUsageSnapshot


class DailyUsageSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyUsageSnapshot
        fields = "__all__"
