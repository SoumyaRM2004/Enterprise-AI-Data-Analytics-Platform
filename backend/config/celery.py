"""
Celery configuration for analytics-platform.
"""

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('analytics_platform')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Configure beat schedule for periodic tasks
app.conf.beat_schedule = {
    'check-scheduled-reports': {
        'task': 'reports.tasks.check_and_send_scheduled_reports',
        'schedule': 300.0,  # Every 5 minutes
    },
}
