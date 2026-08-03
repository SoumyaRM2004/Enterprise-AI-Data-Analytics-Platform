"""
Views for accounts app - authentication and user management.
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from django.contrib.auth import logout

from .serializers import UserSerializer, RegisterSerializer, ChangePasswordSerializer, AuditLogSerializer
from .models import AuditLog

User = get_user_model()


def get_client_ip(request):
    """Get client IP address."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


class LoginView(TokenObtainPairView):
    """JWT login view with audit logging."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            AuditLog.objects.create(
                user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                action=AuditLog.ActionType.LOGIN,
                description=f"User {request.data.get('username')} logged in",
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
        return response


class RegisterView(generics.CreateAPIView):
    """User registration."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        AuditLog.objects.create(
            user=user,
            action=AuditLog.ActionType.USER_CHANGE,
            description=f"New user registered: {user.username}",
        )
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get/update current user profile."""
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """Change user password."""

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': 'Old password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'message': 'Password changed successfully.'})


class LogoutView(APIView):
    """Logout and invalidate token."""

    def post(self, request):
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.ActionType.LOGOUT,
            description=f"User {request.user.username} logged out",
            ip_address=get_client_ip(request),
        )
        return Response({'message': 'Logged out successfully.'})


class UserListView(generics.ListAPIView):
    """List all users (admin only)."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)


class AuditLogListView(generics.ListAPIView):
    """List audit logs with filtering."""
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['action', 'user', 'resource_type']

    def get_queryset(self):
        qs = AuditLog.objects.all()
        action = self.request.query_params.get('action')
        user_id = self.request.query_params.get('user_id')
        if action:
            qs = qs.filter(action=action)
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs[:500]
