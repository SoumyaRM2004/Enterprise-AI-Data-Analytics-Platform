"""
Views for reports app - generate, download, and schedule reports.
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import FileResponse, HttpResponse
from django.utils import timezone

from .models import Report, ScheduledReport
from .serializers import ReportSerializer, ScheduledReportSerializer, ScheduledReportCreateSerializer
from .generator import PDFReportGenerator
from .tasks import generate_report_task
from datasets.models import Dataset
from analytics.engine import DataProcessor
from accounts.models import AuditLog


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


class ReportListView(generics.ListAPIView):
    """List all reports for the user."""
    serializer_class = ReportSerializer

    def get_queryset(self):
        return Report.objects.filter(owner=self.request.user)


class ReportCreateView(APIView):
    """Generate a new report."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, dataset_id):
        try:
            dataset = Dataset.objects.get(id=dataset_id, owner=request.user, status='ready')
        except Dataset.DoesNotExist:
            return Response({'error': 'Dataset not found or not ready.'}, status=status.HTTP_404_NOT_FOUND)

        report_type = request.data.get('report_type', 'dataset_analysis')

        report = Report.objects.create(
            owner=request.user,
            dataset=dataset,
            title=f"{report_type.replace('_', ' ').title()}: {dataset.name}",
            report_type=report_type,
            status=Report.Status.GENERATING,
        )

        # Launch async generation
        from django.conf import settings
        import threading
        import uuid

        report.celery_task_id = str(uuid.uuid4())
        report.save()

        if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            thread = threading.Thread(target=generate_report_task, args=(report.id,), daemon=True)
            thread.start()
        else:
            task = generate_report_task.delay(report.id)
            report.celery_task_id = task.id
            report.save()

        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.ActionType.REPORT,
            description=f"Generating report: {report.title}",
            resource_type='report',
            resource_id=report.id,
        )

        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


class ReportDetailView(generics.RetrieveDestroyAPIView):
    """Get or delete a report."""
    serializer_class = ReportSerializer

    def get_queryset(self):
        return Report.objects.filter(owner=self.request.user)


class ReportDownloadView(APIView):
    """Download a generated report PDF."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            report = Report.objects.get(id=pk, owner=request.user, status=Report.Status.COMPLETED)
        except Report.DoesNotExist:
            return Response({'error': 'Report not found or not ready.'}, status=status.HTTP_404_NOT_FOUND)

        if report.file:
            response = FileResponse(
                report.file.open('rb'),
                content_type='application/pdf',
                as_attachment=True,
                filename=f"{report.title}.pdf",
            )
            return response
        else:
            # Generate on-the-fly
            return Response({'error': 'Report file not available.'}, status=status.HTTP_404_NOT_FOUND)


class ScheduledReportListView(generics.ListCreateAPIView):
    """List and create scheduled reports."""
    serializer_class = ScheduledReportSerializer

    def get_queryset(self):
        return ScheduledReport.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ScheduledReportCreateSerializer
        return ScheduledReportSerializer

    def perform_create(self, serializer):
        scheduled = serializer.save(owner=self.request.user)
        # Calculate next send time
        self._update_next_send(scheduled)


class ScheduledReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Manage a scheduled report."""
    serializer_class = ScheduledReportSerializer

    def get_queryset(self):
        return ScheduledReport.objects.filter(owner=self.request.user)

    def perform_update(self, serializer):
        scheduled = serializer.save()
        self._update_next_send(scheduled)

    def _update_next_send(self, scheduled):
        now = timezone.now()
        if scheduled.frequency == 'daily':
            scheduled.next_send = now + timezone.timedelta(days=1)
        elif scheduled.frequency == 'weekly':
            scheduled.next_send = now + timezone.timedelta(weeks=1)
        elif scheduled.frequency == 'monthly':
            scheduled.next_send = now + timezone.timedelta(days=30)
        scheduled.save()
