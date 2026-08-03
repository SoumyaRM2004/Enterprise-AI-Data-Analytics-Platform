"""
Serializers for reports app.
"""

from rest_framework import serializers
from .models import Report, ScheduledReport


class ReportSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    dataset_name = serializers.CharField(source='dataset.name', read_only=True, default=None)

    class Meta:
        model = Report
        fields = '__all__'
        read_only_fields = ['owner', 'status', 'file', 'celery_task_id',
                          'error_message', 'created_at', 'completed_at']


class ScheduledReportSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = ScheduledReport
        fields = '__all__'
        read_only_fields = ['owner', 'last_sent', 'next_send', 'created_at', 'updated_at']


class ScheduledReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledReport
        fields = ['dataset', 'title', 'report_type', 'frequency', 'email_recipients', 'parameters']
        read_only_fields = ['dataset']
