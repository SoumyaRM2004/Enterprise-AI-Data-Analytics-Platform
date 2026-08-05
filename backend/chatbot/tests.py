from django.test import TestCase
import pandas as pd
from analytics.sql_engine import SQLExecutor
from chatbot.engine import ChatbotEngine


class SQLExecutorASTValidationTest(TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            'InvoiceDate': ['2025-01-01', '2025-01-02'],
            'Country': ['USA', 'UK'],
            'Quantity': [10, 20],
            'Price': [15.5, 20.0]
        })
        self.executor = SQLExecutor(self.df)

    def test_valid_select_query(self):
        sql = "SELECT Country, SUM(Quantity) AS total_qty FROM df GROUP BY Country ORDER BY total_qty DESC"
        is_valid, err = SQLExecutor.validate_sql_ast(sql, list(self.df.columns))
        self.assertTrue(is_valid)
        self.assertIsNone(err)

        res = self.executor.execute(sql)
        self.assertEqual(len(res['data']['rows']), 2)

    def test_forbidden_mutation_query(self):
        sql = "DROP TABLE df"
        is_valid, err = SQLExecutor.validate_sql_ast(sql, list(self.df.columns))
        self.assertFalse(is_valid)
        self.assertIn("Forbidden SQL operation", err)

        with self.assertRaises(ValueError):
            self.executor.execute(sql)

    def test_invalid_column_query(self):
        sql = "SELECT NonExistentColumn FROM df"
        is_valid, err = SQLExecutor.validate_sql_ast(sql, list(self.df.columns))
        self.assertFalse(is_valid)
        self.assertIn("Invalid column(s) referenced", err)


class ChatbotEnginePipelineTest(TestCase):
    def setUp(self):
        self.engine = ChatbotEngine()
        self.profile = {
            'name': 'Sales Dataset',
            'column_names': ['InvoiceDate', 'Country', 'Quantity', 'Price'],
            'column_types': {'InvoiceDate': 'datetime', 'Country': 'string', 'Quantity': 'integer', 'Price': 'float'},
            'data_profile': {
                'Quantity': {'mean': 15.0, 'min': 10, 'max': 20},
                'Country': {'unique_count': 2, 'top_values': {'USA': 1, 'UK': 1}}
            },
            'sample_data': [
                {'InvoiceDate': '2025-01-01', 'Country': 'USA', 'Quantity': 10, 'Price': 15.5},
                {'InvoiceDate': '2025-01-02', 'Country': 'UK', 'Quantity': 20, 'Price': 20.0}
            ],
            'row_count': 2,
            'column_count': 4
        }

    def test_intent_classification(self):
        self.assertEqual(self.engine._classify_intent("Forecast next quarter sales"), 'forecast')
        self.assertEqual(self.engine._classify_intent("Plot monthly revenue bar chart"), 'chart')
        self.assertEqual(self.engine._classify_intent("Analyze anomalies and key insights"), 'insight')
        self.assertEqual(self.engine._classify_intent("Show top 5 countries by quantity"), 'sql')

    def test_schema_context_rich_metadata(self):
        context = self.engine._build_schema_context(self.profile, question="Show sales by country")
        self.assertIn("Rich Database Schema Metadata:", context)
        self.assertIn("sample_values", context)
        self.assertIn("Sample Data Rows", context)

    def test_result_explanation(self):
        query_result = {
            'data': {
                'columns': ['Country', 'total_qty'],
                'rows': [{'Country': 'UK', 'total_qty': 20}, {'Country': 'USA', 'total_qty': 10}]
            },
            'total_rows': 2
        }
        explanation = self.engine.explain_sql_results(
            user_message="Show total quantity by country",
            sql_query="SELECT Country, SUM(Quantity) AS total_qty FROM df GROUP BY Country",
            query_result=query_result
        )
        self.assertTrue(len(explanation) > 0)
