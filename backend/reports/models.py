"""
Reports models - PDF reports and scheduled email reports.
"""

from django.db import models
from django.conf import settings


class Report(models.Model):
    """Generated PDF report."""

    class ReportType(models.TextChoices):
        DATASET_ANALYSIS = 'dataset_analysis', 'Dataset Analysis'
        FORECAST = 'forecast', 'Forecast Report'
        ANOMALY = 'anomaly', 'Anomaly Report'
        CUSTOM = 'custom', 'Custom Report'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        GENERATING = 'generating', 'Generating'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports'
    )
    dataset = models.ForeignKey(
        'datasets.Dataset', on_delete=models.CASCADE, related_name='reports', null=True, blank=True
    )
    title = models.CharField(max_length=255)
    report_type = models.CharField(max_length=30, choices=ReportType.choices, default=ReportType.DATASET_ANALYSIS)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    file = models.FileField(upload_to='reports/%Y/%m/', blank=True)
    content = models.JSONField(default=dict, blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.status})"


class ScheduledReport(models.Model):
    """Scheduled report with email delivery."""

    class Frequency(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='scheduled_reports'
    )
    dataset = models.ForeignKey(
        'datasets.Dataset', on_delete=models.CASCADE, related_name='scheduled_reports'
    )
    title = models.CharField(max_length=255)
    report_type = models.CharField(max_length=30, choices=Report.ReportType.choices)
    frequency = models.CharField(max_length=10, choices=Frequency.choices)
    email_recipients = models.JSONField(default=list)  # List of email addresses
    last_sent = models.DateTimeField(null=True, blank=True)
    next_send = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    parameters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.frequency})"
