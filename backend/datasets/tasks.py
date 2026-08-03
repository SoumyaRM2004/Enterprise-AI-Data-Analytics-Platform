"""
Celery tasks for dataset processing and cleaning.
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_dataset_task(self, dataset_id):
    """Process uploaded dataset: parse, profile, and prepare for analysis."""
    from .models import Dataset
    from analytics.engine import DataProcessor

    try:
        dataset = Dataset.objects.get(id=dataset_id)
        logger.info(f"Processing dataset: {dataset.name}")

        processor = DataProcessor(str(dataset.file.path))
        result = processor.process()

        # Update dataset with profiling results
        dataset.row_count = result.get('row_count', 0)
        dataset.column_count = result.get('column_count', 0)
        dataset.file_type = result.get('file_type', '')
        dataset.column_names = result.get('column_names', [])
        dataset.column_types = result.get('column_types', {})
        dataset.data_profile = result.get('data_profile', {})
        dataset.sample_data = result.get('sample_data', [])
        dataset.data_quality_score = result.get('quality_score', 0.0)
        dataset.status = Dataset.Status.READY
        dataset.processing_completed_at = timezone.now()
        dataset.save()

        logger.info(f"Dataset {dataset.name} processed successfully.")
        return {'status': 'success', 'dataset_id': str(dataset.id)}

    except Exception as exc:
        logger.error(f"Error processing dataset {dataset_id}: {exc}")
        dataset = Dataset.objects.get(id=dataset_id)
        dataset.status = Dataset.Status.ERROR
        dataset.error_message = str(exc)
        dataset.save()
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=2)
def run_cleaning_job_task(self, job_id):
    """Execute a data cleaning job."""
    from .models import CleaningJob, Dataset

    try:
        job = CleaningJob.objects.get(id=job_id)
        job.status = CleaningJob.JobStatus.RUNNING
        job.save()

        dataset = job.dataset
        processor = DataProcessor(str(dataset.file.path))

        # Execute the cleaning operation
        result = processor.clean(
            operation=job.job_type,
            parameters=job.parameters,
        )

        job.rows_affected = result.get('rows_affected', 0)
        job.result_summary = result.get('summary', '')
        job.status = CleaningJob.JobStatus.COMPLETED
        job.completed_at = timezone.now()
        job.save()

        logger.info(f"Cleaning job {job.id} completed: {result.get('summary')}")
        return {'status': 'success', 'job_id': job.id}

    except Exception as exc:
        logger.error(f"Error in cleaning job {job_id}: {exc}")
        job = CleaningJob.objects.get(id=job_id)
        job.status = CleaningJob.JobStatus.FAILED
        job.result_summary = str(exc)
        job.save()
        raise self.retry(exc=exc, countdown=30)


@shared_task
def reprocess_dataset(dataset_id):
    """Reprocess a dataset with updated cleaning."""
    from .models import Dataset

    dataset = Dataset.objects.get(id=dataset_id)
    dataset.status = Dataset.Status.PROCESSING
    dataset.processing_started_at = timezone.now()
    dataset.save()

    result = process_dataset_task.delay(dataset_id)
    return result.id
