"""
Serializers for analytics app.
"""

from rest_framework import serializers
from .models import SavedQuery, AnalysisReport, DashboardWidget


class SavedQuerySerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = SavedQuery
        fields = '__all__'
        read_only_fields = ['owner', 'created_at', 'updated_at']


class AnalysisReportSerializer(serializers.ModelSerializer):
    dataset_name = serializers.CharField(source='dataset.name', read_only=True)

    class Meta:
        model = AnalysisReport
        fields = '__all__'
        read_only_fields = ['created_at']


class DashboardWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidget
        fields = '__all__'
        read_only_fields = ['owner', 'created_at', 'updated_at']
