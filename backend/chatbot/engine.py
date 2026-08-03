"""
Chatbot engine - handles NL-to-SQL, AI insights, and conversational responses.
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from django.conf import settings

from .llm_provider import LLMProviderFactory
from analytics.engine import DataProcessor

logger = logging.getLogger(__name__)


class ChatbotEngine:
    """Main chatbot engine with NL-to-SQL and AI insights."""

    SYSTEM_PROMPT = """You are an expert data analytics AI assistant. You help users analyze their data,
generate insights, create visualizations, and answer questions about their datasets.

When users ask questions about data:
1. If they want to query data, generate a SQL query
2. If they want insights, analyze the data profile
3. If they want visualizations, suggest chart types
4. Always explain your findings in plain language

Your response format should be a JSON object with:
{
    "type": "text" | "sql" | "chart" | "insight" | "forecast",
    "content": "your response text",
    "sql_query": "SQL query if type is sql",
    "chart_suggestion": {"type": "chart_type", "x": "column", "y": "column"},
    "follow_up_questions": ["question1", "question2"]
}

Be helpful, concise, and accurate. Use the dataset schema to inform your answers."""

    def __init__(self):
        self.llm = LLMProviderFactory.create()

    def process_message(
        self,
        message: str,
        dataset_profile: Optional[Dict] = None,
        chat_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Process a user message and generate a response."""

        if not chat_history:
            chat_history = []

        # Build context with dataset schema
        schema_context = self._build_schema_context(dataset_profile)

        # Classify the user's intent
        intent = self._classify_intent(message, dataset_profile)

        if intent == 'sql':
            return self._handle_nl_to_sql(message, schema_context, chat_history)
        elif intent == 'insight':
            return self._handle_insight_request(message, schema_context, dataset_profile, chat_history)
        elif intent == 'chart':
            return self._handle_chart_request(message, schema_context, dataset_profile, chat_history)
        elif intent == 'forecast':
            return self._handle_forecast_request(message, schema_context, dataset_profile, chat_history)
        else:
            return self._handle_general_query(message, schema_context, chat_history)

    def _classify_intent(self, message: str, profile: Optional[Dict] = None) -> str:
        """Classify user message intent."""
        message_lower = message.lower()

        # SQL intent patterns
        sql_patterns = [
            'show', 'find', 'get', 'list', 'filter', 'count', 'how many',
            'which', 'who', 'select', 'where', 'group by', 'average',
            'total', 'sum', 'max', 'min', 'top', 'bottom', 'compare',
            'between', 'greater than', 'less than', 'equal to',
        ]

        # Chart intent patterns
        chart_patterns = [
            'chart', 'graph', 'plot', 'visualize', 'visualization',
            'bar chart', 'line chart', 'pie chart', 'scatter',
        ]

        # Forecast intent patterns
        forecast_patterns = [
            'predict', 'forecast', 'future', 'next month', 'next year',
            'trend', 'projection', 'estimate',
        ]

        # Insight intent patterns
        insight_patterns = [
            'insight', 'analyze', 'analysis', 'pattern', 'correlation',
            'relationship', 'anomaly', 'unusual', 'outlier',
            'recommend', 'suggest', 'improve', 'optimize',
            'why did', 'reason', 'cause', 'explain',
            'summary', 'overview', 'report',
        ]

        if any(p in message_lower for p in forecast_patterns):
            return 'forecast'
        elif any(p in message_lower for p in chart_patterns):
            return 'chart'
        elif any(p in message_lower for p in insight_patterns):
            return 'insight'
        elif any(p in message_lower for p in sql_patterns):
            return 'sql'
        else:
            return 'sql'  # Default to SQL for data questions

    def _handle_nl_to_sql(
        self, message: str, schema_context: str, chat_history: List[Dict]
    ) -> Dict[str, Any]:
        """Handle natural language to SQL conversion."""
        prompt = f"""{self.SYSTEM_PROMPT}

Dataset Schema:
{schema_context}

User Question: {message}

Based on the question, generate a SQL query that would answer it.
The data is in a pandas DataFrame context, so use standard SQL syntax.

Respond with JSON:
{{"type": "sql", "content": "explanation", "sql_query": "SELECT ..."}}"""

        messages = [{'role': 'system', 'content': prompt}]
        for msg in chat_history[-settings.CHAT_MAX_CONTEXT_MESSAGES:]:
            messages.append({'role': msg['role'], 'content': msg['content']})

        result = self.llm.generate(messages)

        # Parse response
        try:
            response_data = self._parse_response(result['content'])
            if response_data.get('type') == 'sql' and response_data.get('sql_query'):
                # Validate and sanitize the SQL
                sql = response_data['sql_query']
                validated_sql = self._validate_sql(sql)
                response_data['sql_query'] = validated_sql
                return response_data
        except Exception:
            pass

        # Fallback: try to extract SQL from the response
        return self._extract_sql_from_text(result['content'])

    def _handle_insight_request(
        self, message: str, schema_context: str, profile: Dict, chat_history: List[Dict]
    ) -> Dict[str, Any]:
        """Handle AI insight requests."""
        # Include data statistics in the prompt
        stats = self._get_data_statistics(profile)

        prompt = f"""{self.SYSTEM_PROMPT}

Dataset Schema:
{schema_context}

Data Statistics:
{stats}

User Request: {message}

Provide a detailed analysis and insights based on the data.
Respond with JSON:
{{"type": "insight", "content": "detailed insight text", "key_findings": ["finding1", "finding2"]}}"""

        messages = [{'role': 'system', 'content': prompt}]
        for msg in chat_history[-settings.CHAT_MAX_CONTEXT_MESSAGES:]:
            messages.append({'role': msg['role'], 'content': msg['content']})

        result = self.llm.generate(messages)

        try:
            response_data = self._parse_response(result['content'])
            if response_data.get('type') == 'insight':
                return response_data
        except Exception:
            pass

        return {
            'type': 'insight',
            'content': result['content'],
            'key_findings': [],
        }

    def _handle_chart_request(
        self, message: str, schema_context: str, profile: Dict, chat_history: List[Dict]
    ) -> Dict[str, Any]:
        """Handle chart/visualization requests."""
        prompt = f"""{self.SYSTEM_PROMPT}

Dataset Schema:
{schema_context}

User Request: {message}

Suggest the best chart type and configuration for visualizing this data.
Respond with JSON:
{{"type": "chart", "content": "explanation", "chart_suggestion": {{"type": "bar/line/pie/scatter", "x": "column_name", "y": "column_name"}}}}"""

        messages = [{'role': 'system', 'content': prompt}]
        for msg in chat_history[-settings.CHAT_MAX_CONTEXT_MESSAGES:]:
            messages.append({'role': msg['role'], 'content': msg['content']})

        result = self.llm.generate(messages)

        try:
            response_data = self._parse_response(result['content'])
            if response_data.get('type') == 'chart':
                return response_data
        except Exception:
            pass

        return {
            'type': 'chart',
            'content': result['content'],
            'chart_suggestion': {'type': 'bar', 'x': '', 'y': ''},
        }

    def _handle_forecast_request(
        self, message: str, schema_context: str, profile: Dict, chat_history: List[Dict]
    ) -> Dict[str, Any]:
        """Handle forecasting requests."""
        prompt = f"""{self.SYSTEM_PROMPT}

Dataset Schema:
{schema_context}

User Request: {message}

Provide forecasting guidance.
Respond with JSON:
{{"type": "forecast", "content": "forecasting advice", "recommended_method": "arima/sarimax/holt_winters", "suggested_columns": {{"target": "col", "date": "col"}}, "suggested_horizon": 30}}"""

        messages = [{'role': 'system', 'content': prompt}]
        for msg in chat_history[-settings.CHAT_MAX_CONTEXT_MESSAGES:]:
            messages.append({'role': msg['role'], 'content': msg['content']})

        result = self.llm.generate(messages)

        try:
            response_data = self._parse_response(result['content'])
            if response_data.get('type') == 'forecast':
                return response_data
        except Exception:
            pass

        return {
            'type': 'forecast',
            'content': result['content'],
            'recommended_method': 'arima',
        }

    def _handle_general_query(
        self, message: str, schema_context: str, chat_history: List[Dict]
    ) -> Dict[str, Any]:
        """Handle general queries."""
        prompt = f"""{self.SYSTEM_PROMPT}

Dataset Schema:
{schema_context}

User Message: {message}

Respond helpfully about the dataset and what analyses are possible."""

        messages = [{'role': 'system', 'content': prompt}]
        for msg in chat_history[-settings.CHAT_MAX_CONTEXT_MESSAGES:]:
            messages.append({'role': msg['role'], 'content': msg['content']})

        result = self.llm.generate(messages)

        return {
            'type': 'text',
            'content': result['content'],
        }

    def _build_schema_context(self, profile: Optional[Dict]) -> str:
        """Build a schema context string from dataset profile."""
        if not profile:
            return "No dataset schema available."

        lines = []
        if profile.get('column_names'):
            lines.append("Columns:")
            for col in profile['column_names']:
                col_type = profile.get('column_types', {}).get(col, 'unknown')
                col_info = profile.get('data_profile', {}).get(col, {})
                lines.append(f"  - {col}: {col_type} (null: {col_info.get('null_percent', 0)}%, unique: {col_info.get('unique_count', 0)})")

        if profile.get('data_profile'):
            lines.append("\nColumn Statistics:")
            for col, info in list(profile['data_profile'].items())[:10]:
                if isinstance(info, dict):
                    if 'mean' in info:
                        lines.append(f"  {col}: mean={info['mean']}, min={info.get('min')}, max={info.get('max')}")
                    elif 'top_values' in info:
                        top = list(info['top_values'].keys())[:3]
                        lines.append(f"  {col}: categories={top}")

        lines.append(f"\nTotal rows: {profile.get('row_count', 'unknown')}")
        return '\n'.join(lines)

    def _get_data_statistics(self, profile: Dict) -> str:
        """Get summary statistics from profile."""
        if not profile.get('data_profile'):
            return "No statistics available."

        stats = []
        for col, info in list(profile['data_profile'].items())[:15]:
            if isinstance(info, dict):
                if 'mean' in info:
                    stats.append(f"  {col}: mean={info.get('mean')}, std={info.get('std')}, min={info.get('min')}, max={info.get('max')}")
                elif 'top_values' in info:
                    stats.append(f"  {col}: top={list(info['top_values'].keys())[:3]}")

        return '\n'.join(stats)

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse LLM response as JSON."""
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {'type': 'text', 'content': text}

    def _validate_sql(self, sql: str) -> str:
        """Validate and sanitize SQL query."""
        sql = sql.strip().rstrip(';')

        # Forbidden keywords
        forbidden = ['DELETE', 'DROP', 'ALTER', 'CREATE', 'INSERT', 'UPDATE', 'EXEC', 'GRANT', 'REVOKE']
        sql_upper = sql.upper()
        for keyword in forbidden:
            if keyword in sql_upper:
                raise ValueError(f"Forbidden SQL keyword: {keyword}")

        return sql

    def _extract_sql_from_text(self, text: str) -> Dict[str, Any]:
        """Try to extract a SQL query from free-text response."""
        # Look for SQL patterns
        sql_pattern = re.search(
            r'(?:SELECT|select)\s+.*?(?:FROM|from)\s+\w+.*?(?:;|$)',
            text, re.DOTALL | re.IGNORECASE
        )
        if sql_pattern:
            sql = sql_pattern.group().rstrip(';').strip()
            return {
                'type': 'sql',
                'content': 'Here is the SQL query for your question:',
                'sql_query': sql,
            }

        return {
            'type': 'text',
            'content': text,
        }
