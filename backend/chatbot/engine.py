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
            res = self._handle_nl_to_sql(message, schema_context, chat_history, dataset_profile)
        elif intent == 'insight':
            res = self._handle_insight_request(message, schema_context, dataset_profile, chat_history)
        elif intent == 'chart':
            res = self._handle_chart_request(message, schema_context, dataset_profile, chat_history)
        elif intent == 'forecast':
            res = self._handle_forecast_request(message, schema_context, dataset_profile, chat_history)
        else:
            res = self._handle_general_query(message, schema_context, chat_history, dataset_profile)

        if isinstance(res, dict) and ('error' in res or (isinstance(res.get('content'), str) and res.get('content', '').startswith('Error:'))):
            return self._generate_dynamic_fallback(message, dataset_profile, intent)

        return res

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
        self, message: str, schema_context: str, chat_history: List[Dict], dataset_profile: Optional[Dict] = None
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
        self, message: str, schema_context: str, chat_history: List[Dict], dataset_profile: Optional[Dict] = None
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

    def _generate_dynamic_fallback(self, message: str, profile: Optional[Dict], intent: str) -> Dict[str, Any]:
        """Generate smart dynamic response directly from dataset schema when LLM API Key is missing or offline."""
        if not profile:
            return {
                'type': 'text',
                'content': 'I am ready to assist! Upload a dataset or select an existing one to perform natural language SQL queries, AI data insights, forecasting, and automated reporting.',
                'follow_up_questions': ['How do I upload a dataset?', 'What file formats are supported?'],
            }

        cols = profile.get('column_names', [])
        col_types = profile.get('column_types', {})
        row_count = profile.get('row_count', 0)
        col_count = profile.get('column_count', 0)

        num_cols = [c for c, t in col_types.items() if t in ['integer', 'float']]
        cat_cols = [c for c, t in col_types.items() if t in ['category', 'string']]
        date_cols = [c for c, t in col_types.items() if t == 'datetime' or 'date' in c.lower() or 'time' in c.lower()]

        target_num = num_cols[0] if num_cols else (cols[0] if cols else 'column')
        target_cat = cat_cols[0] if cat_cols else (cols[1] if len(cols) > 1 else target_num)
        target_date = date_cols[0] if date_cols else None

        msg_lower = message.lower()

        if intent == 'forecast' or any(k in msg_lower for k in ['forecast', 'predict', 'future', 'trend']):
            return {
                'type': 'forecast',
                'content': f"Based on dataset schema ({row_count:,} rows), I recommend running time-series forecasting on numeric column '{target_num}' using date/time column '{target_date or target_cat}' over a 30-day horizon.",
                'recommended_method': 'holt_winters',
                'suggested_columns': {'target': target_num, 'date': target_date or target_cat},
                'suggested_horizon': 30,
                'follow_up_questions': [f"Forecast {target_num} for next 30 days", "Run anomaly detection"],
            }
        elif intent == 'chart' or any(k in msg_lower for k in ['chart', 'plot', 'graph', 'visualize']):
            return {
                'type': 'chart',
                'content': f"Here is a recommended chart visualization comparing '{target_num}' grouped by '{target_cat}'.",
                'chart_suggestion': {'type': 'bar', 'x': target_cat, 'y': target_num},
                'follow_up_questions': [f"Show distribution of {target_num}", f"Compare {target_num} by {target_cat}"],
            }
        elif intent == 'insight' or any(k in msg_lower for k in ['insight', 'summary', 'analyze', 'overview']):
            return {
                'type': 'insight',
                'content': f"Dataset Overview:\n- **Rows**: {row_count:,}\n- **Columns**: {col_count}\n- **Numeric Metrics**: {', '.join(num_cols[:5]) if num_cols else 'N/A'}\n- **Categorical Dimensions**: {', '.join(cat_cols[:5]) if cat_cols else 'N/A'}",
                'key_findings': [
                    f"Dataset contains {row_count:,} records across {col_count} attributes.",
                    f"Primary numeric column identified: '{target_num}'.",
                    f"Primary categorical dimension identified: '{target_cat}'.",
                ],
                'follow_up_questions': [f"What is the average {target_num}?", f"Show top 10 {target_cat} by {target_num}"],
            }
        else:
            if 'count' in msg_lower or 'how many' in msg_lower:
                sql = "SELECT COUNT(*) AS total_count FROM df"
                explanation = f"Counting total records in dataset ({row_count:,} rows)."
            elif 'top' in msg_lower or 'highest' in msg_lower or 'largest' in msg_lower or 'most' in msg_lower:
                sql = f"SELECT `{target_cat}`, SUM(`{target_num}`) AS total_{target_num} FROM df GROUP BY `{target_cat}` ORDER BY total_{target_num} DESC LIMIT 10"
                explanation = f"Querying top 10 '{target_cat}' by total '{target_num}'."
            elif 'average' in msg_lower or 'mean' in msg_lower:
                sql = f"SELECT AVG(`{target_num}`) AS avg_{target_num} FROM df"
                explanation = f"Calculating average of '{target_num}'."
            else:
                sql = f"SELECT * FROM df LIMIT 10"
                explanation = f"Displaying sample records from dataset."

            return {
                'type': 'sql',
                'content': explanation,
                'sql_query': sql,
                'follow_up_questions': [f"Show top 10 {target_cat} by {target_num}", f"Calculate average {target_num}"],
            }
