"""
Forecasting models - store forecast results and configurations.
"""

from django.db import models
from django.conf import settings


class ForecastModel(models.Model):
    """Store forecasting model configurations and results."""

    class Method(models.TextChoices):
        ARIMA = 'arima', 'ARIMA'
        SARIMAX = 'sarimax', 'SARIMAX'
        PROPHET = 'prophet', 'Prophet'
        HOLT_WINTERS = 'holt_winters', 'Holt-Winters'
        LINEAR_REGRESSION = 'linear_regression', 'Linear Regression'
        EXPONENTIAL_SMOOTHING = 'exp_smoothing', 'Exponential Smoothing'

    dataset = models.ForeignKey(
        'datasets.Dataset', on_delete=models.CASCADE, related_name='forecast_models'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forecast_models'
    )
    method = models.CharField(max_length=30, choices=Method.choices)
    target_column = models.CharField(max_length=255)
    date_column = models.CharField(max_length=255, blank=True)
    horizon = models.IntegerField(default=30)
    parameters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, default='pending')
    results = models.JSONField(default=dict, blank=True)
    historical_data = models.JSONField(default=dict, blank=True)
    forecast_data = models.JSONField(default=dict, blank=True)
    metrics = models.JSONField(default=dict, blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.method} - {self.target_column} ({self.dataset.name})"


class AnomalyDetection(models.Model):
    """Store anomaly detection results."""

    dataset = models.ForeignKey(
        'datasets.Dataset', on_delete=models.CASCADE, related_name='anomaly_detections'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='anomaly_detections'
    )
    method = models.CharField(max_length=50, default='isolation_forest')
    column = models.CharField(max_length=255)
    parameters = models.JSONField(default=dict, blank=True)
    anomalies = models.JSONField(default=list, blank=True)
    anomaly_count = models.IntegerField(default=0)
    total_records = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Anomaly detection on {self.column} ({self.dataset.name})"
