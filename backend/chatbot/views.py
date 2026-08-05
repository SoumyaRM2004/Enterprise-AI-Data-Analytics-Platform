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
                'name': session.dataset.name,
                'column_names': session.dataset.column_names,
                'column_types': session.dataset.column_types,
                'data_profile': session.dataset.data_profile,
                'sample_data': session.dataset.sample_data,
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
                'options': response.get('options', []),
                'confidence': response.get('confidence', 1.0),
                'reasoning': response.get('reasoning', ''),
            },
            sql_query=response.get('sql_query', ''),
            query_result=response.get('query_result', {}),
            chart_config=response.get('chart_suggestion', {}),
            token_count=response.get('token_count', 0),
        )

        # If SQL or Forecast was generated, execute SQL and process results
        if response.get('type') in ['sql', 'forecast'] and response.get('sql_query') and session.dataset:
            try:
                dataset = session.dataset
                processor = DataProcessor(str(dataset.file.path))
                processor.load()
                executor = SQLExecutor(processor.df)
                result = executor.execute(response['sql_query'])

                if response.get('type') == 'forecast':
                    from forecasting.engine import ForecastEngine

                    # Convert SQL query result rows into a DataFrame for time-series forecasting
                    sql_rows = result.get('data', {}).get('rows', [])
                    sql_cols = result.get('data', {}).get('columns', [])

                    if sql_rows and len(sql_cols) >= 2:
                        res_df = pd.DataFrame(sql_rows)
                        date_col = sql_cols[0]
                        target_col = sql_cols[1]

                        forecast_engine = ForecastEngine(res_df)
                        fc_output = forecast_engine.forecast(
                            method=response.get('recommended_method', 'holt_winters'),
                            target_column=target_col,
                            date_column=date_col,
                            horizon=6,
                        )

                        # Construct combined period | actual | forecast rows
                        combined_rows = []
                        hist_dates = fc_output['historical']['dates']
                        hist_vals = fc_output['historical']['values']
                        for d, v in zip(hist_dates, hist_vals):
                            combined_rows.append({
                                'period': str(d),
                                'actual': round(float(v), 2) if v is not None else None,
                                'forecast': None,
                            })

                        fc_dates = fc_output['forecast']['dates']
                        fc_vals = fc_output['forecast']['values']
                        for d, v in zip(fc_dates, fc_vals):
                            combined_rows.append({
                                'period': str(d),
                                'actual': None,
                                'forecast': round(float(v), 2) if v is not None else None,
                            })

                        nl_explanation = engine.explain_forecast_results(
                            user_message=serializer.validated_data['message'],
                            target_metric=target_col,
                            forecast_res=fc_output,
                        )

                        assistant_msg.query_result = {
                            'data': {
                                'columns': ['period', 'actual', 'forecast'],
                                'rows': combined_rows,
                                'row_count': len(combined_rows),
                            },
                            'total_rows': len(combined_rows),
                            'forecast_data': fc_output,
                        }
                        assistant_msg.chart_config = {'type': 'line', 'x': 'period', 'y': 'forecast'}
                        assistant_msg.message_type = ChatMessage.MessageType.FORECAST
                        assistant_msg.content = nl_explanation
                    else:
                        assistant_msg.content = f"Could not construct time-series aggregation for {response.get('target_metric', 'metric')}."
                else:
                    nl_explanation = engine.explain_sql_results(
                        user_message=serializer.validated_data['message'],
                        sql_query=response['sql_query'],
                        query_result=result,
                    )
                    assistant_msg.query_result = result
                    assistant_msg.message_type = ChatMessage.MessageType.TABLE
                    assistant_msg.content = nl_explanation

                assistant_msg.save()

                AuditLog.objects.create(
                    user=request.user,
                    action=AuditLog.ActionType.QUERY,
                    description=f"{response.get('type', 'query').upper()}: {serializer.validated_data['message'][:100]}",
                    resource_type='dataset',
                    resource_id=str(dataset.id),
                )
            except Exception as e:
                assistant_msg.content = f"Execution failed: {str(e)}"
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
