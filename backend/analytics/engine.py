"""
Data processing engine - handles parsing, profiling, cleaning, and analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import json
import os


class DataProcessor:
    """Core data processing engine for dataset handling."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df = None
        self.file_type = self._detect_file_type()

    def _detect_file_type(self) -> str:
        ext = os.path.splitext(self.file_path)[1].lower()
        type_map = {'.csv': 'csv', '.tsv': 'csv', '.xlsx': 'xlsx', '.xls': 'xlsx'}
        return type_map.get(ext, 'csv')

    def load(self) -> pd.DataFrame:
        """Load dataset into pandas DataFrame with fast encoding detection."""
        if self.df is not None:
            return self.df

        if self.file_type == 'csv':
            sep = '\t' if self.file_path.endswith('.tsv') else ','
            encoding = 'utf-8'
            try:
                with open(self.file_path, 'rb') as f:
                    chunk = f.read(131072)
                    chunk.decode('utf-8')
            except UnicodeDecodeError:
                encoding = 'latin-1'

            try:
                self.df = pd.read_csv(self.file_path, sep=sep, encoding=encoding, low_memory=False)
            except Exception:
                self.df = pd.read_csv(self.file_path, sep=sep, encoding='latin-1', on_bad_lines='skip', low_memory=False)

        elif self.file_type == 'xlsx':
            self.df = pd.read_excel(self.file_path, engine='openpyxl')
        else:
            encoding = 'utf-8'
            try:
                with open(self.file_path, 'rb') as f:
                    chunk = f.read(131072)
                    chunk.decode('utf-8')
            except UnicodeDecodeError:
                encoding = 'latin-1'
            self.df = pd.read_csv(self.file_path, encoding=encoding, low_memory=False)
        return self.df

    def process(self) -> Dict[str, Any]:
        """Full processing pipeline: load, profile, and return metadata."""
        self.load()

        result = {
            'row_count': int(len(self.df)),
            'column_count': int(len(self.df.columns)),
            'file_type': self.file_type,
            'column_names': list(self.df.columns),
            'column_types': self._get_column_types(),
            'data_profile': self._create_profile(),
            'sample_data': self._get_sample_data(),
            'quality_score': self._calculate_quality_score(),
        }
        return result

    def _get_column_types(self) -> Dict[str, str]:
        """Get data types for each column."""
        types = {}
        for col in self.df.columns:
            dtype = str(self.df[col].dtype)
            if 'int' in dtype:
                types[col] = 'integer'
            elif 'float' in dtype:
                types[col] = 'float'
            elif 'datetime' in dtype:
                types[col] = 'datetime'
            elif 'bool' in dtype:
                types[col] = 'boolean'
            elif 'object' in dtype:
                if self.df[col].nunique() / max(len(self.df), 1) < 0.05:
                    types[col] = 'category'
                else:
                    types[col] = 'string'
            else:
                types[col] = 'other'
        return types

    def _safe_float(self, val, round_digits=4) -> Optional[float]:
        """Convert float safely, converting NaN and Inf to None."""
        if pd.isna(val) or np.isinf(val):
            return None
        return round(float(val), round_digits)

    def _create_profile(self) -> Dict[str, Any]:
        """Create detailed statistical profile of the dataset (using sampling for large files)."""
        profile = {}
        
        # Use sampling for expensive statistical metrics if dataset exceeds 50,000 rows
        stat_df = self.df if len(self.df) <= 50000 else self.df.sample(50000, random_state=42)

        for col in self.df.columns:
            col_info = {
                'dtype': str(self.df[col].dtype),
                'null_count': int(self.df[col].isnull().sum()),
                'null_percent': round(float(self.df[col].isnull().sum() / len(self.df) * 100), 2),
                'unique_count': int(stat_df[col].nunique()),
            }

            if self.df[col].dtype in ['int64', 'float64', 'int32', 'float32']:
                col_info.update({
                    'min': self._safe_float(self.df[col].min()),
                    'max': self._safe_float(self.df[col].max()),
                    'mean': self._safe_float(self.df[col].mean()),
                    'median': self._safe_float(stat_df[col].median()),
                    'std': self._safe_float(stat_df[col].std()),
                })

                # Percentiles
                try:
                    percentiles = stat_df[col].quantile([0.25, 0.5, 0.75])
                    col_info['percentiles'] = {
                        'p25': self._safe_float(percentiles.iloc[0]),
                        'p50': self._safe_float(percentiles.iloc[1]),
                        'p75': self._safe_float(percentiles.iloc[2]),
                    }
                except Exception:
                    pass

                # Skewness and kurtosis
                if len(stat_df[col].dropna()) > 2:
                    col_info['skewness'] = self._safe_float(stat_df[col].skew())
                    col_info['kurtosis'] = self._safe_float(stat_df[col].kurtosis())

            elif self.df[col].dtype == 'object':
                top_dict = stat_df[col].value_counts().head(5).to_dict()
                col_info['top_values'] = {str(k): int(v) for k, v in top_dict.items()}

            profile[col] = col_info

        return profile

    def _get_sample_data(self) -> List[Dict[str, Any]]:
        """Get first 20 rows as sample data (JSON serializable)."""
        sample = self.df.head(20)
        records = []
        for _, row in sample.iterrows():
            record = {}
            for col in self.df.columns:
                val = row[col]
                if pd.isna(val):
                    record[col] = None
                elif hasattr(val, 'isoformat'):
                    record[col] = val.isoformat()
                elif isinstance(val, (np.integer,)):
                    record[col] = int(val)
                elif isinstance(val, (np.floating,)):
                    record[col] = float(val)
                elif isinstance(val, np.ndarray):
                    record[col] = val.tolist()
                else:
                    record[col] = str(val) if not isinstance(val, (int, float, bool)) else val
            records.append(record)
        return records

    def _calculate_quality_score(self) -> float:
        """Calculate data quality score (0-100)."""
        if len(self.df) == 0:
            return 0.0

        score = 100.0

        # Deduct for missing values
        null_pct = self.df.isnull().sum().sum() / (len(self.df) * len(self.df.columns)) * 100
        score -= min(null_pct * 0.5, 30)

        # Deduct for duplicate rows
        dup_pct = self.df.duplicated().sum() / len(self.df) * 100
        score -= min(dup_pct * 0.5, 20)

        # Bonus for having data types well-defined
        score += min(self.df.select_dtypes(include=['number']).shape[1] * 2, 10)

        return round(max(0, min(100, score)), 1)

    def clean(self, operation: str, parameters: Dict = None) -> Dict[str, Any]:
        """Execute a cleaning operation on the dataset."""
        self.load()
        initial_rows = len(self.df)
        result = {'rows_affected': 0, 'summary': ''}

        if operation == 'remove_duplicates':
            self.df = self.df.drop_duplicates()
            result['rows_affected'] = initial_rows - len(self.df)
            result['summary'] = f"Removed {result['rows_affected']} duplicate rows."

        elif operation == 'fill_nulls':
            strategy = parameters.get('strategy', 'mean') if parameters else 'mean'
            columns = parameters.get('columns', None) if parameters else None

            if columns:
                subset = self.df[columns]
            else:
                subset = self.df.select_dtypes(include=['number'])

            before_nulls = subset.isnull().sum().sum()
            if strategy == 'mean':
                for col in subset.columns:
                    if subset[col].dtype in ['float64', 'int64']:
                        self.df[col] = self.df[col].fillna(self.df[col].mean())
            elif strategy == 'median':
                for col in subset.columns:
                    if subset[col].dtype in ['float64', 'int64']:
                        self.df[col] = self.df[col].fillna(self.df[col].median())
            elif strategy == 'mode':
                for col in subset.columns:
                    self.df[col] = self.df[col].fillna(self.df[col].mode().iloc[0])
            elif strategy == 'constant':
                value = parameters.get('value', 0) if parameters else 0
                for col in subset.columns:
                    self.df[col] = self.df[col].fillna(value)

            after_nulls = subset.isnull().sum().sum()
            result['rows_affected'] = int(before_nulls - after_nulls)
            result['summary'] = f"Filled {result['rows_affected']} null values using {strategy}."

        elif operation == 'remove_nulls':
            self.df = self.df.dropna()
            result['rows_affected'] = initial_rows - len(self.df)
            result['summary'] = f"Removed {result['rows_affected']} rows with null values."

        elif operation == 'outlier_removal':
            method = parameters.get('method', 'iqr') if parameters else 'iqr'
            threshold = parameters.get('threshold', 1.5) if parameters else 1.5
            numeric_cols = self.df.select_dtypes(include=['number']).columns
            removed = 0

            for col in numeric_cols:
                if method == 'iqr':
                    q1 = self.df[col].quantile(0.25)
                    q3 = self.df[col].quantile(0.75)
                    iqr = q3 - q1
                    mask = (self.df[col] >= q1 - threshold * iqr) & (self.df[col] <= q3 + threshold * iqr)
                elif method == 'zscore':
                    mean = self.df[col].mean()
                    std = self.df[col].std()
                    mask = abs(self.df[col] - mean) <= threshold * std
                else:
                    continue

                removed += (~mask).sum()
                self.df = self.df[mask]

            result['rows_affected'] = int(removed)
            result['summary'] = f"Removed {removed} outlier rows using {method} method."

        elif operation == 'type_cast':
            column = parameters.get('column') if parameters else None
            target_type = parameters.get('target_type', 'float') if parameters else 'float'

            if column and column in self.df.columns:
                type_map = {
                    'float': 'float64', 'int': 'int64',
                    'string': 'str', 'datetime': 'datetime64[ns]',
                }
                try:
                    target_dtype = type_map.get(target_type, target_type)
                    if target_type == 'datetime':
                        self.df[column] = pd.to_datetime(self.df[column], errors='coerce')
                    else:
                        self.df[column] = self.df[column].astype(target_dtype)
                    result['rows_affected'] = 1
                    result['summary'] = f"Converted column '{column}' to {target_type}."
                except Exception as e:
                    result['summary'] = f"Type cast failed: {str(e)}"

        elif operation == 'standardize':
            column = parameters.get('column') if parameters else None
            if column and column in self.df.columns:
                self.df[column] = self.df[column].str.strip().str.title()
                result['rows_affected'] = len(self.df)
                result['summary'] = f"Standardized column '{column}'."

        elif operation == 'auto_clean':
            # Full automatic cleaning pipeline
            self.df = self.df.drop_duplicates()
            dups = initial_rows - len(self.df)
            self.df = self.df.dropna(thresh=int(len(self.df.columns) * 0.5))
            nulls = initial_rows - len(self.df) - dups
            numeric_cols = self.df.select_dtypes(include=['number']).columns
            for col in numeric_cols:
                self.df[col] = self.df[col].fillna(self.df[col].median())

            result['rows_affected'] = initial_rows - len(self.df)
            result['summary'] = f"Auto-cleaned: removed {dups} duplicates, {nulls} sparse rows, filled numeric nulls."

        # Save cleaned data
        self.df.to_csv(self.file_path, index=False)

        result['new_row_count'] = len(self.df)
        return result

    def get_correlations(self) -> Dict[str, float]:
        """Get correlation matrix for numeric columns."""
        self.load()
        numeric_df = self.df.select_dtypes(include=['number'])
        if len(numeric_df.columns) < 2:
            return {}
        corr = numeric_df.corr()
        # Convert to dict format
        result = {}
        for i, col1 in enumerate(corr.columns):
            for j, col2 in enumerate(corr.columns):
                if i < j:  # Only upper triangle
                    key = f"{col1} vs {col2}"
                    result[key] = round(float(corr.iloc[i, j]), 4)
        return result

    def get_kpis(self) -> Dict[str, Any]:
        """Generate key performance indicators from the dataset."""
        self.load()
        kpis = {
            'total_rows': int(len(self.df)),
            'total_columns': int(len(self.df.columns)),
            'numeric_columns': int(self.df.select_dtypes(include=['number']).shape[1]),
            'categorical_columns': int(self.df.select_dtypes(exclude=['number']).shape[1]),
            'null_percentage': round(float(self.df.isnull().sum().sum() / (len(self.df) * len(self.df.columns)) * 100), 2),
            'duplicate_rows': int(self.df.duplicated().sum()),
        }

        # Find potential date columns
        date_cols = self.df.select_dtypes(include=['datetime64']).columns.tolist()
        if date_cols:
            kpis['date_columns'] = date_cols
            for col in date_cols:
                kpis[f'{col}_range'] = {
                    'start': str(self.df[col].min()),
                    'end': str(self.df[col].max()),
                    'days': int((self.df[col].max() - self.df[col].min()).days),
                }

        return kpis
