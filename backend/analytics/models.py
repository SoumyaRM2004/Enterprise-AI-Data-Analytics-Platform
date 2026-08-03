"""
Analytics models - charts, queries, and saved analyses.
"""

from django.db import models
from django.conf import settings


class SavedQuery(models.Model):
    """Saved SQL queries for reuse."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sql_query = models.TextField()
    dataset = models.ForeignKey(
        'datasets.Dataset', on_delete=models.CASCADE, related_name='saved_queries', null=True
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_queries'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name


class AnalysisReport(models.Model):
    """Auto-generated analysis report for a dataset."""

    dataset = models.ForeignKey(
        'datasets.Dataset', on_delete=models.CASCADE, related_name='analysis_reports'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analysis_reports'
    )
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    kpis = models.JSONField(default=dict, blank=True)
    correlations = models.JSONField(default=dict, blank=True)
    charts_config = models.JSONField(default=list, blank=True)
    ai_insights = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.dataset.name}"


class DashboardWidget(models.Model):
    """Saved dashboard widget configuration."""

    class WidgetType(models.TextChoices):
        BAR_CHART = 'bar', 'Bar Chart'
        LINE_CHART = 'line', 'Line Chart'
        PIE_CHART = 'pie', 'Pie Chart'
        SCATTER_CHART = 'scatter', 'Scatter Chart'
        HEATMAP = 'heatmap', 'Heatmap'
        KPI_CARD = 'kpi', 'KPI Card'
        TABLE = 'table', 'Data Table'
        HISTOGRAM = 'histogram', 'Histogram'

    dataset = models.ForeignKey(
        'datasets.Dataset', on_delete=models.CASCADE, related_name='widgets'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_widgets'
    )
    title = models.CharField(max_length=255)
    widget_type = models.CharField(max_length=20, choices=WidgetType.choices)
    config = models.JSONField(default=dict, blank=True)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=6)
    height = models.IntegerField(default=4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.widget_type})"
