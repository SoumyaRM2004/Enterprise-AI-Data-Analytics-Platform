"""
Celery tasks for report generation and email scheduling.
"""

import logging
import io
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def generate_report_task(self, report_id):
    """Generate a PDF report asynchronously."""
    from .models import Report
    from .generator import PDFReportGenerator
    from datasets.models import Dataset
    from analytics.engine import DataProcessor

    try:
        report = Report.objects.get(id=report_id)
        report.status = 'generating'
        report.save()

        dataset = report.dataset
        processor = DataProcessor(str(dataset.file.path))
        processor.load()

        kpis = processor.get_kpis()
        correlations = processor.get_correlations()
        profile = processor._create_profile()

        generator = PDFReportGenerator()

        if report.report_type == 'dataset_analysis':
            pdf_buffer = generator.generate_dataset_report(
                dataset_name=dataset.name,
                dataset_id=str(dataset.id),
                profile=profile,
                kpis=kpis,
                correlations=correlations,
                sample_data=processor._get_sample_data()[:20],
                charts=[],
            )
        elif report.report_type == 'forecast':
            pdf_buffer = generator.generate_forecast_report(
                dataset_name=dataset.name,
                method=report.content.get('method', 'arima'),
                target_column=report.content.get('target_column', ''),
                horizon=report.content.get('horizon', 30),
                forecast_results=report.content.get('forecast_results', {}),
            )
        else:
            pdf_buffer = generator.generate_dataset_report(
                dataset_name=dataset.name,
                dataset_id=str(dataset.id),
                profile=profile,
                kpis=kpis,
                correlations=correlations,
                sample_data=processor._get_sample_data()[:20],
                charts=[],
            )

        # Save PDF file
        filename = f"report_{dataset.name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        from django.core.files.base import ContentFile
        report.file.save(filename, ContentFile(pdf_buffer.read()))
        report.status = 'completed'
        report.completed_at = timezone.now()
        report.save()

        logger.info(f"Report {report.id} generated successfully.")
        return {'status': 'success', 'report_id': report.id}

    except Exception as exc:
        logger.error(f"Report generation failed: {exc}")
        try:
            report = Report.objects.get(id=report_id)
            report.status = 'failed'
            report.error_message = str(exc)
            report.save()
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=60)


@shared_task
def check_and_send_scheduled_reports():
    """Check for scheduled reports that need to be sent."""
    from .models import ScheduledReport, Report
    from .generator import PDFReportGenerator
    from datasets.models import Dataset
    from analytics.engine import DataProcessor

    now = timezone.now()
    scheduled = ScheduledReport.objects.filter(
        is_active=True,
        next_send__lte=now,
    )

    for sched in scheduled:
        try:
            # Generate report
            dataset = sched.dataset
            processor = DataProcessor(str(dataset.file.path))
            processor.load()

            kpis = processor.get_kpis()
            correlations = processor.get_correlations()
            profile = processor._create_profile()

            generator = PDFReportGenerator()
            pdf_buffer = generator.generate_dataset_report(
                dataset_name=dataset.name,
                dataset_id=str(dataset.id),
                profile=profile,
                kpis=kpis,
                correlations=correlations,
                sample_data=processor._get_sample_data()[:20],
                charts=[],
            )

            # Create report record
            report = Report.objects.create(
                owner=sched.owner,
                dataset=dataset,
                title=sched.title,
                report_type=sched.report_type,
                status='completed',
                completed_at=now,
            )

            from django.core.files.base import ContentFile
            filename = f"scheduled_{sched.title}_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
            report.file.save(filename, ContentFile(pdf_buffer.read()))

            # Send email to recipients
            for recipient in sched.email_recipients:
                try:
                    send_mail(
                        subject=f"Analytics Report: {sched.title}",
                        message=f"Please find attached the scheduled analytics report for {dataset.name}.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[recipient],
                        fail_silently=False,
                    )
                except Exception as e:
                    logger.error(f"Failed to send email to {recipient}: {e}")

            # Update schedule
            sched.last_sent = now
            if sched.frequency == 'daily':
                sched.next_send = now + timedelta(days=1)
            elif sched.frequency == 'weekly':
                sched.next_send = now + timedelta(weeks=1)
            elif sched.frequency == 'monthly':
                sched.next_send = now + timedelta(days=30)
            sched.save()

            logger.info(f"Scheduled report sent: {sched.title}")

        except Exception as e:
            logger.error(f"Failed to process scheduled report {sched.id}: {e}")


@shared_task
def cleanup_old_reports():
    """Clean up old reports and files."""
    from .models import Report
    cutoff = timezone.now() - timedelta(days=90)
    old_reports = Report.objects.filter(created_at__lt=cutoff)
    count = old_reports.count()
    old_reports.delete()
    logger.info(f"Cleaned up {count} old reports.")
