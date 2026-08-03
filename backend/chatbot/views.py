"""
Views for chatbot app - chat sessions, messages, and AI processing.
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from .models import ChatSession, ChatMessage
from .serializers import (
    ChatSessionSerializer, ChatSessionCreateSerializer, ChatMessageSerializer,
    ChatSendSerializer,
)
from .engine import ChatbotEngine
from datasets.models import Dataset
from analytics.sql_engine import SQLExecutor
from analytics.engine import DataProcessor
from accounts.models import AuditLog


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


class ChatSessionListView(generics.ListCreateAPIView):
    """List and create chat sessions."""
    serializer_class = ChatSessionSerializer

    def get_queryset(self):
        return ChatSession.objects.filter(
            owner=self.request.user, is_active=True
        )

    def create(self, request, *args, **kwargs):
        serializer = ChatSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save(owner=request.user)
        return Response(ChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class ChatSessionDetailView(generics.RetrieveDestroyAPIView):
    """Get or delete a chat session."""
    serializer_class = ChatSessionSerializer

    def get_queryset(self):
        return ChatSession.objects.filter(owner=self.request.user)


class ChatSendView(APIView):
    """Send a message in a chat session and get AI response."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk=None, session_id=None):
        target_id = pk or session_id
        try:
            session = ChatSession.objects.get(
                id=target_id, owner=request.user, is_active=True
            )
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ChatSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save user message
        user_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            message_type=serializer.validated_data['message_type'],
            content=serializer.validated_data['message'],
        )

        # Get chat history
        chat_history = ChatMessageSerializer(
            session.messages.filter(role__in=['user', 'assistant']), many=True
        ).data
        history_for_llm = [{'role': msg['role'], 'content': msg['content']} for msg in chat_history]

        # Get dataset profile if available
        dataset_profile = None
        if session.dataset and session.dataset.status == 'ready':
            dataset_profile = {
                'column_names': session.dataset.column_names,
                'column_types': session.dataset.column_types,
                'data_profile': session.dataset.data_profile,
                'row_count': session.dataset.row_count,
                'column_count': session.dataset.column_count,
            }

        # Process with AI engine
        engine = ChatbotEngine()
        response = engine.process_message(
            message=serializer.validated_data['message'],
            dataset_profile=dataset_profile,
            chat_history=history_for_llm,
        )

        # Save assistant message
        assistant_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            message_type=response.get('type', 'text'),
            content=response.get('content', ''),
            metadata={
                'key_findings': response.get('key_findings', []),
                'follow_up_questions': response.get('follow_up_questions', []),
            },
            sql_query=response.get('sql_query', ''),
            query_result=response.get('query_result', {}),
            chart_config=response.get('chart_suggestion', {}),
            token_count=response.get('token_count', 0),
        )

        # If SQL was generated, execute it
        if response.get('type') == 'sql' and response.get('sql_query') and session.dataset:
            try:
                dataset = session.dataset
                processor = DataProcessor(str(dataset.file.path))
                processor.load()
                executor = SQLExecutor(processor.df)
                result = executor.execute(response['sql_query'])

                assistant_msg.query_result = result
                assistant_msg.message_type = ChatMessage.MessageType.TABLE
                assistant_msg.save()

                AuditLog.objects.create(
                    user=request.user,
                    action=AuditLog.ActionType.QUERY,
                    description=f"NL-to-SQL: {serializer.validated_data['message'][:100]}",
                    resource_type='dataset',
                    resource_id=str(dataset.id),
                )
            except Exception as e:
                assistant_msg.content = f"SQL generated but execution failed: {str(e)}\n\nOriginal SQL: {response.get('sql_query', '')}"
                assistant_msg.sql_query = response.get('sql_query', '')
                assistant_msg.save()

        # Update session
        session.title = session.title or serializer.validated_data['message'][:50]
        session.save()

        return Response({
            'user_message': ChatMessageSerializer(user_msg).data,
            'assistant_message': ChatMessageSerializer(assistant_msg).data,
        })


class LLMProvidersView(APIView):
    """Get available LLM providers."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .llm_provider import LLMProviderFactory
        providers = LLMProviderFactory.get_available_providers()
        current_provider = __import__('django.conf', fromlist=['settings']).settings.LLM_PROVIDER
        return Response({
            'current_provider': current_provider,
            'providers': providers,
        })
