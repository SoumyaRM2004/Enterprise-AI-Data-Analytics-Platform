from django.urls import path
from .views import (
    DashboardView, ChartDataView, SQLQueryView,
    AnalysisReportView, AnalysisReportDetailView, GenerateReportView,
    SavedQueryView, SavedQueryDetailView,
    WidgetView, WidgetDetailView,
)

urlpatterns = [
    path('dashboard/<uuid:dataset_id>/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/<uuid:dataset_id>/chart/', ChartDataView.as_view(), name='chart-data'),
    path('dashboard/<uuid:dataset_id>/query/', SQLQueryView.as_view(), name='sql-query'),
    path('dashboard/<uuid:dataset_id>/generate-report/', GenerateReportView.as_view(), name='generate-report'),
    path('reports/', AnalysisReportView.as_view(), name='report-list'),
    path('reports/<int:pk>/', AnalysisReportDetailView.as_view(), name='report-detail'),
    path('queries/', SavedQueryView.as_view(), name='query-list'),
    path('queries/<int:pk>/', SavedQueryDetailView.as_view(), name='query-detail'),
    path('widgets/', WidgetView.as_view(), name='widget-list'),
    path('widgets/<int:pk>/', WidgetDetailView.as_view(), name='widget-detail'),
]
