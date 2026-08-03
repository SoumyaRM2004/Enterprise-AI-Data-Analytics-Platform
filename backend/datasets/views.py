"""
Views for datasets app - upload, manage, and process datasets.
"""

from rest_framework import generics, permissions, status, parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from .models import Project, Dataset, DatasetVersion, CleaningJob
from .serializers import (
    ProjectSerializer, DatasetSerializer, DatasetUploadSerializer,
    DatasetVersionSerializer, CleaningJobSerializer,
)
from accounts.models import AuditLog
from .tasks import process_dataset_task, run_cleaning_job_task


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


class ProjectListCreateView(generics.ListCreateAPIView):
    """List and create projects."""
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user) | Project.objects.filter(
            collaborators=self.request.user
        )

    def perform_create(self, serializer):
        project = serializer.save(owner=self.request.user)
        AuditLog.objects.create(
            user=self.request.user,
            action=AuditLog.ActionType.USER_CHANGE,
            description=f"Created project: {project.name}",
            resource_type='project',
            resource_id=project.id,
        )


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a project."""
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)


class DatasetListView(generics.ListAPIView):
    """List datasets for the current user."""
    serializer_class = DatasetSerializer

    def get_queryset(self):
        qs = Dataset.objects.filter(owner=self.request.user)
        project_id = self.request.query_params.get('project_id')
        if project_id:
            qs = qs.filter(project_id=project_id)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class DatasetUploadView(APIView):
    """Upload a new dataset (CSV/Excel)."""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        serializer = DatasetUploadSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        dataset = serializer.save()

        # Trigger async processing
        dataset.processing_started_at = timezone.now()
        dataset.status = Dataset.Status.PROCESSING
        dataset.save()

        # Launch Celery task in background thread if Celery is running eagerly locally
        from django.conf import settings
        import threading
        import uuid

        task_id = str(uuid.uuid4())
        dataset.celery_task_id = task_id
        dataset.save()

        if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            thread = threading.Thread(
                target=process_dataset_task,
                args=(str(dataset.id),),
                daemon=True
            )
            thread.start()
        else:
            task = process_dataset_task.delay(str(dataset.id))
            dataset.celery_task_id = task.id
            dataset.save()

        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.ActionType.UPLOAD,
            description=f"Uploaded dataset: {dataset.name}",
            resource_type='dataset',
            ip_address=get_client_ip(request),
        )

        return Response(DatasetSerializer(dataset).data, status=status.HTTP_201_CREATED)


class DatasetDetailView(generics.RetrieveDestroyAPIView):
    """Retrieve or delete a dataset."""
    serializer_class = DatasetSerializer

    def get_queryset(self):
        return Dataset.objects.filter(owner=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.ActionType.DELETE,
            description=f"Deleted dataset: {instance.name}",
            resource_type='dataset',
            resource_id=str(instance.id),
        )
        return super().destroy(request, *args, **kwargs)


class DatasetProfileView(APIView):
    """Get detailed data profile for a dataset."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            dataset = Dataset.objects.get(id=pk, owner=request.user)
        except Dataset.DoesNotExist:
            return Response({'error': 'Dataset not found.'}, status=status.HTTP_404_NOT_FOUND)

        if dataset.status != Dataset.Status.READY:
            return Response(
                {'error': 'Dataset is not ready yet. Please wait for processing to complete.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            'name': dataset.name,
            'row_count': dataset.row_count,
            'column_count': dataset.column_count,
            'column_names': dataset.column_names,
            'column_types': dataset.column_types,
            'data_profile': dataset.data_profile,
            'data_quality_score': dataset.data_quality_score,
            'sample_data': dataset.sample_data[:10],
        })


class DatasetVersionsView(generics.ListCreateAPIView):
    """List and create dataset versions."""
    serializer_class = DatasetVersionSerializer

    def get_queryset(self):
        return DatasetVersion.objects.filter(dataset_id=self.kwargs['pk'])

    def perform_create(self, serializer):
        serializer.save(dataset_id=self.kwargs['pk'])


class CleaningJobListView(generics.ListCreateAPIView):
    """List cleaning jobs and create new ones."""
    serializer_class = CleaningJobSerializer

    def get_queryset(self):
        return CleaningJob.objects.filter(dataset_id=self.kwargs['pk'])

    def perform_create(self, serializer):
        job = serializer.save(dataset_id=self.kwargs['pk'])
        # Trigger async cleaning
        task = run_cleaning_job_task.delay(job.id)
        job.celery_task_id = task.id
        job.status = CleaningJob.JobStatus.RUNNING
        job.save()
