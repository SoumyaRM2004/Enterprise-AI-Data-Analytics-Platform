"""
Chatbot models - chat sessions and messages.
"""

from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    """A chat session for AI-powered analytics."""

    class SessionType(models.TextChoices):
        GENERAL = 'general', 'General Query'
        NL_SQL = 'nl_to_sql', 'Natural Language to SQL'
        INSIGHT = 'insight', 'AI Insight'
        FORECAST = 'forecast', 'Forecasting'
        REPORT = 'report', 'Report Generation'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sessions'
    )
    dataset = models.ForeignKey(
        'datasets.Dataset', on_delete=models.CASCADE, related_name='chat_sessions', null=True, blank=True
    )
    title = models.CharField(max_length=255, blank=True)
    session_type = models.CharField(max_length=20, choices=SessionType.choices, default=SessionType.GENERAL)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title or f"Session {self.id} ({self.owner.username})"


class ChatMessage(models.Model):
    """Individual messages in a chat session."""

    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'
        SYSTEM = 'system', 'System'

    class MessageType(models.TextChoices):
        TEXT = 'text', 'Text'
        SQL = 'sql', 'SQL Query'
        CHART = 'chart', 'Chart'
        TABLE = 'table', 'Data Table'
        INSIGHT = 'insight', 'AI Insight'
        FILE = 'file', 'File Link'

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name='messages'
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    message_type = models.CharField(max_length=20, choices=MessageType.choices, default=MessageType.TEXT)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    # For SQL results
    sql_query = models.TextField(blank=True)
    query_result = models.JSONField(default=dict, blank=True)
    chart_config = models.JSONField(default=dict, blank=True)
    # Token usage tracking
    token_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
