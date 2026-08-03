"""
User model with role-based access control.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with role-based access control."""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        ANALYST = 'analyst', 'Analyst'
        VIEWER = 'viewer', 'Viewer'
        DATA_ENGINEER = 'data_engineer', 'Data Engineer'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ANALYST,
    )
    company = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_analyst(self):
        return self.role in [self.Role.ADMIN, self.Role.ANALYST, self.Role.DATA_ENGINEER]


class AuditLog(models.Model):
    """Track all important actions for compliance."""

    class ActionType(models.TextChoices):
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        UPLOAD = 'upload', 'Dataset Upload'
        DELETE = 'delete', 'Dataset Delete'
        QUERY = 'query', 'SQL Query'
        REPORT = 'report', 'Report Generated'
        EXPORT = 'export', 'Data Export'
        USER_CHANGE = 'user_change', 'User Change'
        FORECAST = 'forecast', 'Forecast Generated'
        SCHEDULE = 'schedule', 'Schedule Change'

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField(max_length=50, choices=ActionType.choices)
    description = models.TextField(blank=True)
    resource_type = models.CharField(max_length=50, blank=True)
    resource_id = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user} - {self.action} - {self.created_at}"
