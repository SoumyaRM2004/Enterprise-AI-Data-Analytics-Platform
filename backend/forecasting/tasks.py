"""
Celery tasks for forecasting and anomaly detection.
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def run_forecast_task(self, forecast_id):
    """Run a forecasting model asynchronously."""
    from .models import ForecastModel
    from .engine import ForecastEngine
    from datasets.models import Dataset

    try:
        forecast = ForecastModel.objects.get(id=forecast_id)
        forecast.status = 'running'
        forecast.save()

        dataset = forecast.dataset
        from analytics.engine import DataProcessor
        processor = DataProcessor(str(dataset.file.path))
        processor.load()

        engine = ForecastEngine(processor.df)
        results = engine.forecast(
            method=forecast.method,
            target_column=forecast.target_column,
            date_column=forecast.date_column if forecast.date_column else None,
            horizon=forecast.horizon,
            parameters=forecast.parameters,
        )

        forecast.results = results.get('metrics', {})
        forecast.historical_data = results.get('historical', {})
        forecast.forecast_data = results.get('forecast', {})
        forecast.metrics = results.get('metrics', {})
        forecast.status = 'completed'
        forecast.completed_at = timezone.now()
        forecast.save()

        logger.info(f"Forecast {forecast.id} completed successfully.")
        return {'status': 'success', 'forecast_id': forecast.id}

    except Exception as exc:
        logger.error(f"Forecast {forecast_id} failed: {exc}")
        try:
            forecast = ForecastModel.objects.get(id=forecast_id)
            forecast.status = 'failed'
            forecast.results = {'error': str(exc)}
            forecast.save()
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=2)
def run_anomaly_detection_task(self, detection_id):
    """Run anomaly detection asynchronously."""
    from .models import AnomalyDetection
    from .engine import ForecastEngine

    try:
        detection = AnomalyDetection.objects.get(id=detection_id)
        detection.status = 'running'
        detection.save()

        dataset = detection.dataset
        from analytics.engine import DataProcessor
        processor = DataProcessor(str(dataset.file.path))
        processor.load()

        engine = ForecastEngine(processor.df)
        results = engine.detect_anomalies(
            column=detection.column,
            method=detection.method,
            parameters=detection.parameters,
        )

        detection.anomalies = results.get('anomalies', [])
        detection.anomaly_count = results.get('anomaly_count', 0)
        detection.total_records = results.get('total_records', 0)
        detection.status = 'completed'
        detection.save()

        logger.info(f"Anomaly detection {detection.id} completed.")
        return {'status': 'success', 'detection_id': detection.id}

    except Exception as exc:
        logger.error(f"Anomaly detection {detection_id} failed: {exc}")
        try:
            detection = AnomalyDetection.objects.get(id=detection_id)
            detection.status = 'failed'
            detection.save()
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=30)
