"""
Chatbot engine - handles NL-to-SQL with AST parsing, repair loop, intent routing, and AI insights.
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
    """Production-grade AI Chatbot Engine for NL-to-SQL, analytics, and forecasting."""

    SYSTEM_PROMPT = """You are an expert Data Analytics and SQL Assistant.

Your job is to understand the user's intent and return EXACTLY ONE valid JSON object.

Available response types:

1. "sql"
Use when the user is asking about historical, existing, or current data (e.g., monthly sales trends, top 10 customers, average order value, sales by country, highest selling products, monthly revenue, compare sales between categories).

2. "forecast"
Use ONLY when the user explicitly asks about future values or predictions (e.g., predict next month sales, forecast next quarter revenue, estimate future demand, predict customer growth, sales projection). Return the historical SQL required for forecasting along with the recommended forecasting method.

3. "clarification"
Use when the user's request is ambiguous or lacks required information (e.g., "predict next quarter", "show best products", "analyze performance"). Ask ONE concise clarification question instead of guessing.

4. "answer" (or "text")
Use when the question is conceptual and does not require SQL (e.g., "What is SQL?", "Explain correlation.", "What is regression?").

Rules:
- Decide the intent yourself using the user's request.
- Do NOT rely on keywords alone. Understand the semantic meaning of the question.
- "Trend" means historical analysis unless the user explicitly asks to predict the future.
- Historical analysis MUST return type "sql".
- Future prediction MUST return type "forecast".
- Never return more than one response type or multiple JSON objects.
- Never explain your reasoning outside the JSON.
- Never generate SQL for non-SQL responses.
- If required information is missing, return a "clarification" response instead of guessing.
- Use standard SQLite SELECT queries (table name 'df'). Use only tables and columns from the provided schema. Never invent columns or tables.

