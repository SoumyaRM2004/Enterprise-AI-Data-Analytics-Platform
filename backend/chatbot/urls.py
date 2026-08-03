from django.urls import path
from .views import (
    ChatSessionListView, ChatSessionDetailView, ChatSendView, LLMProvidersView,
)

urlpatterns = [
    path('sessions/', ChatSessionListView.as_view(), name='chat-session-list'),
    path('sessions/<int:pk>/', ChatSessionDetailView.as_view(), name='chat-session-detail'),
    path('sessions/<int:pk>/send/', ChatSendView.as_view(), name='chat-send'),
    path('providers/', LLMProvidersView.as_view(), name='llm-providers'),
]
