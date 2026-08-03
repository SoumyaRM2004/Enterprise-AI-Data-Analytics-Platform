"""
Chart data generator - creates chart configurations from datasets.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional


class ChartGenerator:
    """Generate chart data and configurations from pandas DataFrames."""

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def auto_generate_charts(self) -> List[Dict[str, Any]]:
        """Automatically generate relevant charts based on data types."""
        charts = []
        numeric_cols = self.df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = self.df.select_dtypes(exclude=['number']).columns.tolist()

        # 1. Bar chart for categorical vs numeric
        if categorical_cols and numeric_cols:
            for cat_col in categorical_cols[:2]:
                if self.df[cat_col].nunique() <= 20:
                    for num_col in numeric_cols[:2]:
                        grouped = self.df.groupby(cat_col)[num_col].mean().reset_index()
                        charts.append({
                            'type': 'bar',
                            'title': f'Average {num_col} by {cat_col}',
                            'data': {
                                'labels': grouped[cat_col].astype(str).tolist(),
                                'datasets': [{
                                    'label': num_col,
                                    'data': grouped[num_col].round(2).tolist(),
                                    'backgroundColor': 'rgba(59, 130, 246, 0.6)',
                                    'borderColor': 'rgba(59, 130, 246, 1)',
                                    'borderWidth': 1,
                                }]
                            },
                            'options': {
                                'responsive': True,
                                'plugins': {'legend': {'position': 'top'}},
                                'scales': {'y': {'beginAtZero': True}},
                            }
                        })
                        break  # One bar chart per categorical column

        # 2. Line chart for time series or sequential numeric data
        if numeric_cols and len(self.df) > 5:
            for num_col in numeric_cols[:2]:
                # Check if there's a sequential index or date column
                charts.append({
                    'type': 'line',
                    'title': f'{num_col} Trend',
                    'data': {
                        'labels': [str(i) for i in range(min(len(self.df), 100))],
                        'datasets': [{
                            'label': num_col,
                            'data': self.df[num_col].head(100).tolist(),
                            'borderColor': 'rgba(16, 185, 129, 1)',
                            'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                            'fill': True,
                            'tension': 0.4,
                        }]
                    },
                    'options': {
                        'responsive': True,
                        'plugins': {'legend': {'position': 'top'}},
                        'scales': {'y': {'beginAtZero': True}},
                    }
                })

        # 3. Pie chart for categorical distribution
        if categorical_cols:
            for cat_col in categorical_cols[:1]:
                if self.df[cat_col].nunique() <= 10 and self.df[cat_col].nunique() >= 2:
                    value_counts = self.df[cat_col].value_counts()
                    colors = [
                        'rgba(59, 130, 246, 0.7)',
                        'rgba(16, 185, 129, 0.7)',
                        'rgba(245, 158, 11, 0.7)',
                        'rgba(239, 68, 68, 0.7)',
                        'rgba(139, 92, 246, 0.7)',
                        'rgba(236, 72, 153, 0.7)',
                        'rgba(20, 184, 166, 0.7)',
                        'rgba(251, 146, 60, 0.7)',
                        'rgba(100, 116, 139, 0.7)',
                        'rgba(99, 102, 241, 0.7)',
                    ]
                    charts.append({
                        'type': 'pie',
                        'title': f'Distribution of {cat_col}',
                        'data': {
                            'labels': value_counts.index.astype(str).tolist(),
                            'datasets': [{
                                'data': value_counts.values.tolist(),
                                'backgroundColor': colors[:len(value_counts)],
                            }]
                        },
                        'options': {
                            'responsive': True,
                            'plugins': {'legend': {'position': 'right'}},
                        }
                    })

        # 4. Histogram for numeric columns
        if numeric_cols:
            for num_col in numeric_cols[:2]:
                histogram_data, bin_edges = np.histogram(
                    self.df[num_col].dropna(), bins=min(20, int(np.sqrt(len(self.df))))
                )
                charts.append({
                    'type': 'histogram',
                    'title': f'Distribution of {num_col}',
                    'data': {
                        'labels': [f'{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}'
                                   for i in range(len(histogram_data))],
                        'datasets': [{
                            'label': num_col,
                            'data': histogram_data.tolist(),
                            'backgroundColor': 'rgba(139, 92, 246, 0.5)',
                            'borderColor': 'rgba(139, 92, 246, 1)',
                            'borderWidth': 1,
                        }]
                    },
                    'options': {
                        'responsive': True,
                        'scales': {'y': {'beginAtZero': True}},
                    }
                })

        # 5. Scatter plot for two numeric columns
        if len(numeric_cols) >= 2:
            charts.append({
                'type': 'scatter',
                'title': f'{numeric_cols[0]} vs {numeric_cols[1]}',
                'data': {
                    'datasets': [{
                        'label': f'{numeric_cols[0]} vs {numeric_cols[1]}',
                        'data': [
                            {'x': float(self.df[numeric_cols[0]].iloc[i]),
                             'y': float(self.df[numeric_cols[1]].iloc[i])}
                            for i in range(min(200, len(self.df)))
                            if not pd.isna(self.df[numeric_cols[0]].iloc[i])
                            and not pd.isna(self.df[numeric_cols[1]].iloc[i])
                        ],
                        'backgroundColor': 'rgba(59, 130, 246, 0.5)',
                        'pointRadius': 4,
                    }]
                },
                'options': {
                    'responsive': True,
                    'scales': {
                        'x': {'title': {'display': True, 'text': numeric_cols[0]}},
                        'y': {'title': {'display': True, 'text': numeric_cols[1]}},
                    },
                }
            })

        return charts[:10]  # Limit to 10 auto-generated charts

    def generate_chart_data(
        self,
        chart_type: str,
        x_column: Optional[str] = None,
        y_column: Optional[str] = None,
        group_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate chart data based on specified parameters."""

        if chart_type == 'bar':
            return self._bar_chart(x_column, y_column, group_by)
        elif chart_type == 'line':
            return self._line_chart(x_column, y_column)
        elif chart_type == 'pie':
            return self._pie_chart(x_column)
        elif chart_type == 'scatter':
            return self._scatter_chart(x_column, y_column)
        elif chart_type == 'heatmap':
            return self._heatmap_data(x_column, y_column)
        elif chart_type == 'histogram':
            return self._histogram_chart(x_column)
        else:
            return {'error': f'Unsupported chart type: {chart_type}'}

    def _bar_chart(self, x_col, y_col, group_by=None):
        if not x_col or not y_col:
            return {'error': 'x and y columns are required for bar chart.'}

        if group_by:
            grouped = self.df.groupby([x_col, group_by])[y_col].mean().unstack()
            datasets = []
            for col in grouped.columns:
                datasets.append({
                    'label': str(col),
                    'data': grouped[col].tolist(),
                })
            labels = [str(i) for i in grouped.index]
        else:
            grouped = self.df.groupby(x_col)[y_col].mean().reset_index()
            labels = grouped[x_col].astype(str).tolist()
            datasets = [{'label': y_col, 'data': grouped[y_col].round(2).tolist()}]

        return {
            'type': 'bar',
            'data': {'labels': labels, 'datasets': datasets},
            'options': {'responsive': True},
        }

    def _line_chart(self, x_col, y_col):
        if not y_col:
            return {'error': 'y column is required for line chart.'}

        labels = [str(i) for i in range(min(len(self.df), 200))]
        if x_col and x_col in self.df.columns:
            labels = self.df[x_col].astype(str).head(200).tolist()

        datasets = []
        for col in (self.df.select_dtypes(include=['number']).columns if not y_col else [y_col]):
            datasets.append({
                'label': col,
                'data': self.df[col].head(200).tolist(),
                'borderColor': 'rgba(59, 130, 246, 1)',
                'fill': False,
            })

        return {'type': 'line', 'data': {'labels': labels, 'datasets': datasets}, 'options': {'responsive': True}}

    def _pie_chart(self, x_col):
        if not x_col:
            # Use first categorical column
            cat_cols = self.df.select_dtypes(exclude=['number']).columns
            if len(cat_cols) == 0:
                return {'error': 'No categorical column found for pie chart.'}
            x_col = cat_cols[0]

        value_counts = self.df[x_col].value_counts().head(10)
        return {
            'type': 'pie',
            'data': {
                'labels': value_counts.index.astype(str).tolist(),
                'datasets': [{'data': value_counts.values.tolist()}],
            },
            'options': {'responsive': True},
        }

    def _scatter_chart(self, x_col, y_col):
        if not x_col or not y_col:
            return {'error': 'x and y columns are required for scatter chart.'}

        valid_data = self.df[[x_col, y_col]].dropna()
        return {
            'type': 'scatter',
            'data': {
                'datasets': [{
                    'label': f'{x_col} vs {y_col}',
                    'data': [{'x': float(valid_data[x_col].iloc[i]),
                             'y': float(valid_data[y_col].iloc[i])}
                            for i in range(min(500, len(valid_data)))],
                }]
            },
            'options': {'responsive': True},
        }

    def _heatmap_data(self, x_col, y_col):
        numeric_df = self.df.select_dtypes(include=['number'])
        if len(numeric_df.columns) < 2:
            return {'error': 'Need at least 2 numeric columns for heatmap.'}

        corr = numeric_df.corr()
        return {
            'type': 'heatmap',
            'data': {
                'columns': corr.columns.tolist(),
                'rows': corr.index.tolist(),
                'values': corr.values.tolist(),
            },
            'options': {'responsive': True},
        }

    def _histogram_chart(self, x_col):
        if not x_col:
            num_cols = self.df.select_dtypes(include=['number']).columns
            if len(num_cols) == 0:
                return {'error': 'No numeric columns found.'}
            x_col = num_cols[0]

        hist, bin_edges = np.histogram(self.df[x_col].dropna(), bins=20)
        labels = [f'{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}' for i in range(len(hist))]

        return {
            'type': 'histogram',
            'data': {
                'labels': labels,
                'datasets': [{'label': x_col, 'data': hist.tolist()}],
            },
            'options': {'responsive': True},
        }
