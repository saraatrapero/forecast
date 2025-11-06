"""
Feature engineering for ML models.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Generate features for machine learning models.
    """
    
    def build_features(
        self, skus: List[Dict[str, Any]], meses_fecha: List[datetime]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build feature matrix and target vector.
        
        Features include:
        - Lags (1, 2, 3, 6, 12 months)
        - Rolling statistics (mean, std, min, max)
        - Trend indicators
        - Seasonality indicators
        - Time-based features (month, quarter, year)
        """
        all_features = []
        all_targets = []
        
        for sku in skus:
            ventas = sku["ventas"]
            
            # Need at least 13 periods for 12-month lag
            if len(ventas) < 13:
                continue
            
            for i in range(12, len(ventas)):
                features = self._extract_features_at_time(
                    ventas, i, meses_fecha[i] if i < len(meses_fecha) else None
                )
                target = ventas[i]
                
                all_features.append(features)
                all_targets.append(target)
        
        if len(all_features) == 0:
            logger.warning("No features could be generated")
            return np.array([]), np.array([])
        
        return np.array(all_features), np.array(all_targets)
    
    def _extract_features_at_time(
        self, ventas: List[float], idx: int, fecha: datetime = None
    ) -> List[float]:
        """
        Extract features for a specific time point.
        """
        features = []
        
        # Lags
        lags = [1, 2, 3, 6, 12]
        for lag in lags:
            if idx >= lag:
                features.append(ventas[idx - lag])
            else:
                features.append(0)
        
        # Rolling statistics (3-month window)
        if idx >= 3:
            window = ventas[idx-3:idx]
            features.extend([
                np.mean(window),
                np.std(window),
                np.min(window),
                np.max(window)
            ])
        else:
            features.extend([0, 0, 0, 0])
        
        # Rolling statistics (6-month window)
        if idx >= 6:
            window = ventas[idx-6:idx]
            features.extend([
                np.mean(window),
                np.std(window)
            ])
        else:
            features.extend([0, 0])
        
        # Trend (simple)
        if idx >= 3:
            trend = (ventas[idx-1] - ventas[idx-3]) / (ventas[idx-3] + 1)
            features.append(trend)
        else:
            features.append(0)
        
        # Acceleration
        if idx >= 4:
            accel = (ventas[idx-1] - 2*ventas[idx-2] + ventas[idx-3]) / (ventas[idx-2] + 1)
            features.append(accel)
        else:
            features.append(0)
        
        # Time-based features
        if fecha:
            features.extend([
                fecha.month,  # 1-12
                (fecha.month - 1) // 3 + 1,  # Quarter 1-4
                fecha.year % 100,  # Year (2-digit)
                1 if fecha.month in [12, 1, 2] else 0,  # Winter indicator
                1 if fecha.month in [6, 7, 8] else 0,  # Summer indicator
            ])
        else:
            features.extend([0, 0, 0, 0, 0])
        
        # Fourier features for seasonality
        if fecha:
            month_angle = 2 * np.pi * fecha.month / 12
            features.extend([
                np.sin(month_angle),
                np.cos(month_angle)
            ])
        else:
            features.extend([0, 0])
        
        return features
    
    def create_lag_features(
        self, series: List[float], lags: List[int]
    ) -> np.ndarray:
        """
        Create lag features for a single series.
        """
        n = len(series)
        max_lag = max(lags)
        
        if n <= max_lag:
            return np.array([])
        
        features = []
        for i in range(max_lag, n):
            row = [series[i - lag] for lag in lags]
            features.append(row)
        
        return np.array(features)
    
    def create_rolling_features(
        self, series: List[float], windows: List[int]
    ) -> Dict[str, List[float]]:
        """
        Create rolling window statistics.
        """
        df = pd.DataFrame({"value": series})
        
        features = {}
        for window in windows:
            features[f"rolling_mean_{window}"] = df["value"].rolling(window).mean().fillna(0).tolist()
            features[f"rolling_std_{window}"] = df["value"].rolling(window).std().fillna(0).tolist()
            features[f"rolling_min_{window}"] = df["value"].rolling(window).min().fillna(0).tolist()
            features[f"rolling_max_{window}"] = df["value"].rolling(window).max().fillna(0).tolist()
        
        return features
    
    def decompose_series(
        self, series: List[float], period: int = 12
    ) -> Dict[str, List[float]]:
        """
        Decompose time series into trend, seasonal, and residual.
        """
        if len(series) < 2 * period:
            return {
                "trend": series,
                "seasonal": [0] * len(series),
                "residual": [0] * len(series)
            }
        
        try:
            from statsmodels.tsa.seasonal import seasonal_decompose
            
            df = pd.DataFrame({"value": series})
            decomposition = seasonal_decompose(
                df["value"],
                model='additive',
                period=period,
                extrapolate_trend='freq'
            )
            
            return {
                "trend": decomposition.trend.fillna(0).tolist(),
                "seasonal": decomposition.seasonal.fillna(0).tolist(),
                "residual": decomposition.resid.fillna(0).tolist()
            }
        except Exception as e:
            logger.warning(f"Decomposition failed: {str(e)}")
            return {
                "trend": series,
                "seasonal": [0] * len(series),
                "residual": [0] * len(series)
            }
