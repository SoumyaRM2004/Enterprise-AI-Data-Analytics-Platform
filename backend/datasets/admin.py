from django.contrib import admin
from .models import Project, Dataset, DatasetVersion, CleaningJob


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_active', 'created_at')
    list_filter = ('is_active', 'owner')
    search_fields = ('name', 'description')


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'status', 'row_count', 'column_count', 'created_at')
    list_filter = ('status', 'file_type', 'owner')
    search_fields = ('name',)
    readonly_fields = ('id', 'data_profile', 'sample_data', 'column_names', 'column_types')


@admin.register(DatasetVersion)
class DatasetVersionAdmin(admin.ModelAdmin):
    list_display = ('dataset', 'version_number', 'row_count', 'created_at')
    list_filter = ('dataset',)


@admin.register(CleaningJob)
class CleaningJobAdmin(admin.ModelAdmin):
    list_display = ('dataset', 'job_type', 'status', 'rows_affected', 'created_at')
    list_filter = ('job_type', 'status')
