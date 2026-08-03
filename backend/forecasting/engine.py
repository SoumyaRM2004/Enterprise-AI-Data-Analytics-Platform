"""
Forecasting engine - supports multiple forecasting methods.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta


class ForecastEngine:
    """Engine for time series forecasting and anomaly detection."""

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def forecast(
        self,
        method: str,
        target_column: str,
        date_column: Optional[str] = None,
        horizon: int = 30,
        parameters: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Generate forecast using specified method."""

        if target_column not in self.df.columns:
            raise ValueError(f"Column '{target_column}' not found in dataset.")

        # Prepare data
        if date_column and date_column in self.df.columns:
            try:
                temp_df = self.df[[date_column, target_column]].copy()
                temp_df[date_column] = pd.to_datetime(temp_df[date_column], format='mixed', dayfirst=True, errors='coerce')
                temp_df[target_column] = pd.to_numeric(temp_df[target_column], errors='coerce')
                temp_df = temp_df.dropna(subset=[date_column, target_column])

                # Aggregate duplicate timestamps into a clean daily time series
                daily_ts = temp_df.groupby(pd.Grouper(key=date_column, freq='D'))[target_column].mean().dropna()
                if len(daily_ts) >= 5:
                    time_series = daily_ts
                else:
                    time_series = pd.to_numeric(self.df[target_column], errors='coerce').dropna()
            except Exception:
                time_series = pd.to_numeric(self.df[target_column], errors='coerce').dropna()
        else:
            time_series = pd.to_numeric(self.df[target_column], errors='coerce').dropna()

        if len(time_series) < 5:
            raise ValueError("Not enough numeric data points for forecasting. Need at least 5 valid numbers.")

        if method == 'arima':
            return self._forecast_arima(time_series, horizon, parameters or {})
        elif method == 'sarimax':
            return self._forecast_sarimax(time_series, horizon, parameters or {})
        elif method == 'holt_winters':
            return self._forecast_holt_winters(time_series, horizon, parameters or {})
        elif method == 'linear_regression':
            return self._forecast_linear_regression(time_series, horizon)
        elif method == 'exp_smoothing':
            return self._forecast_exponential_smoothing(time_series, horizon, parameters or {})
        else:
            raise ValueError(f"Unknown forecasting method: {method}")

    def _forecast_arima(self, ts: pd.Series, horizon: int, params: Dict) -> Dict[str, Any]:
        """ARIMA forecasting."""
        from statsmodels.tsa.arima.model import ARIMA

        order = (params.get('p', 1), params.get('d', 1), params.get('q', 1))
        try:
            model = ARIMA(ts, order=order)
            fit = model.fit()
            forecast = fit.get_forecast(steps=horizon)
            mean = forecast.predicted_mean
            conf = forecast.conf_int(alpha=0.05)

            return self._format_forecast_result(mean, conf, ts, horizon)
        except Exception as e:
            # Fallback to simpler method
            return self._forecast_linear_regression(ts, horizon)

    def _forecast_sarimax(self, ts: pd.Series, horizon: int, params: Dict) -> Dict[str, Any]:
        """SARIMAX forecasting."""
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        order = (params.get('p', 1), params.get('d', 0), params.get('q', 1))
        seasonal = (params.get('P', 1), params.get('D', 0), params.get('Q', 1), params.get('period', 12))

        try:
            model = SARIMAX(ts, order=order, seasonal_order=seasonal)
            fit = model.fit(disp=False)
            forecast = fit.get_forecast(steps=horizon)
            mean = forecast.predicted_mean
            conf = forecast.conf_int(alpha=0.05)

            return self._format_forecast_result(mean, conf, ts, horizon)
        except Exception:
            return self._forecast_arima(ts, horizon, params)

    def _forecast_holt_winters(self, ts: pd.Series, horizon: int, params: Dict) -> Dict[str, Any]:
        """Holt-Winters exponential smoothing."""
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        trend = params.get('trend', 'add')
        seasonal = params.get('seasonal', None)
        seasonal_periods = params.get('seasonal_periods', None)

        try:
            model = ExponentialSmoothing(
                ts, trend=trend, seasonal=seasonal, seasonal_periods=seasonal_periods
            )
            fit = model.fit()
            forecast = fit.forecast(horizon)

            # Calculate confidence intervals (approximate)
            resid_std = np.std(ts - fit.fittedvalues)
            lower = forecast - 1.96 * resid_std
            upper = forecast + 1.96 * resid_std

            result = pd.DataFrame({
                'forecast': forecast.values,
                'lower': lower.values,
                'upper': upper.values,
            }, index=range(len(ts), len(ts) + horizon))

            return self._format_forecast_result(forecast, result[['lower', 'upper']], ts, horizon)
        except Exception:
            return self._forecast_linear_regression(ts, horizon)

    def _forecast_linear_regression(self, ts: pd.Series, horizon: int) -> Dict[str, Any]:
        """Simple linear regression forecasting."""
        x = np.arange(len(ts)).reshape(-1, 1)
        y = ts.values.reshape(-1, 1)

        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        model.fit(x, y)

        future_x = np.arange(len(ts), len(ts) + horizon).reshape(-1, 1)
        predictions = model.predict(future_x).flatten()

        # Calculate residuals for confidence intervals
        fitted = model.predict(x).flatten()
        residuals = ts.values - fitted
        std_err = np.std(residuals) * np.sqrt(1 + 1/len(ts))

        lower = predictions - 1.96 * std_err
        upper = predictions + 1.96 * std_err

        forecast_series = pd.Series(predictions, index=range(len(ts), len(ts) + horizon))
        conf = pd.DataFrame({'lower': lower, 'upper': upper}, index=range(len(ts), len(ts) + horizon))

        return self._format_forecast_result(forecast_series, conf, ts, horizon)

    def _forecast_exponential_smoothing(self, ts: pd.Series, horizon: int, params: Dict) -> Dict[str, Any]:
        """Simple exponential smoothing."""
        alpha = params.get('alpha', None)

        from statsmodels.tsa.holtwinters import SimpleExpSmoothing
        try:
            model = SimpleExpSmoothing(ts)
            fit = model.fit(smoothing_level=alpha)
            forecast = fit.forecast(horizon)

            resid_std = np.std(ts - fit.fittedvalues)
            lower = forecast - 1.96 * resid_std
            upper = forecast + 1.96 * resid_std

            conf = pd.DataFrame({'lower': lower.values, 'upper': upper.values},
                              index=range(len(ts), len(ts) + horizon))

            return self._format_forecast_result(forecast, conf, ts, horizon)
        except Exception:
            return self._forecast_linear_regression(ts, horizon)

    def _format_forecast_result(
        self, forecast: pd.Series, confidence: pd.DataFrame,
        historical: pd.Series, horizon: int
    ) -> Dict[str, Any]:
        """Format forecast results into JSON-serializable dict."""
        # Historical data
        hist_values = historical.tail(60).values.tolist()
        hist_dates = [str(i) for i in historical.tail(60).index]

        # Forecast data
        forecast_values = forecast.values.tolist()
        forecast_dates = [str(i) for i in forecast.index]

        # Confidence intervals
        lower = confidence['lower'].values.tolist() if 'lower' in confidence.columns else None
        upper = confidence['upper'].values.tolist() if 'upper' in confidence.columns else None

        # Calculate metrics (MAE, RMSE on training)
        fitted_start = max(0, len(historical) - len(forecast))
        fitted = historical.iloc[fitted_start:]

        metrics = {}
        if len(fitted) == len(forecast) and len(fitted) > 0:
            errors = fitted.values - forecast.values
            metrics = {
                'mae': float(np.mean(np.abs(errors))),
                'rmse': float(np.sqrt(np.mean(errors ** 2))),
                'mape': float(np.mean(np.abs(errors / np.where(fitted.values != 0, fitted.values, 1))) * 100),
                'r2': float(1 - np.sum(errors**2) / np.sum((fitted.values - np.mean(fitted.values))**2)),
            }

        return {
            'historical': {
                'dates': hist_dates,
                'values': [float(v) if not np.isnan(v) else None for v in hist_values],
            },
            'forecast': {
                'dates': forecast_dates,
                'values': [float(v) if not np.isnan(v) else None for v in forecast_values],
                'lower_bound': [float(v) if not np.isnan(v) else None for v in lower] if lower else None,
                'upper_bound': [float(v) if not np.isnan(v) else None for v in upper] if upper else None,
            },
            'horizon': horizon,
            'metrics': metrics,
        }

    def detect_anomalies(
        self,
        column: str,
        method: str = 'isolation_forest',
        parameters: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Detect anomalies in a column."""
        if column not in self.df.columns:
            raise ValueError(f"Column '{column}' not found.")

        data = self.df[column].dropna()

        if method == 'isolation_forest':
            return self._detect_isolation_forest(data, column, parameters or {})
        elif method == 'zscore':
            return self._detect_zscore(data, column, parameters or {})
        elif method == 'iqr':
            return self._detect_iqr(data, column, parameters or {})
        else:
            raise ValueError(f"Unknown anomaly detection method: {method}")

    def _detect_isolation_forest(self, data: pd.Series, column: str, params: Dict) -> Dict[str, Any]:
        """Isolation Forest anomaly detection."""
        from sklearn.ensemble import IsolationForest

        n_estimators = params.get('n_estimators', 100)
        contamination = params.get('contamination', 'auto')

        X = data.values.reshape(-1, 1)
        model = IsolationForest(n_estimators=n_estimators, contamination=contamination, random_state=42)
        predictions = model.fit_predict(X)
        scores = model.decision_function(X)

        anomaly_indices = np.where(predictions == -1)[0]
        anomalies = [
            {'index': int(i), 'value': float(data.iloc[i]), 'score': float(scores[i])}
            for i in anomaly_indices
        ]

        return {
            'method': 'isolation_forest',
            'column': column,
            'anomalies': anomalies,
            'anomaly_count': len(anomalies),
            'total_records': len(data),
            'anomaly_percentage': round(len(anomalies) / len(data) * 100, 2),
        }

    def _detect_zscore(self, data: pd.Series, column: str, params: Dict) -> Dict[str, Any]:
        """Z-score based anomaly detection."""
        threshold = params.get('threshold', 3.0)
        mean = data.mean()
        std = data.std()
        z_scores = np.abs((data - mean) / std)

        anomaly_mask = z_scores > threshold
        anomalies = [
            {'index': int(i), 'value': float(data.iloc[i]), 'z_score': float(z_scores.iloc[i])}
            for i in np.where(anomaly_mask)[0]
        ]

        return {
            'method': 'zscore',
            'column': column,
            'anomalies': anomalies,
            'anomaly_count': len(anomalies),
            'total_records': len(data),
            'anomaly_percentage': round(len(anomalies) / len(data) * 100, 2),
        }

    def _detect_iqr(self, data: pd.Series, column: str, params: Dict) -> Dict[str, Any]:
        """IQR-based anomaly detection."""
        threshold = params.get('threshold', 1.5)
        q1 = data.quantile(0.25)
        q3 = data.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr

        anomaly_mask = (data < lower_bound) | (data > upper_bound)
        anomalies = [
            {'index': int(i), 'value': float(data.iloc[i])}
            for i in np.where(anomaly_mask)[0]
        ]

        return {
            'method': 'iqr',
            'column': column,
            'anomalies': anomalies,
            'anomaly_count': len(anomalies),
            'total_records': len(data),
            'anomaly_percentage': round(len(anomalies) / len(data) * 100, 2),
        }
