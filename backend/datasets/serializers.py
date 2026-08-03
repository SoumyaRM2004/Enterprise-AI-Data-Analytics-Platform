"""
Serializers for datasets app.
"""

from rest_framework import serializers
from .models import Project, Dataset, DatasetVersion, CleaningJob


class ProjectSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    dataset_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'owner', 'owner_username',
                  'collaborators', 'is_active', 'dataset_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_dataset_count(self, obj):
        return obj.datasets.filter(status='ready').count()


class DatasetSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True, default=None)

    class Meta:
        model = Dataset
        fields = ['id', 'name', 'file', 'project', 'project_name', 'owner',
                  'owner_username', 'status', 'file_type', 'row_count', 'column_count',
                  'file_size', 'column_names', 'column_types', 'data_profile',
                  'sample_data', 'data_quality_score', 'version', 'created_at',
                  'updated_at', 'processing_completed_at', 'error_message']
        read_only_fields = ['id', 'owner', 'status', 'file_type', 'row_count',
                          'column_count', 'file_size', 'column_names', 'column_types',
                          'data_profile', 'sample_data', 'data_quality_score',
                          'version', 'created_at', 'updated_at']


class DatasetUploadSerializer(serializers.ModelSerializer):
    """Serializer for dataset upload with file validation."""
    project_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Dataset
        fields = ['name', 'file', 'project_id']

    def validate_file(self, value):
        """Validate uploaded file type and size."""
        from django.conf import settings
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 100 * 1024 * 1024)
        allowed = getattr(settings, 'ALLOWED_UPLOAD_EXTENSIONS', ['.csv', '.xlsx', '.xls', '.tsv'])

        if value.size > max_size:
            raise serializers.ValidationError(f"File size exceeds maximum of {max_size / 1024 / 1024}MB.")

        ext = value.name.rsplit('.', 1)[-1].lower()
        if f'.{ext}' not in allowed:
            raise serializers.ValidationError(f"File type .{ext} not supported. Allowed: {', '.join(allowed)}")

        return value

    def create(self, validated_data):
        project_id = validated_data.pop('project_id', None)
        project = None
        if project_id:
            from .models import Project
            project = Project.objects.filter(id=project_id, owner=self.context['request'].user).first()

        dataset = Dataset.objects.create(
            owner=self.context['request'].user,
            project=project,
            **validated_data,
        )
        return dataset


class DatasetVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetVersion
        fields = '__all__'
        read_only_fields = ['dataset', 'created_at']


class CleaningJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = CleaningJob
        fields = '__all__'
        read_only_fields = ['dataset', 'status', 'rows_affected', 'celery_task_id',
                          'result_summary', 'created_at', 'completed_at']
