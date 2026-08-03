"""
URL configuration for analytics-platform project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # App URLs
    path('api/auth/', include('accounts.urls')),
    path('api/datasets/', include('datasets.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/chatbot/', include('chatbot.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/forecasting/', include('forecasting.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
