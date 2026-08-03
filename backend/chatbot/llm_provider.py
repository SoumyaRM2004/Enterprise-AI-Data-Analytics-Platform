"""
Configurable LLM provider interface.
Supports OpenAI, Gemini, Ollama, OpenRouter, and OpenAI-compatible endpoints.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Dict[str, Any]:
        """Generate a response from the LLM."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str, model: str = 'gpt-4o-mini', base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Dict[str, Any]:
        try:
            import openai
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url or 'https://api.openai.com/v1',
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=2048,
            )

            return {
                'content': response.choices[0].message.content,
                'model': self.model,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens,
                },
            }
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {'content': f"Error: {str(e)}", 'error': str(e)}


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    def __init__(self, api_key: str, model: str = 'gemini-2.0-flash'):
        self.api_key = api_key
        self.model = model

    def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Dict[str, Any]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)

            model = genai.GenerativeModel(self.model)

            # Convert messages to Gemini format
            contents = []
            for msg in messages:
                if msg['role'] == 'system':
                    contents.append({'role': 'user', 'parts': [msg['content']]})
                    contents.append({'role': 'model', 'parts': ['Understood. I will follow these instructions.']})
                else:
                    contents.append({'role': msg['role'], 'parts': [msg['content']]})

            response = model.generate_content(
                contents,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=2048,
                )
            )

            return {
                'content': response.text,
                'model': self.model,
                'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
            }
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return {'content': f"Error: {str(e)}", 'error': str(e)}


class OllamaProvider(LLMProvider):
    """Ollama local model provider."""

    def __init__(self, base_url: str = 'http://localhost:11434', model: str = 'llama3'):
        self.base_url = base_url
        self.model = model

    def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Dict[str, Any]:
        try:
            import requests

            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    'model': self.model,
                    'messages': messages,
                    'options': {'temperature': temperature},
                    'stream': False,
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()

            return {
                'content': data.get('message', {}).get('content', ''),
                'model': self.model,
                'usage': data.get('eval_count', {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}),
            }
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return {'content': f"Error: {str(e)}", 'error': str(e)}


class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider."""

    def __init__(self, api_key: str, model: str = 'openai/gpt-4o-mini'):
        self.api_key = api_key
        self.model = model
        self.base_url = 'https://openrouter.ai/api/v1'

    def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Dict[str, Any]:
        try:
            import requests

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    'model': self.model,
                    'messages': messages,
                    'temperature': temperature,
                    'max_tokens': 2048,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            return {
                'content': data['choices'][0]['message']['content'],
                'model': data.get('model', self.model),
                'usage': data.get('usage', {}),
            }
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            return {'content': f"Error: {str(e)}", 'error': str(e)}


class GroqProvider(LLMProvider):
    """Groq API provider (Free fast Llama 3 models)."""

    def __init__(self, api_key: str, model: str = 'llama-3.3-70b-versatile'):
        self.api_key = api_key
        self.model = model or 'llama-3.3-70b-versatile'

    def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Dict[str, Any]:
        try:
            import requests

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }

            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json={
                    'model': self.model,
                    'messages': messages,
                    'temperature': temperature,
                    'max_tokens': 2048,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            return {
                'content': data['choices'][0]['message']['content'],
                'model': data.get('model', self.model),
                'usage': data.get('usage', {}),
            }
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return {'content': f"Error: {str(e)}", 'error': str(e)}


class LLMProviderFactory:
    """Factory to create the appropriate LLM provider based on configuration."""

    PROVIDERS = {
        'openai': OpenAIProvider,
        'gemini': GeminiProvider,
        'groq': GroqProvider,
        'ollama': OllamaProvider,
        'openrouter': OpenRouterProvider,
        'openai_compatible': OpenAIProvider,
    }

    @classmethod
    def create(cls, provider_name: Optional[str] = None) -> LLMProvider:
        """Create an LLM provider instance based on settings."""
        provider_name = provider_name or getattr(settings, 'LLM_PROVIDER', 'openai_compatible')

        if provider_name == 'openai':
            return OpenAIProvider(
                api_key=getattr(settings, 'OPENAI_API_KEY', ''),
                model=getattr(settings, 'LLM_MODEL_NAME', 'gpt-4o-mini'),
            )
        elif provider_name == 'gemini':
            return GeminiProvider(
                api_key=getattr(settings, 'GEMINI_API_KEY', ''),
                model=getattr(settings, 'LLM_MODEL_NAME', 'gemini-2.0-flash') or 'gemini-2.0-flash',
            )
        elif provider_name == 'groq':
            return GroqProvider(
                api_key=getattr(settings, 'GROQ_API_KEY', ''),
                model=getattr(settings, 'LLM_MODEL_NAME', 'llama-3.3-70b-versatile') or 'llama-3.3-70b-versatile',
            )
        elif provider_name == 'ollama':
            return OllamaProvider(
                base_url=getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434'),
                model=getattr(settings, 'LLM_MODEL_NAME', 'llama3') or 'llama3',
            )
        elif provider_name == 'openrouter':
            return OpenRouterProvider(
                api_key=getattr(settings, 'OPENAI_API_KEY', ''),
                model=getattr(settings, 'LLM_MODEL_NAME', 'google/gemma-2-9b-it:free') or 'google/gemma-2-9b-it:free',
            )
        elif provider_name == 'openai_compatible':
            return OpenAIProvider(
                api_key=getattr(settings, 'OPENAI_API_KEY', 'dummy-key') or 'dummy-key',
                model=getattr(settings, 'LLM_MODEL_NAME', 'gpt-4o-mini') or 'gpt-4o-mini',
                base_url=getattr(settings, 'OPENAI_API_BASE', None) or None,
            )
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}. Supported: {list(cls.PROVIDERS.keys())}")

    @classmethod
    def get_available_providers(cls) -> List[Dict[str, str]]:
        """Get list of available providers."""
        available = []
        for name, provider_class in cls.PROVIDERS.items():
            available.append({
                'name': name,
                'display_name': name.replace('_', ' ').title(),
                'available': cls._check_provider_available(name),
            })
        return available

    @classmethod
    def _check_provider_available(cls, provider_name: str) -> bool:
        """Check if a provider has the required credentials."""
        if provider_name == 'openai':
            return bool(getattr(settings, 'OPENAI_API_KEY', ''))
        elif provider_name == 'gemini':
            return bool(getattr(settings, 'GEMINI_API_KEY', ''))
        elif provider_name == 'groq':
            return bool(getattr(settings, 'GROQ_API_KEY', ''))
        elif provider_name == 'ollama':
            return True
        elif provider_name == 'openrouter':
            return bool(getattr(settings, 'OPENAI_API_KEY', ''))
        elif provider_name == 'openai_compatible':
            return bool(getattr(settings, 'OPENAI_API_BASE', ''))
        return False
