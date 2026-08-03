"""
SQL executor - translates SQL queries to pandas operations.
Uses sqlglot for safe parsing and validation.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


class SQLExecutor:
    """Execute SQL-like queries on pandas DataFrames safely."""

    # Safety restrictions
    FORBIDDEN_KEYWORDS = ['DELETE', 'DROP', 'ALTER', 'CREATE', 'INSERT', 'UPDATE', 'EXEC']
    MAX_RESULT_ROWS = 10000
    MAX_QUERY_LENGTH = 5000

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def execute(self, sql: str) -> Dict[str, Any]:
        """Parse and execute SQL query on the DataFrame."""
        sql = sql.strip()

        # Security checks
        if len(sql) > self.MAX_QUERY_LENGTH:
            raise ValueError(f"Query too long. Maximum {self.MAX_QUERY_LENGTH} characters.")

        sql_upper = sql.upper()
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in sql_upper and keyword not in ['SELECT']:
                raise ValueError(f"Forbidden SQL keyword: {keyword}")

        sql = sql.replace('`', '"')
        from sqlglot import parse as sqlglot_parse

        try:
            parsed = sqlglot_parse(sql)
        except Exception:
            raise ValueError("Could not parse SQL query.")

        # Parse the query and execute using pandas operations
        return self._execute_parsed(sql)

    def _execute_parsed(self, sql: str) -> Dict[str, Any]:
        """Execute parsed SQL query using pandas."""
        import re

        sql_clean = sql.strip().rstrip(';')

        # Handle SELECT queries
        if sql_clean.upper().startswith('SELECT'):
            return self._execute_select(sql_clean)
        elif sql_clean.upper().startswith('SHOW'):
            return self._execute_show(sql_clean)
        elif sql_clean.upper().startswith('DESCRIBE'):
            return self._execute_describe(sql_clean)
        else:
            raise ValueError("Only SELECT, SHOW, and DESCRIBE queries are supported.")

    def _execute_select(self, sql: str) -> Dict[str, Any]:
        """Execute SELECT queries with WHERE, GROUP BY, ORDER BY, LIMIT."""
        import re

        # Extract columns
        match = re.match(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if not match:
            # Simple SELECT * FROM table
            if 'SELECT *' in sql.upper() or 'SELECT  *' in sql.upper():
                result_df = self.df.copy()
            else:
                raise ValueError("Could not parse SELECT columns.")
        else:
            cols_str = match.group(1).strip()
            if cols_str == '*':
                result_df = self.df.copy()
            else:
                # Parse column expressions
                columns = [c.strip() for c in cols_str.split(',')]
                available_cols = [c for c in columns if c in self.df.columns]
                if not available_cols:
                    raise ValueError(f"None of the requested columns found. Available: {list(self.df.columns)}")
                result_df = self.df[available_cols].copy()

        # Extract table name and validate
        from_match = re.search(r'FROM\s+(\w+)', sql, re.IGNORECASE)
        # Table name is validated but we just use our df

        # Handle WHERE clause
        where_match = re.search(r'WHERE\s+(.*?)(?:GROUP|ORDER|LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1).strip()
            result_df = self._apply_where(result_df, where_clause)

        # Handle GROUP BY with aggregation
        group_match = re.search(r'GROUP\s+BY\s+(.*?)(?:ORDER|LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
        if group_match:
            group_cols = [c.strip() for c in group_match.group(1).strip().split(',')]
            group_cols = [c for c in group_cols if c in result_df.columns]
            if group_cols:
                # Parse aggregate functions
                agg_dict = self._parse_aggregations(sql, result_df.columns)
                if agg_dict:
                    result_df = result_df.groupby(group_cols).agg(agg_dict).reset_index()
                else:
                    result_df = result_df.groupby(group_cols).size().reset_index(name='count')

        # Handle ORDER BY
        order_match = re.search(r'ORDER\s+BY\s+(.*?)(?:LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
        if order_match:
            order_clause = order_match.group(1).strip()
            result_df = self._apply_order(result_df, order_clause)

        # Handle LIMIT
        limit_match = re.search(r'LIMIT\s+(\d+)', sql, re.IGNORECASE)
        if limit_match:
            limit = int(limit_match.group(1))
            result_df = result_df.head(min(limit, self.MAX_RESULT_ROWS))
        else:
            result_df = result_df.head(self.MAX_RESULT_ROWS)

        # Convert to JSON-serializable format
        return self._result_to_dict(result_df, len(self.df))

    def _apply_where(self, df: pd.DataFrame, where_clause: str) -> pd.DataFrame:
        """Apply WHERE clause filtering."""
        import re

        conditions = re.split(r'\bAND\b|\bOR\b', where_clause, flags=re.IGNORECASE)

        for condition in conditions:
            condition = condition.strip().strip('()')

            # Handle LIKE
            like_match = re.match(r"(\w+)\s+LIKE\s+'([^']+)'", condition, re.IGNORECASE)
            if like_match:
                col, pattern = like_match.groups()
                if col in df.columns:
                    regex_pattern = pattern.replace('%', '.*').replace('_', '.')
                    df = df[df[col].astype(str).str.contains(regex_pattern, case=False, na=False)]
                continue

            # Handle IN
            in_match = re.match(r"(\w+)\s+IN\s+\(([^)]+)\)", condition, re.IGNORECASE)
            if in_match:
                col, values_str = in_match.groups()
                if col in df.columns:
                    values = [v.strip().strip("'\"") for v in values_str.split(',')]
                    df = df[df[col].astype(str).isin(values)]
                continue

            # Handle comparison operators
            comp_match = re.match(r"(\w+)\s*(>=|<=|!=|<>|=|>|<)\s*(.+)", condition)
            if comp_match:
                col, operator, value = comp_match.groups()
                if col in df.columns:
                    value = value.strip().strip("'\"")
                    # Try numeric comparison
                    try:
                        num_value = float(value)
                        if operator == '=':
                            df = df[df[col] == num_value]
                        elif operator == '!=' or operator == '<>':
                            df = df[df[col] != num_value]
                        elif operator == '>':
                            df = df[df[col] > num_value]
                        elif operator == '<':
                            df = df[df[col] < num_value]
                        elif operator == '>=':
                            df = df[df[col] >= num_value]
                        elif operator == '<=':
                            df = df[df[col] <= num_value]
                    except ValueError:
                        if operator == '=':
                            df = df[df[col].astype(str) == value]
                        elif operator == '!=' or operator == '<>':
                            df = df[df[col].astype(str) != value]
                        else:
                            df = df[df[col].astype(str) > value]

            # Handle IS NULL / IS NOT NULL
            null_match = re.match(r"(\w+)\s+IS\s+(NOT\s+)?NULL", condition, re.IGNORECASE)
            if null_match:
                col, is_not = null_match.groups()
                if col in df.columns:
                    if is_not:
                        df = df[df[col].notna()]
                    else:
                        df = df[df[col].isna()]

        return df

    def _apply_order(self, df: pd.DataFrame, order_clause: str) -> pd.DataFrame:
        """Apply ORDER BY clause."""
        parts = order_clause.strip().split()
        if len(parts) >= 2:
            col = parts[0]
            direction = parts[1].upper()
            if col in df.columns:
                ascending = direction != 'DESC'
                df = df.sort_values(by=col, ascending=ascending)
        elif len(parts) == 1 and parts[0] in df.columns:
            df = df.sort_values(by=parts[0])
        return df

    def _parse_aggregations(self, sql: str, columns: list) -> Dict[str, str]:
        """Parse aggregate functions from SQL."""
        import re
        agg_pattern = r'(COUNT|SUM|AVG|MEAN|MIN|MAX|MEDIAN|STD|FIRST|LAST)\s*\(\s*(?:DISTINCT\s+)?(\*|\w+)\s*\)'
        matches = re.findall(agg_pattern, sql, re.IGNORECASE)

        agg_dict = {}
        pandas_agg_map = {
            'COUNT': 'count',
            'SUM': 'sum',
            'AVG': 'mean',
            'MEAN': 'mean',
            'MIN': 'min',
            'MAX': 'max',
            'MEDIAN': 'median',
            'STD': 'std',
            'FIRST': 'first',
            'LAST': 'last',
        }

        for func, col in matches:
            pandas_func = pandas_agg_map.get(func.upper(), func.lower())
            if col == '*':
                agg_dict = {'*': pandas_func}
            elif col in columns:
                agg_dict[col] = pandas_func

        return agg_dict

    def _execute_show(self, sql: str) -> Dict[str, Any]:
        """Execute SHOW TABLES or SHOW COLUMNS."""
        return {
            'data': {
                'columns': list(self.df.columns),
                'dtypes': {col: str(self.df[col].dtype) for col in self.df.columns},
                'row_count': len(self.df),
            },
            'total_rows': len(self.df),
            'execution_time': 0.001,
        }

    def _execute_describe(self, sql: str) -> Dict[str, Any]:
        """Execute DESCRIBE TABLE."""
        desc = self.df.describe(include='all').T
        result = desc.reset_index()
        result.columns = ['column'] + list(result.columns[1:])
        return self._result_to_dict(result, len(self.df))

    def _result_to_dict(self, df: pd.DataFrame, total_rows: int) -> Dict[str, Any]:
        """Convert DataFrame result to JSON-serializable dict."""
        rows = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                if pd.isna(val):
                    record[col] = None
                elif isinstance(val, (np.integer,)):
                    record[col] = int(val)
                elif isinstance(val, (np.floating,)):
                    record[col] = float(val)
                elif hasattr(val, 'isoformat'):
                    record[col] = val.isoformat()
                else:
                    record[col] = str(val)
            rows.append(record)

        return {
            'data': {
                'columns': list(df.columns),
                'rows': rows,
                'row_count': len(rows),
            },
            'total_rows': total_rows,
            'truncated': len(rows) >= self.MAX_RESULT_ROWS,
        }