Your response MUST be a single valid JSON object:
{
    "type": "sql" | "forecast" | "chart" | "insight" | "clarification" | "answer",
    "content": "natural language response / explanation / clarifying question",
    "sql_query": "SELECT ... FROM df ... (for sql or forecast)",
    "confidence": 0.95,
    "reasoning": "Brief explanation of query logic",
    "chart_suggestion": {"type": "bar/line/pie/scatter", "x": "column", "y": "column"},
    "recommended_method": "holt_winters",
    "follow_up_questions": ["question1", "question2"]
}"""

    def __init__(self):
        self.llm = LLMProviderFactory.create()
        self._cache = {}

    def process_message(
        self,
        message: str,
        dataset_profile: Optional[Dict] = None,
        chat_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Process user message using intent routing, AST validation, and repair loops."""

        if not chat_history:
            chat_history = []

        # Check SQL Cache
        cache_key = (
            dataset_profile.get('name', 'ds') if dataset_profile else 'no_ds',
            message.strip().lower()
        )
        if cache_key in self._cache:
            logger.info(f"Returning cached chatbot response for: {message}")
            return self._cache[cache_key]

        # Extract conversational state memory across turns
        conv_state = self._extract_conversational_state(chat_history)

        # Build rich schema context
        schema_context = self._build_schema_context(dataset_profile, question=message)

        # Classify intent
        intent = self._classify_intent(message, dataset_profile)

        if intent == 'sql':
            res = self._handle_nl_to_sql_with_repair(
                message, schema_context, chat_history, dataset_profile, conv_state
            )
        elif intent == 'insight':
            res = self._handle_insight_request(message, schema_context, dataset_profile, chat_history)
        elif intent == 'chart':
            res = self._handle_chart_request(message, schema_context, dataset_profile, chat_history)
        elif intent == 'forecast':
            res = self._handle_forecast_request(message, schema_context, dataset_profile, chat_history)
        else:
            res = self._handle_general_query(message, schema_context, chat_history, dataset_profile)

        # Handle API key missing / offline fallback
        if isinstance(res, dict) and ('error' in res or (isinstance(res.get('content'), str) and res.get('content', '').startswith('Error:'))):
            return self._generate_dynamic_fallback(message, dataset_profile, intent)

        # Cache high confidence SQL responses
        if isinstance(res, dict) and res.get('type') in ['sql', 'chart', 'insight'] and res.get('confidence', 1.0) >= 0.8:
            self._cache[cache_key] = res

        return res

    def _classify_intent(self, message: str, profile: Optional[Dict] = None) -> str:
        """Classify user message intent into sql, forecast, chart, insight, or general."""
        msg = message.lower()

        # Explicit future prediction words (excluding 'trend' which defaults to historical SQL)
        forecast_words = ['predict', 'forecast', 'future', 'next month', 'next quarter', 'next year', 'projection', 'estimate']
        chart_words = ['chart', 'graph', 'plot', 'visualize', 'visualization', 'bar chart', 'line chart', 'pie chart', 'scatter']
        insight_words = ['insight', 'analyze', 'analysis', 'pattern', 'correlation', 'anomaly', 'outlier', 'recommend', 'suggest', 'why did', 'cause', 'explain', 'overview']
        sql_words = ['show', 'find', 'get', 'list', 'filter', 'count', 'how many', 'which', 'who', 'select', 'where', 'group by', 'average', 'total', 'sum', 'max', 'min', 'top', 'bottom', 'compare', 'trend']

        if any(w in msg for w in forecast_words):
            return 'forecast'
        elif any(w in msg for w in chart_words):
            return 'chart'
        elif any(w in msg for w in insight_words):
            return 'insight'
        elif any(w in msg for w in sql_words):
            return 'sql'
        else:
            return 'sql'

    def _extract_conversational_state(self, chat_history: List[Dict]) -> Dict[str, Any]:
        """Extract state memory from recent chat history turns."""
        state = {}
        for msg in reversed(chat_history[-6:]):
            if isinstance(msg, dict):
                if msg.get('sql_query'):
                    state.setdefault('last_sql', msg['sql_query'])
                if msg.get('chart_config'):
                    state.setdefault('last_chart', msg['chart_config'])
        return state

    def _build_schema_context(self, profile: Optional[Dict], question: Optional[str] = None) -> str:
        """Build rich schema context with column types, nullability, unique values, stats, and sample rows."""
        if not profile:
            return "No dataset schema available."

        columns = profile.get('column_names', [])
        col_types = profile.get('column_types', {})
        data_prof = profile.get('data_profile', {})
        sample_rows = profile.get('sample_data', [])

        # Smart column selection for wide datasets (> 25 columns)
        if len(columns) > 25 and question:
            q_terms = set(re.findall(r'\w+', question.lower()))
            relevant_cols = []
            for col in columns:
                if any(term in col.lower() for term in q_terms if len(term) > 2):
                    relevant_cols.append(col)
            # Add essential numeric and date columns
            for col in columns:
                if col not in relevant_cols:
                    t = str(col_types.get(col, '')).lower()
                    if t in ['integer', 'float', 'datetime'] or 'date' in col.lower() or 'time' in col.lower():
                        relevant_cols.append(col)
                if len(relevant_cols) >= 20:
                    break
            for col in columns:
                if col not in relevant_cols:
                    relevant_cols.append(col)
                if len(relevant_cols) >= 20:
                    break
            columns_to_show = relevant_cols
        else:
            columns_to_show = columns

        schema_dict = {}
        for col in columns_to_show:
            c_type = col_types.get(col, 'string')
            c_info = data_prof.get(col, {})
            c_meta = {
                'type': c_type,
                'null_percent': c_info.get('null_percent', 0),
                'unique_count': c_info.get('unique_count', 'unknown'),
            }
            if 'mean' in c_info:
                c_meta['min'] = c_info.get('min')
                c_meta['max'] = c_info.get('max')
                c_meta['mean'] = c_info.get('mean')
            if 'top_values' in c_info and isinstance(c_info['top_values'], dict):
                c_meta['unique_values'] = list(c_info['top_values'].keys())[:5]

            # Extract sample values for this column from sample_rows
            col_samples = []
            if isinstance(sample_rows, list):
                for row in sample_rows[:3]:
                    if isinstance(row, dict) and col in row:
                        val = row[col]
                        if val is not None and str(val) not in col_samples:
                            col_samples.append(str(val))
            if col_samples:
                c_meta['sample_values'] = col_samples[:3]

            schema_dict[col] = c_meta

        output = [
            f"Table Name: df",
            f"Total Rows: {profile.get('row_count', 'unknown')}",
            f"Total Columns: {profile.get('column_count', len(columns))}",
            "\nRich Database Schema Metadata:",
            json.dumps(schema_dict, indent=2, default=str),
        ]

        if sample_rows and isinstance(sample_rows, list):
            output.append("\nSample Data Rows (First 3 rows):")
            output.append(json.dumps(sample_rows[:3], indent=2, default=str))

        return '\n'.join(output)

    def _handle_nl_to_sql_with_repair(
        self,
        message: str,
        schema_context: str,
        chat_history: List[Dict],
        dataset_profile: Optional[Dict] = None,
        conv_state: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Handle NL-to-SQL with sqlglot AST parsing and a multi-turn self-correction repair loop."""
        from analytics.sql_engine import SQLExecutor

        available_cols = dataset_profile.get('column_names', []) if dataset_profile else []

        prompt = f"""{self.SYSTEM_PROMPT}

Dataset Context:
{schema_context}

Conversational Memory State:
{json.dumps(conv_state or {}, indent=2)}

User Question: {message}

Rules:
1. Generate standard SQLite SELECT query targeting table 'df'.
2. Use ONLY existing columns from the schema.
3. If intent is ambiguous or required metrics are missing (e.g., "predict next quarter"), set type to "clarification" and ask one clear question.
4. Set "confidence" score (0.0 to 1.0). If confidence < 0.6, ask a clarification question."""

        messages = [{'role': 'system', 'content': prompt}]
        for msg in chat_history[-settings.CHAT_MAX_CONTEXT_MESSAGES:]:
            messages.append({'role': msg['role'], 'content': msg['content']})

        result = self.llm.generate(messages)
        response_data = self._parse_response(result.get('content', ''))

        # Clarification check
        if response_data.get('type') == 'clarification' or response_data.get('confidence', 1.0) < 0.6:
            if not response_data.get('content'):
                response_data['content'] = "Could you please specify which metric or column you would like to analyze?"
            response_data['type'] = 'clarification'
            return response_data

        # SQL Repair Loop (up to 2 retries)
        max_retries = 2
        for attempt in range(max_retries + 1):
            if response_data.get('type') == 'sql' and response_data.get('sql_query'):
                sql = response_data['sql_query'].strip()
                is_valid, err_msg = SQLExecutor.validate_sql_ast(sql, available_cols)

                if is_valid:
                    response_data['sql_query'] = sql.rstrip(';')
                    return response_data

                logger.warning(f"SQL AST validation attempt {attempt + 1} failed: {err_msg}")
                if attempt < max_retries:
                    repair_msg = (
                        f"The generated SQL failed AST validation with error: {err_msg}.\n"
                        f"Failed SQL: {sql}\n"
                        f"Available columns: {', '.join(available_cols)}\n"
                        f"Please return a corrected JSON response with a valid SQL query."
                    )
                    messages.append({'role': 'assistant', 'content': result.get('content', '')})
                    messages.append({'role': 'user', 'content': repair_msg})
                    result = self.llm.generate(messages)
                    response_data = self._parse_response(result.get('content', ''))

        # Fallback to text extraction
        extracted = self._extract_sql_from_text(result.get('content', ''))
        if extracted.get('sql_query'):
            is_valid, _ = SQLExecutor.validate_sql_ast(extracted['sql_query'], available_cols)
            if is_valid:
                return extracted

        return self._generate_dynamic_fallback(message, dataset_profile, 'sql')

    def explain_sql_results(
        self,
        user_message: str,
        sql_query: str,
        query_result: Dict[str, Any],
    ) -> str:
        """Synthesize natural language explanations from executed SQL query results."""
        try:
            data = query_result.get('data', {})
            rows = data.get('rows', [])
            cols = data.get('columns', [])
            total_rows = query_result.get('total_rows', len(rows))

            if not rows:
                return "The query executed successfully but returned no matching data records."

            sample_results = rows[:10]
            prompt = f"""You are a senior data analyst explaining SQL query results to a decision-maker.

User Question: {user_message}
Executed SQL: {sql_query}
Total Matching Records: {total_rows:,}
Columns Returned: {cols}
Result Sample (First {len(sample_results)} rows):
{json.dumps(sample_results, indent=2, default=str)}

Write a concise 2-3 sentence business summary explaining the key findings from these results in direct answer to the user's question. Focus on key numbers, top values, or notable patterns."""

            res = self.llm.generate([{'role': 'user', 'content': prompt}])
            summary = res.get('content', '').strip()
            if summary and not summary.startswith('Error:'):
                return summary
        except Exception as e:
            logger.error(f"Error synthesizing SQL results explanation: {e}")

        return f"Query returned {query_result.get('total_rows', 0):,} results."

    def _handle_insight_request(
        self, message: str, schema_context: str, profile: Dict, chat_history: List[Dict]
    ) -> Dict[str, Any]:
        """Handle AI insight requests."""
        stats = self._get_data_statistics(profile)

        prompt = f"""{self.SYSTEM_PROMPT}

Dataset Context:
{schema_context}

Summary Statistics:
{stats}

User Request: {message}

Provide detailed data insights and findings.
Respond with JSON:
{{"type": "insight", "content": "detailed insight text", "key_findings": ["finding1", "finding2"], "confidence": 0.9, "chart_suggestion": {{"type": "bar", "x": "col1", "y": "col2"}}}}"""

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
        """Handle visualization requests."""
        prompt = f"""{self.SYSTEM_PROMPT}

Dataset Context:
{schema_context}

User Request: {message}

Suggest the best chart visualization for this request.
Respond with JSON:
{{"type": "chart", "content": "chart summary", "chart_suggestion": {{"type": "bar/line/pie/scatter", "x": "column_name", "y": "column_name"}}, "confidence": 0.95}}"""

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
        self, message: str, schema_context: str, profile: Optional[Dict], chat_history: List[Dict]
    ) -> Dict[str, Any]:
        """Handle forecasting requests with mandatory target metric verification."""
        msg_lower = message.lower()
        col_names = profile.get('column_names', []) if profile else []
        col_types = profile.get('column_types', {}) if profile else {}

        # Filter out identifier / primary key columns (CustomerID, InvoiceNo, StockCode, RowID, etc.)
        id_terms = ['id', 'code', 'no', 'number', 'key', 'index', 'row', 'invoice', 'sku']
        metric_cols = [
            c for c in col_names
            if col_types.get(c) in ['integer', 'float'] and not any(term == c.lower() or c.lower().endswith(term) for term in id_terms)
        ]

        # Check if user message explicitly specifies a metric
        has_metric = False
        for c in metric_cols:
            if c.lower() in msg_lower:
                has_metric = True
                break

        metric_synonyms = ['revenue', 'sales', 'quantity', 'amount', 'orders', 'price', 'total', 'profit', 'spend', 'demand', 'count', 'value']
        if not has_metric:
            for s in metric_synonyms:
                if s in msg_lower:
                    has_metric = True
                    break

        # If target metric is missing, DO NOT guess. Return a clarification response immediately.
        if not has_metric:
            suggested_options = []
            has_revenue_rec = False

            for c in metric_cols:
                c_lower = c.lower()
                if ('price' in c_lower or 'amount' in c_lower or 'total' in c_lower or 'revenue' in c_lower or 'sales' in c_lower) and not has_revenue_rec:
                    suggested_options.append('Revenue (Recommended)')
                    has_revenue_rec = True
                elif 'quantity' in c_lower or 'qty' in c_lower:
                    suggested_options.append('Quantity Sold')
                elif 'profit' in c_lower or 'margin' in c_lower:
                    suggested_options.append('Profit')
                else:
                    suggested_options.append(c.replace('_', ' ').title())

            # Check if dataset has invoice/order columns to suggest Number of Orders
            if any('invoice' in c.lower() or 'order' in c.lower() for c in col_names):
                if 'Number of Orders' not in suggested_options:
                    suggested_options.append('Number of Orders')

            if not has_revenue_rec and suggested_options:
                suggested_options[0] = f"{suggested_options[0]} (Recommended)"

            # Fallback options if dataset schema is incomplete
            if not suggested_options:
                suggested_options = ["Revenue (Recommended)", "Quantity Sold", "Number of Orders"]

            # Remove duplicates while preserving order
            seen = set()
            clean_options = []
            for opt in suggested_options:
                if opt not in seen:
                    seen.add(opt)
                    clean_options.append(opt)

            return {
                'type': 'clarification',
                'content': 'Which metric would you like to forecast?',
                'options': clean_options,
                'follow_up_questions': clean_options,
                'confidence': 1.0,
            }

        # Target metric is specified -> generate forecasting parameters
        prompt = f"""{self.SYSTEM_PROMPT}

Dataset Context:
{schema_context}

User Request: {message}

The user specified a target metric for forecasting. Provide time-series forecasting guidance and parameters.
Respond with JSON:
{{"type": "forecast", "content": "forecasting advice", "recommended_method": "holt_winters", "suggested_columns": {{"target": "col", "date": "col"}}, "suggested_horizon": 30}}"""

        messages = [{'role': 'system', 'content': prompt}]
        for msg in chat_history[-settings.CHAT_MAX_CONTEXT_MESSAGES:]:
            messages.append({'role': msg['role'], 'content': msg['content']})

        result = self.llm.generate(messages)

        try:
            response_data = self._parse_response(result['content'])
            if response_data.get('type') in ['forecast', 'clarification']:
                return response_data
        except Exception:
            pass

        return {
            'type': 'forecast',
            'content': f"Forecasting guidance for {message}",
            'recommended_method': 'holt_winters',
        }

    def _handle_general_query(
        self, message: str, schema_context: str, chat_history: List[Dict], dataset_profile: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Handle general conversational queries."""
        prompt = f"""{self.SYSTEM_PROMPT}

Dataset Context:
{schema_context}

User Message: {message}"""

        messages = [{'role': 'system', 'content': prompt}]
        for msg in chat_history[-settings.CHAT_MAX_CONTEXT_MESSAGES:]:
            messages.append({'role': msg['role'], 'content': msg['content']})

        result = self.llm.generate(messages)

        return {
            'type': 'text',
            'content': result['content'],
        }

    def _get_data_statistics(self, profile: Dict) -> str:
        """Get summary statistics from profile."""
        if not profile or not profile.get('data_profile'):
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
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {'type': 'text', 'content': text}

    def _extract_sql_from_text(self, text: str) -> Dict[str, Any]:
        """Extract SQL query from free-text response."""
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
                'confidence': 0.85,
            }

        return {
            'type': 'text',
            'content': text,
        }

    def _generate_dynamic_fallback(self, message: str, profile: Optional[Dict], intent: str) -> Dict[str, Any]:
        """Generate smart dynamic response directly from dataset schema when LLM API is offline or missing."""
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
