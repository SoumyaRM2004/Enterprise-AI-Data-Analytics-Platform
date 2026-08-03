"""
Serializers for forecasting app.
"""

from rest_framework import serializers
from .models import ForecastModel, AnomalyDetection


class ForecastModelSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    dataset_name = serializers.CharField(source='dataset.name', read_only=True)

    class Meta:
        model = ForecastModel
        fields = '__all__'
        read_only_fields = ['owner', 'status', 'results', 'historical_data',
                          'forecast_data', 'metrics', 'celery_task_id',
                          'created_at', 'completed_at']


class ForecastCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForecastModel
        fields = ['dataset', 'method', 'target_column', 'date_column', 'horizon', 'parameters']
        read_only_fields = ['dataset']


class AnomalyDetectionSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = AnomalyDetection
        fields = '__all__'
        read_only_fields = ['owner', 'anomalies', 'anomaly_count', 'total_records',
                          'status', 'created_at']
