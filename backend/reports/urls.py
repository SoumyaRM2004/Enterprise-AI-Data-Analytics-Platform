from django.urls import path
from .views import (
    ReportListView, ReportCreateView, ReportDetailView, ReportDownloadView,
    ScheduledReportListView, ScheduledReportDetailView,
)

urlpatterns = [
    path('', ReportListView.as_view(), name='report-list'),
    path('<uuid:dataset_id>/generate/', ReportCreateView.as_view(), name='report-generate'),
    path('<int:pk>/', ReportDetailView.as_view(), name='report-detail'),
    path('<int:pk>/download/', ReportDownloadView.as_view(), name='report-download'),
    path('scheduled/', ScheduledReportListView.as_view(), name='scheduled-list'),
    path('scheduled/<int:pk>/', ScheduledReportDetailView.as_view(), name='scheduled-detail'),
]
