"""
Views for forecasting app.
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from .models import ForecastModel, AnomalyDetection
from .serializers import ForecastModelSerializer, ForecastCreateSerializer, AnomalyDetectionSerializer
from .engine import ForecastEngine
from .tasks import run_forecast_task, run_anomaly_detection_task
from datasets.models import Dataset
from accounts.models import AuditLog


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


class ForecastListView(generics.ListAPIView):
    """List all forecast models for the user."""
    serializer_class = ForecastModelSerializer

    def get_queryset(self):
        return ForecastModel.objects.filter(owner=self.request.user)


class ForecastCreateView(APIView):
    """Create and run a forecast."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, dataset_id):
        try:
            dataset = Dataset.objects.get(id=dataset_id, owner=request.user, status='ready')
        except Dataset.DoesNotExist:
            return Response({'error': 'Dataset not found or not ready.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ForecastCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        forecast = ForecastModel.objects.create(
            owner=request.user,
            dataset=dataset,
            status='running',
            **serializer.validated_data,
        )

        # Launch async forecast
        task = run_forecast_task.delay(forecast.id)
        forecast.celery_task_id = task.id
        forecast.save()

        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.ActionType.FORECAST,
            description=f"Started forecast: {forecast.method} on {dataset.name}",
            resource_type='forecast',
            resource_id=forecast.id,
        )

        return Response(ForecastModelSerializer(forecast).data, status=status.HTTP_201_CREATED)


class ForecastDetailView(generics.RetrieveAPIView):
    """Get forecast details and results."""
    serializer_class = ForecastModelSerializer

    def get_queryset(self):
        return ForecastModel.objects.filter(owner=self.request.user)


class AnomalyDetectionListView(generics.ListAPIView):
    """List anomaly detection results."""
    serializer_class = AnomalyDetectionSerializer

    def get_queryset(self):
        return AnomalyDetection.objects.filter(owner=self.request.user)


class AnomalyDetectionCreateView(APIView):
    """Run anomaly detection."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, dataset_id):
        try:
            dataset = Dataset.objects.get(id=dataset_id, owner=request.user, status='ready')
        except Dataset.DoesNotExist:
            return Response({'error': 'Dataset not found.'}, status=status.HTTP_404_NOT_FOUND)

        method = request.data.get('method', 'isolation_forest')
        column = request.data.get('column')
        parameters = request.data.get('parameters', {})

        if not column:
            return Response({'error': 'Column is required.'}, status=status.HTTP_400_BAD_REQUEST)

        detection = AnomalyDetection.objects.create(
            owner=request.user,
            dataset=dataset,
            method=method,
            column=column,
            parameters=parameters,
            status='running',
        )

        task = run_anomaly_detection_task.delay(detection.id)
        detection.celery_task_id = task.id
        detection.save()

        return Response(AnomalyDetectionSerializer(detection).data, status=status.HTTP_201_CREATED)
