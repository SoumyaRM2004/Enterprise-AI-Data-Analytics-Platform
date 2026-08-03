from django.urls import path
from .views import (
    ProjectListCreateView, ProjectDetailView,
    DatasetListView, DatasetUploadView, DatasetDetailView,
    DatasetProfileView, DatasetVersionsView, CleaningJobListView,
)

urlpatterns = [
    path('projects/', ProjectListCreateView.as_view(), name='project-list'),
    path('projects/<int:pk>/', ProjectDetailView.as_view(), name='project-detail'),
    path('', DatasetListView.as_view(), name='dataset-list'),
    path('upload/', DatasetUploadView.as_view(), name='dataset-upload'),
    path('<uuid:pk>/', DatasetDetailView.as_view(), name='dataset-detail'),
    path('<uuid:pk>/profile/', DatasetProfileView.as_view(), name='dataset-profile'),
    path('<uuid:pk>/versions/', DatasetVersionsView.as_view(), name='dataset-versions'),
    path('<uuid:pk>/cleaning/', CleaningJobListView.as_view(), name='dataset-cleaning'),
]
