"""
Dataset models - manage uploaded files, projects, and cleaning jobs.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class Project(models.Model):
    """A project groups related datasets and analyses."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects'
    )
    collaborators = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='collaborated_projects', blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name


class Dataset(models.Model):
    """Represents an uploaded dataset with metadata and profiling info."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        READY = 'ready', 'Ready'
        ERROR = 'error', 'Error'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='datasets/%Y/%m/')
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='datasets', null=True, blank=True
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='datasets'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    file_type = models.CharField(max_length=10, blank=True)  # csv, xlsx
    row_count = models.IntegerField(default=0)
    column_count = models.IntegerField(default=0)
    file_size = models.BigIntegerField(default=0)
    column_names = models.JSONField(default=list, blank=True)
    column_types = models.JSONField(default=dict, blank=True)
    data_profile = models.JSONField(default=dict, blank=True)
    sample_data = models.JSONField(default=list, blank=True)
    data_quality_score = models.FloatField(default=0.0)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.id})"

    @property
    def is_ready(self):
        return self.status == self.Status.READY


class DatasetVersion(models.Model):
    """Track versions of datasets after cleaning/modification."""

    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name='versions'
    )
    version_number = models.IntegerField()
    description = models.TextField(blank=True)
    changes = models.JSONField(default=dict, blank=True)
    row_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        unique_together = ['dataset', 'version_number']

    def __str__(self):
        return f"{self.dataset.name} v{self.version_number}"


class CleaningJob(models.Model):
    """Track data cleaning operations."""

    class JobStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    class CleanType(models.TextChoices):
        REMOVE_DUPLICATES = 'remove_duplicates', 'Remove Duplicates'
        FILL_NULLS = 'fill_nulls', 'Fill Null Values'
        REMOVE_NULLS = 'remove_nulls', 'Remove Null Rows'
        STANDARDIZE = 'standardize', 'Standardize Values'
        TYPE_CAST = 'type_cast', 'Type Conversion'
        OUTLIER_REMOVAL = 'outlier_removal', 'Outlier Removal'
        AUTO_CLEAN = 'auto_clean', 'Automatic Cleaning'

    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name='cleaning_jobs'
    )
    job_type = models.CharField(max_length=30, choices=CleanType.choices)
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.PENDING)
    parameters = models.JSONField(default=dict, blank=True)
    rows_affected = models.IntegerField(default=0)
    celery_task_id = models.CharField(max_length=255, blank=True)
    result_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.job_type} on {self.dataset.name} ({self.status})"
