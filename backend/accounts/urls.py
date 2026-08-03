from django.urls import path
from .views import (
    LoginView, RegisterView, ProfileView, ChangePasswordView,
    LogoutView, UserListView, AuditLogListView,
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='token_obtain_pair'),
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('audit-logs/', AuditLogListView.as_view(), name='audit-logs'),
]
