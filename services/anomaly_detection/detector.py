"""
Reusable anomaly detection service.
Supports multiple algorithms: Isolation Forest, Z-Score, MAD.
"""
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import IsolationForest
from enum import Enum


class AnomalyAlgorithm(str, Enum):
    """Supported anomaly detection algorithms"""
    ISOLATION_FOREST = "isolation_forest"
    ZSCORE = "zscore"
    MAD = "mad"  # Median Absolute Deviation


class AnomalyDetector(ABC):
    """Abstract base class for anomaly detection"""
    
    @abstractmethod
    def detect(self, data: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        Detect anomalies in the data.
        
        Returns:
            Tuple of (anomaly scores, metadata)
        """
        pass
    
    @abstractmethod
    def detect_window(self, data: np.ndarray, window_size: int) -> List[Dict]:
        """
        Detect anomalies using sliding window.
        
        Returns:
            List of anomaly detection results per window
        """
        pass


class IsolationForestDetector(AnomalyDetector):
    """Isolation Forest based anomaly detection"""
    
    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        self.contamination = contamination
        self.model = IsolationForest(contamination=contamination, random_state=random_state)
    
    def detect(self, data: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """Detect anomalies using Isolation Forest"""
        if len(data.shape) == 1:
            data = data.reshape(-1, 1)
        
        predictions = self.model.fit_predict(data)
        scores = self.model.score_samples(data)
        
        anomalies = predictions == -1
        
        metadata = {
            "algorithm": "isolation_forest",
            "contamination": self.contamination,
            "num_anomalies": int(np.sum(anomalies)),
            "anomaly_ratio": float(np.sum(anomalies) / len(anomalies))
        }
        
        return scores, metadata
    
    def detect_window(self, data: np.ndarray, window_size: int) -> List[Dict]:
        """Detect anomalies using sliding window"""
        results = []
        num_windows = len(data) - window_size + 1
        
        for i in range(num_windows):
            window = data[i:i+window_size].reshape(-1, 1)
            scores, meta = self.detect(window)
            
            results.append({
                "window_start": i,
                "window_end": i + window_size,
                "scores": scores,
                "metadata": meta
            })
        
        return results


class ZScoreDetector(AnomalyDetector):
    """Z-Score based anomaly detection"""
    
    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold
    
    def detect(self, data: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """Detect anomalies using Z-Score"""
        if len(data.shape) == 1:
            data = data.reshape(-1, 1)
        
        # Calculate z-scores
        mean = np.mean(data, axis=0)
        std = np.std(data, axis=0)
        scores = np.abs((data - mean) / (std + 1e-10))
        
        # For multivariate, take max score per sample
        if len(data.shape) > 1:
            scores = np.max(scores, axis=1)
        else:
            scores = scores.flatten()
        
        anomalies = scores > self.threshold
        
        metadata = {
            "algorithm": "zscore",
            "threshold": self.threshold,
            "num_anomalies": int(np.sum(anomalies)),
            "anomaly_ratio": float(np.sum(anomalies) / len(anomalies))
        }
        
        return scores, metadata
    
    def detect_window(self, data: np.ndarray, window_size: int) -> List[Dict]:
        """Detect anomalies using sliding window"""
        results = []
        num_windows = len(data) - window_size + 1
        
        for i in range(num_windows):
            window = data[i:i+window_size].reshape(-1, 1)
            scores, meta = self.detect(window)
            
            results.append({
                "window_start": i,
                "window_end": i + window_size,
                "scores": scores,
                "metadata": meta
            })
        
        return results


class MADDetector(AnomalyDetector):
    """Median Absolute Deviation based anomaly detection"""
    
    def __init__(self, threshold: float = 2.5):
        self.threshold = threshold
    
    def detect(self, data: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """Detect anomalies using MAD"""
        if len(data.shape) == 1:
            data = data.reshape(-1, 1)
        
        # Calculate MAD for each feature
        median = np.median(data, axis=0)
        mad = np.median(np.abs(data - median), axis=0)
        
        # Calculate modified z-scores
        scores = 0.6745 * (data - median) / (mad + 1e-10)
        
        # For multivariate, take max score per sample
        if len(data.shape) > 1:
            scores = np.max(np.abs(scores), axis=1)
        else:
            scores = np.abs(scores.flatten())
        
        anomalies = scores > self.threshold
        
        metadata = {
            "algorithm": "mad",
            "threshold": self.threshold,
            "num_anomalies": int(np.sum(anomalies)),
            "anomaly_ratio": float(np.sum(anomalies) / len(anomalies))
        }
        
        return scores, metadata
    
    def detect_window(self, data: np.ndarray, window_size: int) -> List[Dict]:
        """Detect anomalies using sliding window"""
        results = []
        num_windows = len(data) - window_size + 1
        
        for i in range(num_windows):
            window = data[i:i+window_size].reshape(-1, 1)
            scores, meta = self.detect(window)
            
            results.append({
                "window_start": i,
                "window_end": i + window_size,
                "scores": scores,
                "metadata": meta
            })
        
        return results


class AnomalyDetectionService:
    """Factory and service for anomaly detection"""
    
    def __init__(self, algorithm: str = "isolation_forest", **kwargs):
        """
        Initialize the anomaly detection service.
        
        Args:
            algorithm: One of 'isolation_forest', 'zscore', 'mad'
            **kwargs: Algorithm-specific parameters
        """
        self.algorithm = algorithm
        self.detector = self._create_detector(algorithm, kwargs)
    
    def _create_detector(self, algorithm: str, params: Dict) -> AnomalyDetector:
        """Create the appropriate detector"""
        if algorithm == AnomalyAlgorithm.ISOLATION_FOREST:
            return IsolationForestDetector(
                contamination=params.get("contamination", 0.1)
            )
        elif algorithm == AnomalyAlgorithm.ZSCORE:
            return ZScoreDetector(
                threshold=params.get("threshold", 3.0)
            )
        elif algorithm == AnomalyAlgorithm.MAD:
            return MADDetector(
                threshold=params.get("threshold", 2.5)
            )
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
    
    def detect_anomalies_in_dataframe(
        self,
        df: pd.DataFrame,
        exclude_cols: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Detect anomalies in a DataFrame.
        
        Args:
            df: Input DataFrame
            exclude_cols: Columns to exclude from analysis
        
        Returns:
            DataFrame with anomaly scores
        """
        if exclude_cols is None:
            exclude_cols = ["timestamp"]
        
        # Get numeric columns
        numeric_cols = [col for col in df.columns 
                       if col not in exclude_cols and df[col].dtype in [np.float64, np.int64]]
        
        # Extract numeric data
        data = df[numeric_cols].values
        
        # Detect anomalies
        scores, metadata = self.detector.detect(data)
        
        # Add to dataframe
        df_result = df.copy()
        df_result["anomaly_score"] = scores
        df_result["is_anomaly"] = scores > np.percentile(scores, 90)
        
        return df_result, metadata
    
    def detect_anomalies_timeseries(
        self,
        df: pd.DataFrame,
        metric_cols: List[str],
        window_size: int = 30
    ) -> Dict:
        """
        Detect anomalies in time-series using sliding window.
        
        Args:
            df: Input DataFrame with time-series data
            metric_cols: Columns to analyze
            window_size: Window size for sliding window
        
        Returns:
            Detection results with anomaly indices
        """
        data = df[metric_cols].values
        window_results = self.detector.detect_window(data, window_size)
        
        return {
            "window_results": window_results,
            "metric_cols": metric_cols,
            "window_size": window_size
        }


if __name__ == "__main__":
    # Example usage
    from data.synthetic_kpi_generator import NetworkKPIGenerator
    
    # Generate sample data
    generator = NetworkKPIGenerator(num_metrics=3, time_steps=500)
    df, anomalies = generator.generate_timeseries()
    
    # Detect anomalies with different algorithms
    for algo in ["isolation_forest", "zscore", "mad"]:
        service = AnomalyDetectionService(algorithm=algo)
        df_result, meta = service.detect_anomalies_in_dataframe(df)
        print(f"\n{algo.upper()} Results:")
        print(meta)
