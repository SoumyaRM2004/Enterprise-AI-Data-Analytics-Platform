from django.urls import path
from .views import (
    ForecastListView, ForecastCreateView, ForecastDetailView,
    AnomalyDetectionListView, AnomalyDetectionCreateView, AnomalyDetectionDetailView,
)

urlpatterns = [
    path('', ForecastListView.as_view(), name='forecast-list'),
    path('<uuid:dataset_id>/create/', ForecastCreateView.as_view(), name='forecast-create'),
    path('<int:pk>/detail/', ForecastDetailView.as_view(), name='forecast-detail'),
    path('<int:pk>/', ForecastDetailView.as_view(), name='forecast-delete'),
    path('anomalies/', AnomalyDetectionListView.as_view(), name='anomaly-list'),
    path('anomalies/<int:pk>/', AnomalyDetectionDetailView.as_view(), name='anomaly-detail'),
    path('<uuid:dataset_id>/anomalies/', AnomalyDetectionCreateView.as_view(), name='anomaly-create'),
]
