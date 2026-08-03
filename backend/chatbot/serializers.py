"""
Serializers for chatbot app.
"""

from rest_framework import serializers
from .models import ChatSession, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = '__all__'
        read_only_fields = ['created_at', 'token_count']


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    dataset_name = serializers.CharField(source='dataset.name', read_only=True, default=None)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ['id', 'owner', 'dataset', 'dataset_name', 'title', 'session_type',
                  'is_active', 'message_count', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        return obj.messages.count()


class ChatSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ['dataset', 'title', 'session_type']


class ChatSendSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)
    message_type = serializers.ChoiceField(
        choices=ChatMessage.MessageType.choices,
        default='text',
    )
